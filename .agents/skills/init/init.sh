#!/usr/bin/env bash
# c4flow init — install and configure dependencies for C4Flow workflow
# Usage: skills/init/init.sh [--skip-beads] [--prefix PREFIX] [--remote URL] [--github|--no-github] [--github-owner OWNER] [--github-repo REPO] [--github-visibility VISIBILITY] [--coderabbit|--no-coderabbit] [--coderabbit-installation-id ID]
#
# Installs Dolt + Beads, runs bd init, configures DoltHub sync, and can optionally bootstrap GitHub + CodeRabbit.
# Target: complete in under 30 seconds.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITHUB_BOOTSTRAP_DIR="$SCRIPT_DIR/terraform/github-bootstrap"
CODERABBIT_TEMPLATE="$SCRIPT_DIR/templates/coderabbit.yaml"

# Colors (disable if not a terminal)
if [ -t 1 ]; then
  RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[0;33m' BLUE='\033[0;34m' NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

info()  { echo -e "${BLUE}[c4flow]${NC} $*"; }
ok()    { echo -e "${GREEN}[c4flow]${NC} $*"; }
warn()  { echo -e "${YELLOW}[c4flow]${NC} $*"; }
err()   { echo -e "${RED}[c4flow]${NC} $*" >&2; }

# Run a command with a timeout (default 15s)
run_with_timeout() {
  local secs="${1:-15}"
  shift
  if command -v timeout &>/dev/null; then
    timeout "$secs" "$@" 2>&1
  else
    perl -e "alarm $ARGV[0]; exec @ARGV[1..$#ARGV]" "$secs" "$@" 2>&1
  fi
}

# Parse args
SKIP_BEADS=false
PREFIX=""
REMOTE=""
GITHUB_MODE="prompt"
GITHUB_OWNER="${GITHUB_OWNER:-}"
GITHUB_REPO=""
GITHUB_VISIBILITY="private"
CODERABBIT_MODE="prompt"
CODERABBIT_INSTALLATION_ID=""
GITHUB_AUTH_MODE=""
GITHUB_BOOTSTRAP_FULL_NAME=""
GITHUB_BOOTSTRAP_HTML_URL=""
GITHUB_BOOTSTRAP_HTTP_CLONE_URL=""
CODERABBIT_CONFIG_CHANGED=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-beads) SKIP_BEADS=true; shift ;;
    --prefix)     PREFIX="$2"; shift 2 ;;
    --prefix=*)   PREFIX="${1#*=}"; shift ;;
    --remote)     REMOTE="$2"; shift 2 ;;
    --remote=*)   REMOTE="${1#*=}"; shift ;;
    --github)     GITHUB_MODE="yes"; shift ;;
    --no-github)  GITHUB_MODE="no"; shift ;;
    --github-owner)   GITHUB_OWNER="$2"; shift 2 ;;
    --github-owner=*) GITHUB_OWNER="${1#*=}"; shift ;;
    --github-repo)    GITHUB_REPO="$2"; shift 2 ;;
    --github-repo=*)  GITHUB_REPO="${1#*=}"; shift ;;
    --github-visibility)   GITHUB_VISIBILITY="$2"; shift 2 ;;
    --github-visibility=*) GITHUB_VISIBILITY="${1#*=}"; shift ;;
    --coderabbit)    CODERABBIT_MODE="yes"; shift ;;
    --no-coderabbit) CODERABBIT_MODE="no"; shift ;;
    --coderabbit-installation-id)   CODERABBIT_INSTALLATION_ID="$2"; shift 2 ;;
    --coderabbit-installation-id=*) CODERABBIT_INSTALLATION_ID="${1#*=}"; shift ;;
    -h|--help)
      echo "Usage: init.sh [--skip-beads] [--prefix PREFIX] [--remote URL] [--github|--no-github] [--github-owner OWNER] [--github-repo REPO] [--github-visibility VISIBILITY] [--coderabbit|--no-coderabbit] [--coderabbit-installation-id ID]"
      echo ""
      echo "Options:"
      echo "  --skip-beads    Skip Beads (bd) installation"
      echo "  --prefix NAME   Set beads issue prefix (default: directory name)"
      echo "  --remote URL    DoltHub repo URL for auto-sync"
      echo "                  Accepts: https://www.dolthub.com/repositories/org/repo"
      echo "                       or: https://doltremoteapi.dolthub.com/org/repo"
      echo "  --github        Enable optional GitHub repository bootstrap without prompting"
      echo "  --no-github     Skip GitHub repository bootstrap without prompting"
      echo "  --github-owner  GitHub owner (organization or personal account)"
      echo "  --github-repo   GitHub repository name (default: current directory name)"
      echo "  --github-visibility VISIBILITY"
      echo "                  GitHub repository visibility: public, private, or internal"
      echo "  --coderabbit    Enable optional CodeRabbit setup without prompting"
      echo "  --no-coderabbit Skip CodeRabbit setup without prompting"
      echo "  --coderabbit-installation-id ID"
      echo "                  Existing CodeRabbit GitHub App installation ID for auto-attach"
      echo "  -h, --help      Show this help"
      exit 0
      ;;
    *) err "Unknown option: $1"; exit 1 ;;
  esac
