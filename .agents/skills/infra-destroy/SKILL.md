---
name: c4flow:infra-destroy
description: Tear down all AWS infrastructure provisioned by c4flow:infra — destroys EC2, VPC, Elastic IP, Cloudflare DNS record, and removes associated GitHub Secrets. Clears infraState from .state.json. Requires explicit double-confirmation before any destructive action. Use when the user runs /c4flow:infra-destroy or asks to "destroy infra", "tear down", or "clean up AWS resources".
---

# /c4flow:infra-destroy — Infrastructure Teardown

**Phase**: Release (cleanup)
**Agent type**: Main agent (interactive)

Destroys all AWS and Cloudflare resources created by `/c4flow:infra`, removes GitHub Secrets, and resets the infra state so you can provision fresh infrastructure later.

> **This is irreversible.** EC2 instances, VPCs, Elastic IPs, and DNS records will be permanently deleted. The Terraform state file is also removed. You cannot undo this without re-running `/c4flow:infra`.

---

## Step 0: Verify Cloudflare Credentials

`terraform destroy` calls the Cloudflare provider to remove the DNS record — it needs `CLOUDFLARE_API_TOKEN`. Run credential check before the user commits to destruction.

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SKILL_DIR/scripts/check-creds.sh"
```

AWS credentials are not checked here — Terraform reads `~/.aws/credentials` natively.

---

## Step 1: Read and Validate State

Read `docs/c4flow/.state.json`:

```bash
STATE_FILE="docs/c4flow/.state.json"

if [ ! -f "$STATE_FILE" ]; then
  echo "No .state.json found. Nothing to destroy."
  exit 0
fi

FEATURE_SLUG=$(jq -r '.feature.slug // empty' "$STATE_FILE")
APPLIED_AT=$(jq -r '.infraState.appliedAt // empty' "$STATE_FILE")
EC2_HOST=$(jq -r '.infraState.ec2Host // empty' "$STATE_FILE")
FQDN=$(jq -r '.infraState.fqdn // empty' "$STATE_FILE")
TF_DIR=$(jq -r '.infraState.tfDir // empty' "$STATE_FILE")
```

**If `infraState.appliedAt` is absent**: there is no provisioned infrastructure to destroy.

```
No infrastructure has been provisioned for this feature.
infraState is absent in .state.json — nothing to destroy.
```

Exit cleanly.

**If `TF_DIR` is absent but `infraState` exists**: Terraform state directory is missing. Show warning and continue to Step 2 — terraform destroy will be skipped, but GitHub Secrets cleanup and state reset will still run.

---

## Step 2: Show Destruction Summary

Display exactly what will be destroyed before asking for confirmation:

```
=== INFRASTRUCTURE DESTROY SUMMARY ===

Feature:     {feature.slug}
Provisioned: {infraState.appliedAt}

AWS resources to be destroyed (via terraform destroy):
  - EC2 instance       ({infraState.ec2Host})
  - Elastic IP         ({infraState.ec2Host})
  - VPC + subnets + route tables + internet gateway
  - Security group
  - SSH key pair

Cloudflare DNS record to be destroyed:
  - A record: {infraState.fqdn} → {infraState.ec2Host}

GitHub Secrets to be removed:
  - AWS_EC2_HOST
  - AWS_REGION
  - EC2_SSH_PRIVATE_KEY
  - DEPLOY_DOMAIN

Terraform state files to be deleted:
  - {infraState.tfDir}/terraform.tfstate
  - {infraState.tfDir}/terraform.tfstate.backup
  - {infraState.tfDir}/.terraform/

After destroy:
  - infraState will be cleared from .state.json
  - infraConfig.destroyedAt will be set
  - You can re-provision by running /c4flow:infra again

=====================================
```

---

## Step 3: Double Confirmation

**This is a destructive, irreversible action. Require two explicit confirmations.**

```bash
# First confirmation
echo ""
echo "WARNING: This will permanently delete all infrastructure listed above."
echo "Running applications will go offline immediately."
echo ""
read -p "Type 'destroy' to confirm: " CONFIRM1

if [ "$CONFIRM1" != "destroy" ]; then
  echo "Cancelled — you must type 'destroy' exactly."
  exit 0
fi

# Second confirmation — name the feature slug
echo ""
read -p "Confirm feature name (type '$FEATURE_SLUG' to proceed): " CONFIRM2

if [ "$CONFIRM2" != "$FEATURE_SLUG" ]; then
  echo "Cancelled — feature name did not match."
  exit 0
fi

echo ""
echo "Confirmed. Proceeding with destroy..."
```

---

## Step 4: Run Destroy Script

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SKILL_DIR/scripts/destroy-infra.sh" "$FEATURE_SLUG" "$EC2_HOST" "$FQDN"
```

---

## Key Safety Constraints

- **Double confirmation required**: user must type `destroy` AND the feature slug before anything is deleted
- **Terraform source `.tf` files are preserved** after destroy — only state files and the provider cache are deleted. This lets you inspect what was provisioned and re-apply if needed
- **GitHub Secrets removal is best-effort** — if `gh` is not authenticated, instructions are printed for manual removal
- **`infraConfig.destroyedAt` is written** so there is a permanent record of when infra was torn down, even after `infraState` is gone
