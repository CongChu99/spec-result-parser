#!/usr/bin/env bash
# apply-infra.sh — Terraform apply + GitHub Secrets + SSL verify + infraState writer
# Usage: ./apply-infra.sh <feature-slug> <aws-region> <app-port> <ssh-cidr> <certbot-email>
# Environment: uses CLOUDFLARE_API_TOKEN (from env or ~/.cloudflare), AWS credentials (~/.aws/credentials)

set -euo pipefail

FEATURE_SLUG="${1:?Usage: $0 <feature-slug> <aws-region> <app-port> <ssh-cidr> <certbot-email>}"
AWS_REGION="${2:?}"
APP_PORT="${3:?}"
SSH_CIDR="${4:?}"
CERTBOT_EMAIL="${5:?}"

STATE_FILE="docs/c4flow/.state.json"
STATE_EXISTING=$(cat "$STATE_FILE")
TF_DIR="docs/c4flow/terraform/${FEATURE_SLUG}"

# ── Load Cloudflare credentials ───────────────────────────────────────────────
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$HOME/.cloudflare" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.cloudflare"
fi

cd "$TF_DIR"

# ── Terraform init ────────────────────────────────────────────────────────────
echo "=== terraform init ==="
terraform init -input=false 2>&1 | grep -E '(Initializing|Installing|provider|Error|Warning)' || true
echo "Init complete."

# ── Terraform plan ───────────────────────────────────────────────────────────
echo "=== terraform plan ==="
terraform plan -input=false -out=tfplan
PLAN_SUMMARY=$(terraform show -no-color tfplan 2>/dev/null | grep "^Plan:" | head -1)
echo ""
echo "${PLAN_SUMMARY}"
echo ""

# ── Terraform apply ───────────────────────────────────────────────────────────
echo "=== terraform apply ==="
terraform apply -input=false -auto-approve tfplan
rm -f tfplan
echo "Apply complete."

# ── Capture outputs ───────────────────────────────────────────────────────────
EC2_HOST=$(terraform output -raw ec2_host)
FQDN=$(terraform output -raw fqdn)

# ── Push GitHub Secrets ───────────────────────────────────────────────────────
if gh auth status > /dev/null 2>&1; then
  echo "Pushing GitHub Secrets..."
  # SECURITY: SSH private key piped directly — never assigned to a variable
  terraform output -raw ssh_private_key | gh secret set EC2_SSH_PRIVATE_KEY
  echo "$EC2_HOST"   | gh secret set AWS_EC2_HOST
  echo "$AWS_REGION" | gh secret set AWS_REGION
  echo "$FQDN"       | gh secret set DEPLOY_DOMAIN
  echo "GitHub Secrets configured."
else
  echo "WARNING: gh CLI not authenticated — GitHub Secrets not pushed."
  echo "Run: gh auth login"
fi

# ── SSL verification ──────────────────────────────────────────────────────────
echo "Verifying SSL for https://$FQDN ..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 30 --max-filesize 1024 "https://$FQDN" 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
  SSL_CONFIGURED="true"
  echo "SSL verified (HTTP $HTTP_STATUS)"
else
  SSL_CONFIGURED="false"
  echo "WARNING: SSL not yet responding (HTTP $HTTP_STATUS)."
  echo "DNS propagation and certbot can take a few minutes — this is normal."
fi

# ── Write infraState to .state.json ──────────────────────────────────────────
APPLIED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SSL_BOOL=$([ "$SSL_CONFIGURED" = "true" ] && echo "true" || echo "false")

jq \
  --arg appliedAt "$APPLIED_AT" \
  --arg ec2Host "$EC2_HOST" \
  --arg fqdn "$FQDN" \
  --argjson appPort "$APP_PORT" \
  --arg tfDir "$TF_DIR" \
  --argjson sslConfigured "$SSL_BOOL" \
  '.infraState = {
    appliedAt: $appliedAt,
    ec2Host: $ec2Host,
    fqdn: $fqdn,
    appPort: $appPort,
    tfDir: $tfDir,
    nginxConfigured: true,
    sslConfigured: $sslConfigured,
    githubSecretsConfigured: true
  }' "$STATE_FILE" > "${STATE_FILE}.tmp" \
  && mv "${STATE_FILE}.tmp" "$STATE_FILE"

echo ""
echo "=== Infrastructure Provisioned ==="
echo "  EC2 Host:  $EC2_HOST"
echo "  Domain:    https://$FQDN"
echo "  SSH CIDR:  $SSH_CIDR"
echo "  SSL:       $([ "$SSL_BOOL" = "true" ] && echo "Ready" || echo "Provisioning (~5 min)")"
echo ""
echo "NOTE: Terraform state is at $TF_DIR/terraform.tfstate (gitignored)."
echo "      Do not delete this directory — it tracks provisioned resources."
echo ""
echo "Next: Run /c4flow:deploy to set up CI/CD."
