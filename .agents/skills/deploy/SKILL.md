---
name: c4flow:deploy
description: Set up GitHub Actions CI/CD and deploy the application to the EC2 infrastructure provisioned by c4flow:infra. Use when the user runs /c4flow:deploy or when the orchestrator advances to DEPLOY state. Requires infra to be provisioned first.
---

# /c4flow:deploy — CI/CD Setup & Deploy

**Phase**: 6: Release
**Agent type**: Main agent (interactive)
**Status**: Implemented

Generates a GitHub Actions SSH deploy workflow, commits it to the repo, triggers the first deployment, and monitors the run to completion.

---

## Step 1: infraState Gate Check

Read `docs/c4flow/.state.json`. Check:

```bash
NGINX_OK=$(jq -r '.infraState.nginxConfigured // false' docs/c4flow/.state.json 2>/dev/null)
SECRETS_OK=$(jq -r '.infraState.githubSecretsConfigured // false' docs/c4flow/.state.json 2>/dev/null)
FQDN=$(jq -r '.infraState.fqdn // empty' docs/c4flow/.state.json 2>/dev/null)
```

**If infraState is absent or either flag is not `true`**:

```
Infrastructure not provisioned. Run /c4flow:infra first.

Required:
  infraState.nginxConfigured:         {value or "missing"}
  infraState.githubSecretsConfigured: {value or "missing"}
```

Exit without proceeding.

---

## Step 2: Detect App Type and Write Entrypoint Script

Instead of interpolating the start command into the Actions YAML (injection risk), write a
`scripts/deploy-start.sh` to the repository. The workflow calls this script — keeping shell
logic out of the YAML and in a versioned, reviewable file.

```bash
mkdir -p scripts

detect_app_type() {
  if [ -f "package.json" ]; then
    echo "node"
  elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    echo "python"
  elif [ -f "go.mod" ]; then
    echo "go"
  else
    echo "generic"
  fi
}

APP_TYPE=$(detect_app_type)

case "$APP_TYPE" in
  node)
    cat > scripts/deploy-start.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd ~/app
npm install --production
pm2 restart app 2>/dev/null || pm2 start npm --name app -- start
EOF
    ;;
  python)
    cat > scripts/deploy-start.sh <<'EOF'
#!/bin/bash
set -euo pipefail
# PREREQUISITE: a systemd unit file /etc/systemd/system/app.service must exist on the EC2 instance.
# Create it manually or via cloud-init before the first deploy.
cd ~/app
pip install -r requirements.txt
sudo systemctl restart app
EOF
    ;;
  go)
    cat > scripts/deploy-start.sh <<'EOF'
#!/bin/bash
set -euo pipefail
# PREREQUISITE: a systemd unit file /etc/systemd/system/app.service must exist on the EC2 instance.
# Create it manually or via cloud-init before the first deploy.
cd ~/app
go build -o app .
sudo systemctl restart app
EOF
    ;;
  *)
    cat > scripts/deploy-start.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd ~/app
# TODO: Add your application start command here
sudo systemctl restart app
EOF
    echo "NOTE: Generic entrypoint written to scripts/deploy-start.sh."
    echo "Review and update the start command before the first deploy."
    ;;
esac

chmod +x scripts/deploy-start.sh
echo "Entrypoint script written: scripts/deploy-start.sh (app type: $APP_TYPE)"
```

---

## Step 3: Generate GitHub Actions Workflow

The workflow calls `scripts/deploy-start.sh` over SSH — no shell command interpolation in the YAML.
The `appleboy/ssh-action` is pinned to a commit SHA to prevent supply-chain attacks via mutable tags.