done

has() { command -v "$1" &>/dev/null; }

confirm() {
  local prompt="$1"
  local reply
  read -r -p "$prompt [y/N] " reply
  [[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]
}

require_value() {
  local current="$1"
  local prompt="$2"
  if [ -n "$current" ]; then
    printf '%s\n' "$current"
    return 0
  fi
  read -r -p "$prompt: " current
  printf '%s\n' "$current"
}

default_github_repo_name() {
  basename "$(pwd)"
}

current_branch_name() {
  git branch --show-current
}

validate_github_visibility() {
  case "$GITHUB_VISIBILITY" in
    public|private|internal) ;;
    *)
      err "Invalid GitHub visibility: $GITHUB_VISIBILITY (expected public, private, or internal)"
      exit 1
      ;;
  esac
}

# ─── Git ──────────────────────────────────────────────────────────────────────

setup_git() {
  if ! has git; then
    info "Installing git..."
    if has apt-get; then
      sudo apt-get install -y git
    elif has brew; then
      brew install git
    elif has dnf; then
      sudo dnf install -y git
    elif has pacman; then
      sudo pacman -S --noconfirm git
    else
      err "Cannot install git: no supported package manager found."
      exit 1
    fi
    has git || { err "Git installation failed"; exit 1; }
  fi

  if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    info "Not inside a git repository. Initializing..."
    git init
    # Set default branch to main if not configured
    git symbolic-ref HEAD refs/heads/main 2>/dev/null || true
    # Create initial commit so branch exists
    git commit --allow-empty -m "chore: initial commit" 2>/dev/null || true
    ok "git: initialized new repository"
  else
    ok "git: $(git --version)"
  fi
}

detect_github_auth_mode() {
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    echo "token"
    return 0
  fi

  if [ -n "${GITHUB_APP_ID:-}" ] && [ -n "${GITHUB_APP_INSTALLATION_ID:-}" ] && [ -n "${GITHUB_APP_PEM_FILE:-}" ]; then
    echo "app"
    return 0
  fi

  return 1
}

require_github_auth() {
  if ! GITHUB_AUTH_MODE="$(detect_github_auth_mode)"; then
    err "GitHub bootstrap requires GITHUB_TOKEN or all of GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, and GITHUB_APP_PEM_FILE."
    exit 1
  fi
}

require_terraform() {
  if ! has terraform; then
    err "Terraform is required for GitHub bootstrap. Install terraform and rerun /c4flow:init."
    exit 1
  fi
}

