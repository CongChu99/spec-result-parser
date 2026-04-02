#!/usr/bin/env bash
# dolt_sync.sh — sync beads from DoltHub
# Usage: bash dolt_sync.sh [project-root]
#
# KEY INSIGHT: dolt CLI (fetch, reset) must run with server STOPPED.
# When server runs, it manages refs in-memory; CLI can't see them after stop.
# Running CLI offline writes refs directly to disk → persists across restarts.

set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
cd "$PROJECT_ROOT"

# ── helpers ──────────────────────────────────────────────────────────────────
ok()   { echo "✅ $*"; }
warn() { echo "⚠️  $*"; }
err()  { echo "❌ $*" >&2; exit 1; }
info() { echo "ℹ️  $*"; }

# ── 1. check .beads exists ───────────────────────────────────────────────────
[ -d ".beads" ] || err "No .beads/ directory found. Run c4flow:init first."

# ── 2. read .state.json ──────────────────────────────────────────────────────
STATE_FILE="docs/c4flow/.state.json"
[ -f "$STATE_FILE" ] || STATE_FILE=".beads/.state.json"
[ -f "$STATE_FILE" ] || STATE_FILE=".state.json"
[ -f "$STATE_FILE" ] || err "No .state.json found (checked docs/c4flow/, .beads/, root)."

DOLT_REMOTE=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('doltRemote',''))" 2>/dev/null)
[ -n "$DOLT_REMOTE" ] || err "No doltRemote in $STATE_FILE — Dolt sync not configured."

PROJECT_NAME=$(basename "$DOLT_REMOTE")
DOLT_DB="$PROJECT_ROOT/.beads/dolt/$PROJECT_NAME"

info "DoltHub remote : $DOLT_REMOTE"
info "Dolt DB path   : $DOLT_DB"

# ── 3. stop server ───────────────────────────────────────────────────────────
bd dolt stop 2>/dev/null || true
sleep 1

# ── 4. MISSING_DB: clone fresh from DoltHub ──────────────────────────────────
# dolt clone is the canonical way — handles init+fetch+checkout in one step,
# no journal issues, no no-common-ancestor problem.
if [ ! -d "$DOLT_DB" ]; then
  warn "Inner DB missing — cloning from DoltHub..."
  mkdir -p "$PROJECT_ROOT/.beads/dolt"
  (cd "$PROJECT_ROOT/.beads/dolt" && dolt clone "$DOLT_REMOTE") \
    || err "dolt clone failed. Check: dolt login"
  info "Starting server and pulling latest..."
  bd dolt start 2>/dev/null || err "Server failed to start after clone"
  sleep 3
  bd dolt pull 2>/dev/null || true

# ── 5. EXISTING DB: ensure remote, fetch, merge/reset ────────────────────────
else
  # Ensure remote configured (offline)
  EXISTING_REMOTE=$(cd "$DOLT_DB" && dolt remote -v 2>/dev/null | head -1 | awk '{print $2}' || true)
  if [ -z "$EXISTING_REMOTE" ]; then
    info "Adding DoltHub remote..."
    (cd "$DOLT_DB" && dolt remote add origin "$DOLT_REMOTE") || err "Failed to add remote"
  elif [ "$EXISTING_REMOTE" != "$DOLT_REMOTE" ]; then
    warn "Remote mismatch — updating to match .state.json..."
    (cd "$DOLT_DB" && dolt remote remove origin && dolt remote add origin "$DOLT_REMOTE")
  fi

  # Fetch offline — refs written to disk, visible after server restart
  info "Fetching from DoltHub..."
  FETCH_OUT=$((cd "$DOLT_DB" && dolt fetch origin 2>&1) || true)
  echo "$FETCH_OUT" | grep -qi "authentication" && err "DoltHub auth required. Run: dolt login"
  echo "$FETCH_OUT" | grep -qi "not found\|does not exist" && err "Remote not found: $DOLT_REMOTE"

  # Merge or reset
  MERGE_BASE=$((cd "$DOLT_DB" && dolt merge-base HEAD remotes/origin/main 2>&1) || true)
  if echo "$MERGE_BASE" | grep -qi "no common ancestor\|error"; then
    LOCAL_COMMITS=$((cd "$DOLT_DB" && dolt log --oneline 2>/dev/null | wc -l | tr -d ' ') || echo "0")
    if [ "$LOCAL_COMMITS" -gt 5 ]; then
      warn "Local DB has $LOCAL_COMMITS commits, no common ancestor with DoltHub."
      warn "May have local-only beads — aborting. To force: cd $DOLT_DB && dolt reset --hard remotes/origin/main"
      exit 1
    fi
    info "Fresh local DB ($LOCAL_COMMITS commits). Resetting to DoltHub history..."
    (cd "$DOLT_DB" && dolt reset --hard remotes/origin/main) || err "dolt reset --hard failed"
  else
    info "Pulling from DoltHub (shared history)..."
    PULL_OUT=$((cd "$DOLT_DB" && dolt pull origin main 2>&1) || true)
    if echo "$PULL_OUT" | grep -qi "conflict"; then
      warn "Merge conflicts — resolve manually."; echo "$PULL_OUT"; exit 1
    fi
  fi

  # Start server after offline ops
  info "Starting bd server..."
  bd dolt start 2>/dev/null || err "Server failed to start"
  sleep 3
  bd dolt status 2>/dev/null | grep -q "running" || err "Server not responding. Check dolt-server.log"
fi

# ── 6. verify ────────────────────────────────────────────────────────────────
HEAD_HASH=$(cd "$DOLT_DB" && dolt log -n 1 --oneline 2>/dev/null | awk '{print substr($1,1,8)}' | sed 's/\x1b\[[0-9;]*m//g' || echo "unknown")
HEAD_MSG=$(cd "$DOLT_DB" && dolt log -n 1 --oneline 2>/dev/null | cut -d' ' -f2- | sed 's/\x1b\[[0-9;]*m//g' || echo "")
BEAD_COUNT=$(bd list 2>/dev/null | grep -c "^[│├└○◐●✓❄]" || echo "0")

ok "Dolt sync complete"
echo "   Remote : $DOLT_REMOTE"
echo "   HEAD   : $HEAD_HASH ($HEAD_MSG)"
echo "   Beads  : $BEAD_COUNT issues"