```bash
mkdir -p .github/workflows

cat > .github/workflows/deploy.yml <<'EOF'
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

      - name: Deploy to EC2
        # Pinned to SHA — mutable tags (v1.2.5) can be silently updated by the author.
        # This SHA corresponds to appleboy/ssh-action v1.2.5.
        # To update: verify the new SHA at https://github.com/appleboy/ssh-action
        uses: appleboy/ssh-action@0ff4204d59e8e51228ff73bce53f80d53301dee2  # v1.2.5
        with:
          host: ${{ secrets.AWS_EC2_HOST }}
          username: ec2-user
          key: ${{ secrets.EC2_SSH_PRIVATE_KEY }}
          timeout: 300s
          script: |
            set -euo pipefail
            # Pull latest code
            if [ -d ~/app ]; then
              cd ~/app && git fetch origin main && git reset --hard origin/main
            else
              git clone https://github.com/${{ github.repository }} ~/app && cd ~/app
            fi
            # Run the versioned entrypoint script
            bash ~/app/scripts/deploy-start.sh

      - name: Health Check
        run: |
          echo "Waiting for app to start..."
          sleep 10
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time 30 \
            --max-filesize 1024 \
            --retry 5 \
            --retry-delay 5 \
            "https://${{ secrets.DEPLOY_DOMAIN }}/")
          echo "Health check status: $STATUS"
          if [ "$STATUS" != "200" ] && [ "$STATUS" != "301" ] && [ "$STATUS" != "302" ]; then
            echo "Health check failed (HTTP $STATUS)"
            exit 1
          fi
          echo "Deploy successful! Live at: https://${{ secrets.DEPLOY_DOMAIN }}"
EOF
```

---

## Step 4: Commit and Push

```bash
git add .github/workflows/deploy.yml scripts/deploy-start.sh

git diff --cached --stat

git commit -m "ci: add GitHub Actions deploy workflow and entrypoint script"

git push origin main

echo "Workflow committed and pushed to main."
```

---

## Step 5: Trigger and Monitor Deploy

```bash
echo "Waiting for GitHub Actions to pick up the workflow run..."
sleep 8

# Get the latest run ID for the deploy workflow
RUN_ID=$(gh run list --workflow=deploy.yml --limit=1 --json databaseId --jq '.[0].databaseId' 2>/dev/null)

if [ -z "$RUN_ID" ]; then
  # Trigger manually if not auto-triggered
  gh workflow run deploy.yml
  sleep 8
  RUN_ID=$(gh run list --workflow=deploy.yml --limit=1 --json databaseId --jq '.[0].databaseId')
fi

echo "Monitoring workflow run $RUN_ID ..."
echo "(Press Ctrl+C to stop monitoring — the deploy continues in the background)"
echo ""

gh run watch "$RUN_ID"
```

---

## Step 6: Report Result

```bash
RUN_STATUS=$(gh run view "$RUN_ID" --json conclusion --jq '.conclusion' 2>/dev/null)
FQDN=$(jq -r '.infraState.fqdn' docs/c4flow/.state.json)

if [ "$RUN_STATUS" = "success" ]; then
  echo ""
  echo "=== Deploy Succeeded ==="
  echo "Live at: https://$FQDN"
  echo ""
  echo "The c4flow workflow is complete."
  # Orchestrator advances currentState to DONE
else
  echo ""
  echo "=== Deploy Failed ==="
  echo ""
  echo "SECURITY NOTE: The following log excerpt may contain application output."
  echo "Do not share it publicly if your app logs credentials or PII."
  echo ""
  echo "--- Last 20 lines of failed steps ---"
  # Fetch only failed step logs, limit size to avoid context bloat
  gh run view "$RUN_ID" --log-failed 2>/dev/null | tail -20 || \
    gh run view "$RUN_ID" --log 2>/dev/null | tail -20
  echo "--- end of log excerpt ---"
  echo ""
  echo "Options:"
  echo "  1. Fix the issue and push to main (workflow re-runs automatically)"
  echo "  2. Re-run the failed job: gh run rerun $RUN_ID --failed"
  echo "  3. Full logs: gh run view $RUN_ID --log"
  echo ""
  echo "State NOT advanced — re-run /c4flow:deploy once the issue is fixed."
fi
```

On **success**: the orchestrator adds `DEPLOY` to `completedStates` and sets `currentState` to `DONE`.

On **failure**: state is not advanced. User fixes the issue and re-runs `/c4flow:deploy`.

---

## Key Security Constraints

- **No shell command interpolation in YAML** — start commands live in `scripts/deploy-start.sh`, not the workflow
- **SHA-pin all third-party Actions** — mutable tags can be silently updated by the author
- **Never commit secrets** — workflow uses `${{ secrets.* }}` references only
- **Log excerpts may contain sensitive app output** — warn user before printing, never log to persistent files
- **Gate is hard** — if `infraState.nginxConfigured` or `githubSecretsConfigured` is not `true`, exit immediately
- **`gh run watch` interruption is safe** — the GitHub Actions run continues in the cloud regardless