write_github_bootstrap_tfvars() {
  local enable_coderabbit_installation="$1"
  local coderabbit_installation_id="$2"

  cat > "$GITHUB_BOOTSTRAP_DIR/terraform.tfvars.json" <<EOF
{
  "github_owner": "$GITHUB_OWNER",
  "github_repo": "$GITHUB_REPO",
  "github_visibility": "$GITHUB_VISIBILITY",
  "repo_description": "Bootstrapped by c4flow:init",
  "delete_branch_on_merge": true,
  "enable_coderabbit_installation": $enable_coderabbit_installation,
  "coderabbit_installation_id": "$coderabbit_installation_id",
  "default_branch": "main",
  "github_auth_mode": "$GITHUB_AUTH_MODE"
}
EOF
}

terraform_init_github_bootstrap() {
  # The Terraform module creates github_repository and optional github_app_installation_repository resources.
  if [ "$GITHUB_AUTH_MODE" = "app" ]; then
    run_with_timeout 60 env \
      "TF_VAR_github_app_id=${GITHUB_APP_ID:-}" \
      "TF_VAR_github_app_installation_id=${GITHUB_APP_INSTALLATION_ID:-}" \
      "TF_VAR_github_app_pem_file=${GITHUB_APP_PEM_FILE:-}" \
      terraform -chdir="$GITHUB_BOOTSTRAP_DIR" init -input=false
    return
  fi

  run_with_timeout 60 terraform -chdir="$GITHUB_BOOTSTRAP_DIR" init -input=false
}

terraform_apply_github_bootstrap() {
  if [ "$GITHUB_AUTH_MODE" = "app" ]; then
    run_with_timeout 120 env \
      "TF_VAR_github_app_id=${GITHUB_APP_ID:-}" \
      "TF_VAR_github_app_installation_id=${GITHUB_APP_INSTALLATION_ID:-}" \
      "TF_VAR_github_app_pem_file=${GITHUB_APP_PEM_FILE:-}" \
      terraform -chdir="$GITHUB_BOOTSTRAP_DIR" apply -input=false -auto-approve
    return
  fi

  run_with_timeout 120 terraform -chdir="$GITHUB_BOOTSTRAP_DIR" apply -input=false -auto-approve
}

terraform_output_github_bootstrap() {
  local key="$1"
  if [ "$GITHUB_AUTH_MODE" = "app" ]; then
    env \
      "TF_VAR_github_app_id=${GITHUB_APP_ID:-}" \
      "TF_VAR_github_app_installation_id=${GITHUB_APP_INSTALLATION_ID:-}" \
      "TF_VAR_github_app_pem_file=${GITHUB_APP_PEM_FILE:-}" \
      terraform -chdir="$GITHUB_BOOTSTRAP_DIR" output -raw "$key"
    return
  fi

  terraform -chdir="$GITHUB_BOOTSTRAP_DIR" output -raw "$key"
}

configure_origin_remote() {
  local target_url="$1"

  if git remote get-url origin >/dev/null 2>&1; then
    local existing
    existing="$(git remote get-url origin)"
    if [ "$existing" != "$target_url" ]; then
      if ! confirm "This repo already has an origin remote. Do you want to replace it?"; then
        err "Aborting GitHub bootstrap because origin replacement was declined."
        exit 1
      fi
      git remote remove origin
    fi
  fi

  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$target_url"
  fi
}

push_initial_branch() {
  local branch
  branch="$(current_branch_name)"
  if [ -z "$branch" ]; then
    err "Cannot determine current branch for the initial push."
    exit 1
  fi

  git push -u origin "$branch"
}

verify_remote_branch() {
  local branch
  branch="$(current_branch_name)"
  git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1
}

