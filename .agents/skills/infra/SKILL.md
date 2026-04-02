---
name: c4flow:infra
description: Provision AWS EC2 + nginx + SSL infrastructure and Cloudflare DNS for the current C4Flow feature. Use when the user runs /c4flow:infra or when the orchestrator advances to INFRA state.
---

# /c4flow:infra — Infrastructure Provisioning

**Phase**: 6: Release
**Agent type**: Main agent (interactive)

Provisions EC2 + nginx + Let's Encrypt SSL on AWS and creates a Cloudflare DNS subdomain via Terraform. Pushes outputs to GitHub Secrets so the DEPLOY phase can run CI/CD without manual configuration.

> **Agent execution model**: All bash commands in this skill MUST be run by the agent using the `Bash` tool. Never tell the user to run commands manually.

---

## Step 0: Verify Credentials

Run credential check **before anything else**:

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SKILL_DIR/scripts/check-creds.sh"
```

Exits with guide if credentials are missing.

---

## Step 1: Read State

Read `docs/c4flow/.state.json`. Extract:
- `feature.slug` — used for terraform directory path
- `infraConfig` — existing config (may be partial or absent)
- `infraState` — if present, trigger re-run guard

If `.state.json` is missing or `feature` is null, halt:
```
No active feature found. Run /c4flow:run to start a feature workflow first.
```

**Re-run guard**: If `infraState.appliedAt` is present:
```
Infrastructure already provisioned.
  Host:    {infraState.ec2Host}
  Domain:  {infraState.fqdn}
  Applied: {infraState.appliedAt}

Re-provision? [y/N]
```
If user answers anything other than `y` or `yes`, exit and suggest running `/c4flow:deploy` to continue.

---

## Step 2: Resolve and Validate Config

Resolve each field using this priority order:
1. Existing value in `.state.json` `infraConfig`
2. Environment variable (detect presence with `[ -n "$VAR" ]` — **never print the value**)
3. Interactive prompt (last resort)

For **sensitive** env vars: display `[configured via env]` only. For **non-sensitive** defaults: show the computed default and ask for confirmation.

### Fields to resolve

| Field | Env var | Default | Sensitive? |
|-------|---------|---------|------------|
| `domain` | `C4FLOW_DOMAIN` | — | No |
| `subdomain` | `C4FLOW_SUBDOMAIN` | `basename $(pwd)` | No |
| `awsRegion` | `C4FLOW_AWS_REGION` or `AWS_DEFAULT_REGION` | `us-east-1` | No |
| `appPort` | — | `3000` | No |
| `certbotEmail` | — | — | No |
| `cloudflareZoneId` | `CLOUDFLARE_ZONE_ID` | — | No |
| `sshCidr` | — | current machine IP + /32 | No |
| Cloudflare API token | `CLOUDFLARE_API_TOKEN` | — | **Yes — never stored/displayed** |
| AWS credentials | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | — | **Yes — never stored/displayed** |

**Prompt format**:
```bash
# Sensitive env var detected:
Domain: [configured via env]  Use it? [Y/n]

# Non-sensitive default:
Subdomain: [default: my-app]  Use it? [Y/n]

# Nothing available:
Enter domain: _

