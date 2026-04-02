#!/usr/bin/env bash
# check-creds.sh — Verify Cloudflare credentials exist before infra teardown
# terraform destroy calls the Cloudflare provider to remove the DNS record — it needs CLOUDFLARE_API_TOKEN.
# Exit 0 = credentials present, exit 1 = missing credentials

set -euo pipefail

# Check env var first; fall back to ~/.cloudflare dotfile
if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "✓ CLOUDFLARE_API_TOKEN: [set via env]"
elif [ -f "$HOME/.cloudflare" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.cloudflare" 2>/dev/null
  if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
    echo "✓ CLOUDFLARE_API_TOKEN: [loaded from ~/.cloudflare]"
  else
    echo "✗ CLOUDFLARE_API_TOKEN: ~/.cloudflare exists but does not export the token"
    echo ""
    echo "ERROR: Cannot proceed — terraform destroy will fail without Cloudflare credentials."
    echo "Fix: add 'export CLOUDFLARE_API_TOKEN=your-token-here' to ~/.cloudflare, then re-run."
    exit 1
  fi
else
  echo "✗ CLOUDFLARE_API_TOKEN: not found"
  echo ""
  echo "ERROR: Cannot proceed — terraform destroy will fail without Cloudflare credentials."
  echo "Fix: create ~/.cloudflare with your token:"
  echo "  cat > ~/.cloudflare <<'EOF'"
  echo "  export CLOUDFLARE_API_TOKEN=your-token-here"
  echo "  EOF"
  echo "  chmod 600 ~/.cloudflare"
  echo "Then re-run /c4flow:infra-destroy."
  exit 1
fi

# AWS credentials are not checked here — Terraform reads ~/.aws/credentials natively.

exit 0