maybe_setup_github_repo() {
  case "$GITHUB_MODE" in
    no) return 0 ;;
    yes) ;;
    prompt)
      if ! confirm "Do you want to create/manage a GitHub repository for this project?"; then
        return 0
      fi
      ;;
  esac

  require_terraform
  require_github_auth

  if [ -z "$GITHUB_REPO" ]; then
    GITHUB_REPO="$(default_github_repo_name)"
  fi

  GITHUB_OWNER="$(require_value "$GITHUB_OWNER" "GitHub owner")"
  GITHUB_REPO="$(require_value "$GITHUB_REPO" "GitHub repository name")"
  validate_github_visibility

  write_github_bootstrap_tfvars false ""
  terraform_init_github_bootstrap
  terraform_apply_github_bootstrap

  GITHUB_BOOTSTRAP_FULL_NAME="$(terraform_output_github_bootstrap full_name)"
  GITHUB_BOOTSTRAP_HTML_URL="$(terraform_output_github_bootstrap html_url)"
  GITHUB_BOOTSTRAP_HTTP_CLONE_URL="$(terraform_output_github_bootstrap http_clone_url)"

  configure_origin_remote "$GITHUB_BOOTSTRAP_HTTP_CLONE_URL"
  push_initial_branch

  if verify_remote_branch; then
    ok "GitHub repository ready: $GITHUB_BOOTSTRAP_FULL_NAME"
  else
    err "GitHub repository was created but branch verification failed."
    exit 1
  fi
}

ensure_coderabbit_config() {
  if [ ! -f "$CODERABBIT_TEMPLATE" ]; then
    err "CodeRabbit template not found: $CODERABBIT_TEMPLATE"
    exit 1
  fi

  if [ -f ".coderabbit.yaml" ]; then
    if confirm "A .coderabbit.yaml file already exists. Do you want to replace it?"; then
      cp -f "$CODERABBIT_TEMPLATE" .coderabbit.yaml
      CODERABBIT_CONFIG_CHANGED=true
    fi
    return 0
  fi

  cp -f "$CODERABBIT_TEMPLATE" .coderabbit.yaml
  CODERABBIT_CONFIG_CHANGED=true
}

can_autocommit_coderabbit_config() {
  local status filtered
  status="$(git status --porcelain)"
  filtered="$(printf '%s\n' "$status" | sed '/\.coderabbit\.yaml$/d' | sed '/^$/d')"
  [ -z "$filtered" ]
}

commit_and_push_coderabbit_config() {
  git add .coderabbit.yaml
  if git diff --cached --quiet; then
    return 0
  fi

  git commit -m "chore: add CodeRabbit config"
  git push origin "$(current_branch_name)"
}

maybe_attach_coderabbit_installation() {
  if [ -z "$CODERABBIT_INSTALLATION_ID" ]; then
    return 1
  fi

  require_terraform
  require_github_auth

  write_github_bootstrap_tfvars true "$CODERABBIT_INSTALLATION_ID"
  terraform_apply_github_bootstrap
  ok "CodeRabbit installation attached to $GITHUB_OWNER/$GITHUB_REPO"
  return 0
}

maybe_setup_coderabbit() {
  case "$CODERABBIT_MODE" in
    no) return 0 ;;
    yes) ;;
    prompt)
      if ! confirm "Do you want to set up CodeRabbit for this repository?"; then
        return 0
      fi
      ;;
  esac

  ensure_coderabbit_config

  if ! maybe_attach_coderabbit_installation; then
    warn "CodeRabbit config has been created at .coderabbit.yaml."
    warn "Complete the GitHub App install from the CodeRabbit dashboard for ${GITHUB_OWNER:-<owner>}/${GITHUB_REPO:-<repo>}."
  fi

  if git remote get-url origin >/dev/null 2>&1 && [ "$CODERABBIT_CONFIG_CHANGED" = true ]; then
    if can_autocommit_coderabbit_config; then
      commit_and_push_coderabbit_config
      ok "CodeRabbit config pushed to origin"
    else
      warn "CodeRabbit config was created locally but not auto-committed because other working tree changes are present."
      warn "Commit and push .coderabbit.yaml manually to enable it remotely."
    fi
  fi
}

# ─── Dolt ─────────────────────────────────────────────────────────────────────

install_dolt() {
  if has dolt; then
    ok "dolt: $(dolt version 2>&1 | head -1)"
    return 0
  fi

  info "Installing Dolt..."
  if has brew; then
    brew install dolt
  elif has curl; then
    sudo bash -c 'curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash'
  else
    err "Cannot install Dolt: no brew or curl. See https://docs.dolthub.com/introduction/installation"
    exit 1
  fi

  has dolt && ok "dolt: $(dolt version 2>&1 | head -1)" || { err "Dolt installation failed"; exit 1; }
}