# certbot email (always prompt — must be real):
Certbot email (for Let's Encrypt expiry notices): _

# SSH CIDR (restrict who can SSH to the instance):
SSH access CIDR [default: <your-current-ip>/32, or 0.0.0.0/0 for any]: _
```

Detect current IP for SSH CIDR default:
```bash
CURRENT_IP=$(curl -s --max-time 5 https://checkip.amazonaws.com 2>/dev/null || echo "")
SSH_CIDR_DEFAULT="${CURRENT_IP:+${CURRENT_IP}/32}"
SSH_CIDR_DEFAULT="${SSH_CIDR_DEFAULT:-0.0.0.0/0}"
```

### Validation — REQUIRED before proceeding

**Run these checks before writing anything or generating Terraform. Halt on any failure.**

```bash
# Validate subdomain: lowercase alphanumeric + hyphens, no leading/trailing hyphen, max 63 chars
if ! echo "$SUBDOMAIN" | grep -qE '^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'; then
  echo "ERROR: Invalid subdomain '$SUBDOMAIN'."
  echo "Must be lowercase letters, numbers, and hyphens only. No leading/trailing hyphens. Max 63 chars."
  exit 1
fi

# Validate domain: basic FQDN
if ! echo "$DOMAIN" | grep -qE '^([a-z0-9][a-z0-9-]{0,61}[a-z0-9]\.)+[a-z]{2,}$'; then
  echo "ERROR: Invalid domain '$DOMAIN'."
  echo "Must be a valid fully-qualified domain name (e.g. example.com)."
  exit 1
fi

# Validate appPort: integer 1-65535
if ! echo "$APP_PORT" | grep -qE '^[0-9]+$' || [ "$APP_PORT" -lt 1 ] || [ "$APP_PORT" -gt 65535 ]; then
  echo "ERROR: Invalid app port '$APP_PORT'. Must be a number between 1 and 65535."
  exit 1
fi

# Validate certbotEmail: basic email format
if ! echo "$CERTBOT_EMAIL" | grep -qE '^[^@]+@[^@]+\.[^@]+$'; then
  echo "ERROR: Invalid email '$CERTBOT_EMAIL'."
  exit 1
fi

# Validate sshCidr: CIDR format
if ! echo "$SSH_CIDR" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$'; then
  echo "ERROR: Invalid CIDR '$SSH_CIDR'. Must be in format x.x.x.x/n"
  exit 1
fi

# Validate cloudflareZoneId: 32 hex chars
if ! echo "$CF_ZONE_ID" | grep -qE '^[a-f0-9]{32}$'; then
  echo "ERROR: Invalid Cloudflare Zone ID. Must be a 32-character hex string."
  exit 1
fi
```

### Write resolved config to .state.json

Only write fields NOT sourced from env vars:

```bash
STATE_FILE="docs/c4flow/.state.json"
EXISTING=$(cat "$STATE_FILE")

# DOMAIN_EXPLICIT, CF_ZONE_ID_EXPLICIT are set only when user typed the value (not from env)
NEW_STATE=$(echo "$EXISTING" | jq \
  --arg subdomain "$SUBDOMAIN" \
  --arg awsRegion "$AWS_REGION" \
  --argjson appPort "$APP_PORT" \
  --arg sshCidr "$SSH_CIDR" \
  --arg certbotEmail "$CERTBOT_EMAIL" \
  --arg domain "${DOMAIN_EXPLICIT:-}" \
  --arg cfZoneId "${CF_ZONE_ID_EXPLICIT:-}" \
  '.infraConfig = {
    subdomain: $subdomain,
    awsRegion: $awsRegion,
    appPort: $appPort,
    sshCidr: $sshCidr,
    certbotEmail: $certbotEmail
  }
  | if $domain != "" then .infraConfig.domain = $domain else . end
  | if $cfZoneId != "" then .infraConfig.cloudflareZoneId = $cfZoneId else . end')

echo "$NEW_STATE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
```

---

## Step 3: Generate Terraform Files

Create directory and gitignore **first**:

```bash
TF_DIR="docs/c4flow/terraform/${FEATURE_SLUG}"
mkdir -p "$TF_DIR"

# SECURITY: gitignore the entire terraform directory to prevent committing
# state files (contain SSH private key), plan artifacts, and variable files.
cat > "$TF_DIR/.gitignore" <<'EOF'
# Terraform state — contains SSH private key in plaintext
*.tfstate
*.tfstate.backup

# Terraform plan artifact — contains sensitive state snapshot
tfplan
tfplan.out

# Terraform provider cache
.terraform/
.terraform.lock.hcl

# Variable files — contain infra topology (zone IDs, etc.)
*.tfvars
*.tfvars.json
EOF
```

**Terraform HCL**: Copy the blocks from [references/terraform-templates.md](references/terraform-templates.md):
- `variables.tf` — copy from the reference file
- `main.tf` — copy from the reference file
- `outputs.tf` — copy from the reference file

Then write `terraform.tfvars`:

```hcl
aws_region         = "{awsRegion}"
domain             = "{domain}"
subdomain          = "{subdomain}"
app_port           = {appPort}
cloudflare_zone_id = "{cloudflareZoneId}"
ssh_cidr           = "{sshCidr}"
certbot_email      = "{certbotEmail}"
```

---

## Step 4: Terraform Apply

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SKILL_DIR/scripts/apply-infra.sh" \
  "$FEATURE_SLUG" "$AWS_REGION" "$APP_PORT" "$SSH_CIDR" "$CERTBOT_EMAIL"
```

---

## Key Security Constraints

- **Never print sensitive env var values** — only acknowledge `[configured via env]`
- **Never write** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `CLOUDFLARE_API_TOKEN` to any file
- **Never capture `terraform output -json`** — always use `terraform output -raw <name>`
- **SSH private key must only flow through a pipe** directly to `gh secret set` — never assigned to a variable
- **Validate subdomain and domain** before any shell interpolation
- **Terraform state is local and gitignored** — warn user not to delete `docs/c4flow/terraform/`
