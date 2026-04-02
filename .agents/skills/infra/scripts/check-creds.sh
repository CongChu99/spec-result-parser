#!/usr/bin/env bash
# check-creds.sh — Verify AWS + Cloudflare credentials exist before infra provisioning
# Exit 0 = all credentials present, exit 1 = missing credentials

set -euo pipefail

ERRORS=""

# ── AWS ──────────────────────────────────────────────────────────────────────
if command -v aws &>/dev/null; then
  AWS_ID_OUTPUT=$(aws sts get-caller-identity 2>&1)
  if echo "$AWS_ID_OUTPUT" | grep -q '"Account"'; then
    AWS_ACCOUNT=$(echo "$AWS_ID_OUTPUT" | grep '"Account"' | sed 's/.*"Account": *"\([^"]*\)".*/\1/')
    echo "✓ AWS: authenticated (account: $AWS_ACCOUNT)"
  else
    echo "✗ AWS: not authenticated"
    ERRORS="${ERRORS}AWS_MISSING"
  fi
else
  if [ -f "$HOME/.aws/credentials" ] && grep -q "aws_access_key_id" "$HOME/.aws/credentials"; then
    echo "✓ AWS: ~/.aws/credentials found (aws CLI not installed, Terraform will use file directly)"
  elif [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    echo "✓ AWS: credentials found via environment variables"
  else
    echo "✗ AWS: no credentials found"
    ERRORS="${ERRORS}AWS_MISSING"
  fi
fi

# ── Cloudflare ────────────────────────────────────────────────────────────────
if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "✓ CLOUDFLARE_API_TOKEN: [set via env]"
elif [ -f "$HOME/.cloudflare" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.cloudflare" 2>/dev/null
  if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
    echo "✓ CLOUDFLARE_API_TOKEN: [loaded from ~/.cloudflare]"
  else
    echo "✗ CLOUDFLARE_API_TOKEN: ~/.cloudflare exists but does not export the token"
    ERRORS="${ERRORS}CF_MISSING"
  fi
  if [ -n "${CLOUDFLARE_ZONE_ID:-}" ]; then
    echo "✓ CLOUDFLARE_ZONE_ID: [loaded from ~/.cloudflare]"
  fi
else
  echo "✗ CLOUDFLARE_API_TOKEN: not found"
  ERRORS="${ERRORS}CF_MISSING"
fi

# ── Halt with full guide ─────────────────────────────────────────────────────
if [ -n "$ERRORS" ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "ERROR: Missing credentials — cannot proceed."
  echo "Fix the items marked ✗ above, then re-run /c4flow:infra."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if echo "$ERRORS" | grep -q "AWS_MISSING"; then
    cat <<'AWS_GUIDE'

  ── AWS credentials ──────────────────────────────────────────────
  Recommended (stores keys in ~/.aws/credentials, read by all AWS tools):

    aws configure
    → Enter Access Key ID, Secret Access Key, region (e.g. us-east-1)

  If using SSO:
    aws configure sso
    aws sso login

  AWS credentials are NEVER stored or printed by this skill.
  ~/.aws/credentials is gitignored by default — do not commit it.
AWS_GUIDE
  fi

  if echo "$ERRORS" | grep -q "CF_MISSING"; then
    cat <<'CF_GUIDE'

  ── Cloudflare API token ─────────────────────────────────────────
  SECURITY: Use a scoped token — never the Global API Key.

  1. Create token at: https://dash.cloudflare.com/profile/api-tokens
     → "Create Custom Token"
     → Permissions: Zone > DNS > Edit
     → Zone Resources: your domain only

  2. Store it (and your Zone ID) in a dedicated dotfile:
     cat > ~/.cloudflare <<'EOF'
     export CLOUDFLARE_API_TOKEN=your-token-here
     export CLOUDFLARE_ZONE_ID=your-32-char-zone-id-here
     EOF
     chmod 600 ~/.cloudflare   # restrict to your user only

  Zone ID: found in the Cloudflare dashboard → your domain → Overview → right sidebar.

  3. Auto-load in every new terminal:
     echo '[ -f ~/.cloudflare ] && source ~/.cloudflare' >> ~/.zshrc

  4. Load now without restarting:
     source ~/.cloudflare
     Then re-run /c4flow:infra.

  NEVER commit ~/.cloudflare or paste the token into any file in the repo.
CF_GUIDE
  fi

  exit 1
fi

exit 0