# ─── Beads (bd) ───────────────────────────────────────────────────────────────

install_beads() {
  if has bd; then
    ok "bd: $(bd --version 2>&1)"
    return 0
  fi

  info "Installing Beads (bd)..."
  if has curl; then
    curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
  elif has npm; then
    npm install -g @beads/bd
  else
    err "Cannot install Beads: no curl or npm. See https://github.com/steveyegge/beads"
    exit 1
  fi

  export PATH="$HOME/.local/bin:$HOME/.beads/bin:$PATH"
  has bd && ok "bd: $(bd --version 2>&1)" || { err "Beads installation failed"; exit 1; }
}

# ─── bd init + Dolt server ────────────────────────────────────────────────────

init_beads() {
  # Already initialized?
  if [ -d ".beads" ] && [ -f ".beads/metadata.json" ]; then
    ok ".beads/ already initialized"
    ensure_dolt_server
    return 0
  fi

  info "Running bd init..."

  local init_args=()
  [ -n "$PREFIX" ] && init_args+=(--prefix "$PREFIX")

  # bd init with timeout (30s) — can hang if Dolt server has issues
  if run_with_timeout 30 bd init "${init_args[@]}"; then
    ok "bd init completed"
  else
    local exit_code=$?
    if [ $exit_code -eq 124 ]; then
      warn "bd init timed out (30s). Continuing with manual setup..."
    else
      warn "bd init exited with code $exit_code. Continuing..."
    fi
  fi

  if [ ! -d ".beads" ]; then
    err ".beads/ was not created. bd init failed."
    exit 1
  fi

  ensure_dolt_server
}

ensure_dolt_server() {
  # Use bd's own server management (bd dolt start/status)
  # This is the official way per Beads docs — NOT manual dolt sql-server

  # First check: can bd reach Dolt? (5s timeout)
  if run_with_timeout 5 bd list --json &>/dev/null; then
    ok "Dolt: connected (bd list OK)"
    return 0
  fi

  info "Dolt not responding. Starting via bd dolt start..."

  # Use bd dolt start (official command, handles port/pid/config)
  if run_with_timeout 10 bd dolt start &>/dev/null; then
    sleep 1
    if run_with_timeout 5 bd list --json &>/dev/null; then
      ok "Dolt: started via bd dolt start"
      return 0
    fi
  fi

  # Fallback: try triggering auto-start by just calling bd list
  # Per docs: "Server auto-starts when needed"
  info "Trying auto-start via bd list..."
  if run_with_timeout 10 bd list &>/dev/null; then
    ok "Dolt: auto-started"
    return 0
  fi

  warn "Dolt server could not start. Beads will work in degraded mode."
  warn "Manual fix: bd dolt start (or see bd dolt status)"
}

# ─── Verify ───────────────────────────────────────────────────────────────────

# ─── DoltHub Remote ───────────────────────────────────────────────────────────

# Convert DoltHub web URL to API URL
# https://www.dolthub.com/repositories/org/repo → https://doltremoteapi.dolthub.com/org/repo
normalize_dolthub_url() {
  local url="$1"

  # Already an API URL
  if [[ "$url" == *"doltremoteapi.dolthub.com"* ]]; then
    echo "$url"
    return
  fi

  # Web URL: https://www.dolthub.com/repositories/org/repo
  if [[ "$url" == *"dolthub.com/repositories/"* ]]; then
    local path="${url#*dolthub.com/repositories/}"
    # Strip trailing slash
    path="${path%/}"
    echo "https://doltremoteapi.dolthub.com/${path}"
    return
  fi

  # Short form: org/repo (no URL)
  if [[ "$url" != *"://"* ]] && [[ "$url" == *"/"* ]]; then
    echo "https://doltremoteapi.dolthub.com/${url}"
    return
  fi

  # Unknown format, pass through
  echo "$url"
}

