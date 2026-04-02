#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MODULE_DIR="$ROOT_DIR/skills/init/terraform/github-bootstrap"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required for this test" >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required for this test" >&2
  exit 1
fi

run_case() {
  local name="$1"
  local tfvars_json="$2"
  shift 2

  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' RETURN

  cp -f "$MODULE_DIR"/*.tf "$tmpdir"/
  printf '%s\n' "$tfvars_json" > "$tmpdir/terraform.tfvars.json"

  (
    cd "$tmpdir"
    terraform init -input=false >/tmp/c4flow-init-test-init.log 2>&1
    env "$@" terraform validate >/tmp/c4flow-init-test-validate.log 2>&1
  ) || {
    echo "case failed: $name" >&2
    echo "--- validate log ---" >&2
    tail -n 80 /tmp/c4flow-init-test-validate.log >&2 || true
    exit 1
  }
}

run_case \
  "token-mode" \
  '{
    "github_owner": "example",
    "github_repo": "example-repo",
    "github_visibility": "public",
    "repo_description": "test",
    "delete_branch_on_merge": true,
    "enable_coderabbit_installation": false,
    "coderabbit_installation_id": "",
    "default_branch": "main",
    "github_auth_mode": "token",
    "github_app_id": "",
    "github_app_installation_id": "",
    "github_app_pem_file": ""
  }' \
  GITHUB_TOKEN=dummy

app_pem_file="$(mktemp)"
openssl genrsa -traditional -out "$app_pem_file" 2048 >/dev/null 2>&1
app_pem_content="$(cat "$app_pem_file")"
rm -f "$app_pem_file"

run_case \
  "app-mode" \
  '{
    "github_owner": "example",
    "github_repo": "example-repo",
    "github_visibility": "public",
    "repo_description": "test",
    "delete_branch_on_merge": true,
    "enable_coderabbit_installation": false,
    "coderabbit_installation_id": "",
    "default_branch": "main",
    "github_auth_mode": "app",
    "github_app_id": "12345",
    "github_app_installation_id": "67890"
  }' \
  "TF_VAR_github_app_pem_file=$app_pem_content"

echo "github bootstrap auth mode tests passed"