setup_remote() {
  if [ -z "$REMOTE" ]; then
    return 0
  fi

  local api_url
  api_url=$(normalize_dolthub_url "$REMOTE")

  info "Configuring DoltHub remote: $api_url"

  # Add remote via bd (ensures both SQL server and CLI see it)
  if run_with_timeout 10 bd dolt remote add origin "$api_url"; then
    ok "Remote 'origin' added: $api_url"
  else
    # Remote may already exist, try removing first
    if run_with_timeout 5 bd dolt remote remove origin &>/dev/null; then
      if run_with_timeout 10 bd dolt remote add origin "$api_url"; then
        ok "Remote 'origin' updated: $api_url"
      else
        warn "Failed to add remote. Add manually: bd dolt remote add origin $api_url"
        return 1
      fi
    else
      warn "Failed to configure remote. Add manually: bd dolt remote add origin $api_url"
      return 1
    fi
  fi

  # Initial push to create the remote database
  info "Pushing to DoltHub..."
  if run_with_timeout 30 bd dolt push; then
    ok "Pushed to DoltHub successfully"
  else
    warn "Push failed. You may need to authenticate first:"
    warn "  dolt login"
    warn "Then retry: bd dolt push"
  fi
}

# ─── Verify ───────────────────────────────────────────────────────────────────

verify() {
  echo ""
  info "Verification:"

  local all_ok=true

  has git  && echo -e "  ${GREEN}✓${NC} git"  || { echo -e "  ${RED}✗${NC} git"; all_ok=false; }
  has dolt && echo -e "  ${GREEN}✓${NC} dolt" || { echo -e "  ${RED}✗${NC} dolt"; all_ok=false; }
  has terraform && echo -e "  ${GREEN}✓${NC} terraform" || echo -e "  ${YELLOW}⊘${NC} terraform"

  if [ "$SKIP_BEADS" = true ]; then
    echo -e "  ${YELLOW}⊘${NC} bd (skipped)"
    echo -e "  ${YELLOW}⊘${NC} .beads/ (skipped)"
  else
    has bd && echo -e "  ${GREEN}✓${NC} bd" || { echo -e "  ${RED}✗${NC} bd"; all_ok=false; }
    [ -d ".beads" ] && echo -e "  ${GREEN}✓${NC} .beads/" || { echo -e "  ${RED}✗${NC} .beads/"; all_ok=false; }

    # Quick connectivity check (5s timeout, uses bd list not bd doctor)
    if has bd && [ -d ".beads" ]; then
      if run_with_timeout 5 bd list --json &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} bd ↔ Dolt connected"
      else
        echo -e "  ${YELLOW}⚠${NC} bd ↔ Dolt not connected (run: bd dolt start)"
      fi

      # Show remote if configured
      if [ -n "$REMOTE" ]; then
        local api_url
        api_url=$(normalize_dolthub_url "$REMOTE")
        echo -e "  ${GREEN}✓${NC} remote: $api_url"
      fi
    fi
  fi

  if [ -n "$GITHUB_BOOTSTRAP_FULL_NAME" ]; then
    echo -e "  ${GREEN}✓${NC} github: $GITHUB_BOOTSTRAP_FULL_NAME"
  fi

  if [ -f ".coderabbit.yaml" ]; then
    echo -e "  ${GREEN}✓${NC} .coderabbit.yaml"
  fi

  echo ""
  if [ "$all_ok" = true ]; then
    ok "Ready! Run /c4flow to start a workflow."
  else
    warn "Some checks failed. See above."
    return 1
  fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────

main() {
  echo ""
  echo -e "${BLUE}━━━ C4Flow Init ━━━${NC}"
  echo ""

  setup_git

  if [ "$SKIP_BEADS" = false ]; then
    install_dolt
    install_beads
    init_beads
    setup_remote
  else
    info "Skipping Beads (--skip-beads)"
  fi

  maybe_setup_github_repo
  maybe_setup_coderabbit

  verify
}

main "$@"
