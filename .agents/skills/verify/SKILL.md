---
name: c4flow:verify
description: Quality gate aggregation — runs bd preflight, combines with Codex review results, declares Ready for PR status. Use when the user wants to check if code is ready for PR, verify quality gates, or run preflight checks. Also triggers when mentioning "verify", "preflight", "quality gate", or "ready for PR".
---

# /c4flow:verify — Quality Gate Aggregation

**Phase**: 5: Review & QA
**Agent type**: Main agent (interactive with user)
**Status**: Implemented

## Handoff from REVIEW → VERIFY

```
CODE (per-task reviews) → TEST → REVIEW (Codex full-branch) → VERIFY (you) → PR
```

**What REVIEW already did:**
- Ran Codex review on full branch diff vs main
- Wrote `codex_review` results to `quality-gate-status.json`
- Created/reused the beads quality gate (`gate_id`)

**What VERIFY does:**
- Runs `bd preflight --check --json` (lint, TODO markers, uncommitted changes, etc.)
- Merges preflight results with existing Codex review data
- Declares **Ready for PR: YES / NO** based on both checks
- Resolves the beads gate when both pass

The gate requires BOTH `codex_review.pass` AND `bd_preflight.pass` to be `true`. Either being `null` or `false` blocks the gate.

## Overview

This skill runs `bd preflight --check --json`, merges results with any existing `codex_review` data in `quality-gate-status.json`, resolves the beads gate when all checks pass, and declares a clear **Ready for PR: YES / NO** verdict.

**Blocking threshold:** Both `codex_review.pass` AND `bd_preflight.pass` must be `true`. Any `null` (not-yet-run) check is treated as NOT passing.
**Atomic writes:** All writes to `quality-gate-status.json` go through `.tmp` → `mv`.
**Audit trail:** On `Ready for PR: YES`, prints a reminder to use `bd close --reason` when closing the task bead.

---

## Instructions

You are the `c4flow:verify` agent. Execute the following steps in order.

---

### Step 1: Tool Availability Detection

Check for the `bd` CLI before doing anything else:

```bash
command -v bd
```

**If `bd` is missing:**

Warn the user:

```
WARNING: beads CLI (bd) is not installed.
Preflight checks and gate management are unavailable.
Install from: https://github.com/steveyegge/beads

MANUAL PREFLIGHT CHECKLIST (bd fallback):
[ ] No uncommitted changes: git status --short (should be empty)
[ ] No leftover TODO/FIXME markers introduced in this branch: git diff main | grep -i 'TODO\|FIXME'
[ ] Branch is up to date with main: git fetch && git status
[ ] No debug logging left in shipped code (console.log, debugger, pprint, etc.)
[ ] All new files are included in the commit (nothing left untracked)

Complete the checklist manually, then proceed to PR creation.
```

Exit gracefully — do not proceed to further steps.

**If `bd` is available:** Proceed to Step 2.

---

### Step 2: Check Existing Gate Status

Read `quality-gate-status.json` at the project root:

```bash
if [ ! -f quality-gate-status.json ]; then
  echo "No gate status found. Run /c4flow:review first to create the quality gate."
  exit 1
fi
```

If the file does not exist, exit with the message above.

**If the file exists**, check `expires_at`:

```bash
EXPIRES_AT=$(jq -r '.expires_at // empty' quality-gate-status.json 2>/dev/null)
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

If `EXPIRES_AT` is non-empty and `EXPIRES_AT <= NOW` (expired):

```
WARNING: Gate status is expired (expired: $EXPIRES_AT).
Run /c4flow:review first to refresh the gate status, then re-run /c4flow:verify.
```

Exit gracefully.

If `EXPIRES_AT` is in the future (or `expires_at` is null but file exists): proceed to Step 3.

---

### Step 3: Run bd Preflight

Execute the preflight check and capture full output:

```bash
PREFLIGHT_OUTPUT=$(bd preflight --check --json 2>&1)
```

Parse the JSON:

```bash
PREFLIGHT_JSON=$(echo "$PREFLIGHT_OUTPUT" | grep -o '{.*}' | jq . 2>/dev/null)
PREFLIGHT_PARSE_OK=$(echo "$PREFLIGHT_JSON" | jq 'has("pass")' 2>/dev/null)
```

**If parse fails (`PREFLIGHT_PARSE_OK` is not `true`):**

```bash
PREFLIGHT_PASS=false
PREFLIGHT_JSON='{"pass": false, "issues": [{"check": "parse_error", "message": "Failed to parse bd preflight output"}]}'
echo "WARNING: Could not parse bd preflight JSON output. Treating preflight as FAILED."
echo "Raw output:"
echo "$PREFLIGHT_OUTPUT"
```

**If parse succeeds:**

```bash
PREFLIGHT_PASS=$(echo "$PREFLIGHT_JSON" | jq '.pass // false')
PREFLIGHT_ISSUES=$(echo "$PREFLIGHT_JSON" | jq '.issues // []')
```

---

### Step 4: Write Preflight Results to quality-gate-status.json

Preserve the existing `codex_review` block, update `bd_preflight`, and recompute `overall_pass`.

1. Read existing data:

```bash
EXISTING_CODEX=$(jq '.checks.codex_review // {"pass": null, "ran_at": null, "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0, "findings": []}' quality-gate-status.json 2>/dev/null)
EXISTING_GATE_ID=$(jq -r '.gate_id // empty' quality-gate-status.json 2>/dev/null)
```

2. Compute timestamps:

```bash
GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EXPIRY_MINUTES=${C4FLOW_GATE_EXPIRY_MINUTES:-60}
EXPIRES_AT=$(date -u -d "+${EXPIRY_MINUTES} minutes" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v+${EXPIRY_MINUTES}M +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null)
```

3. Build the `bd_preflight` block with `ran_at`:

```bash
BD_PREFLIGHT_BLOCK=$(echo "$PREFLIGHT_JSON" | jq \
  --arg ran_at "$GENERATED_AT" \
  '. + {ran_at: $ran_at}')
```

4. Compute `overall_pass` — BOTH checks must be `true`; `null` is never a pass:

```bash
CODEX_PASS=$(echo "$EXISTING_CODEX" | jq '.pass')
if [ "$CODEX_PASS" = "true" ] && [ "$PREFLIGHT_PASS" = "true" ]; then
  OVERALL_PASS=true
else
  OVERALL_PASS=false
fi
```

5. Atomic write:

```bash
jq -n \
  --arg schema_version "1" \
  --arg generated_at "$GENERATED_AT" \
  --arg expires_at "$EXPIRES_AT" \
  --arg gate_id "${EXISTING_GATE_ID:-null}" \
  --argjson overall_pass $OVERALL_PASS \
  --argjson codex_review "$EXISTING_CODEX" \
  --argjson bd_preflight "$BD_PREFLIGHT_BLOCK" \
  '{
    schema_version: $schema_version,
    generated_at: $generated_at,
    expires_at: $expires_at,
    gate_id: (if $gate_id == "" or $gate_id == "null" then null else $gate_id end),
    overall_pass: $overall_pass,
    checks: {
      codex_review: $codex_review,
      bd_preflight: $bd_preflight
    }
  }' > quality-gate-status.json.tmp && mv quality-gate-status.json.tmp quality-gate-status.json

echo "[GATE-STATUS WRITE] generated_at=$GENERATED_AT gate_id=${EXISTING_GATE_ID:-null} preflight_pass=$PREFLIGHT_PASS overall_pass=$OVERALL_PASS"
```

---

### Step 5: Gate Resolution Check

Read the `gate_id` from the updated `quality-gate-status.json`:

```bash
GATE_ID=$(jq -r '.gate_id // empty' quality-gate-status.json 2>/dev/null)
```

**If `GATE_ID` is empty — label-based fallback lookup:**

```bash
GATE_ID=$(bd gate list --json 2>/dev/null | \
  jq -r '.[] | select(.labels[]? | contains("c4flow-quality-gate")) | .id' 2>/dev/null | \
  head -1)

# If found via label, persist it back to the status file
if [ -n "$GATE_ID" ]; then
  jq --arg gate_id "$GATE_ID" '.gate_id = $gate_id' quality-gate-status.json > quality-gate-status.json.tmp \
    && mv quality-gate-status.json.tmp quality-gate-status.json
  echo "Gate ID recovered via label lookup: $GATE_ID"
fi
```

**If `overall_pass == true` AND `GATE_ID` is non-empty:**

Resolve the gate with a full audit trail reason string:

```bash
TIMESTAMP=$(jq -r '.generated_at' quality-gate-status.json)
CRITICAL=$(jq -r '.checks.codex_review.critical_count // 0' quality-gate-status.json)
HIGH=$(jq -r '.checks.codex_review.high_count // 0' quality-gate-status.json)
MEDIUM=$(jq -r '.checks.codex_review.medium_count // 0' quality-gate-status.json)
LOW=$(jq -r '.checks.codex_review.low_count // 0' quality-gate-status.json)
PREFLIGHT_ISSUES_COUNT=$(jq '.checks.bd_preflight.issues | length' quality-gate-status.json 2>/dev/null || echo 0)

bd gate resolve "$GATE_ID" \
  --reason "All checks passed. Codex: ${CRITICAL} critical, ${HIGH} high (M:${MEDIUM}, L:${LOW}). bd preflight: passed (${PREFLIGHT_ISSUES_COUNT} issues). Verified at: ${TIMESTAMP}"

echo "All quality gates resolved. Ready for PR."
```

**If `overall_pass == false`:**

Do NOT resolve the gate. The summary output in Step 6 will explain what failed.

---

### Step 6: Aggregated Summary Output

Read all relevant fields from `quality-gate-status.json` and print the status report:

```bash
CODEX_PASS_STATUS=$(jq -r 'if .checks.codex_review.pass == true then "PASS" elif .checks.codex_review.pass == false then "FAIL" else "NOT RUN" end' quality-gate-status.json)
CODEX_RAN_AT=$(jq -r '.checks.codex_review.ran_at // "not yet run"' quality-gate-status.json)
CODEX_CRITICAL=$(jq -r '.checks.codex_review.critical_count // 0' quality-gate-status.json)
CODEX_HIGH=$(jq -r '.checks.codex_review.high_count // 0' quality-gate-status.json)
CODEX_MEDIUM=$(jq -r '.checks.codex_review.medium_count // 0' quality-gate-status.json)
CODEX_LOW=$(jq -r '.checks.codex_review.low_count // 0' quality-gate-status.json)

BD_PASS_STATUS=$(jq -r 'if .checks.bd_preflight.pass == true then "PASS" elif .checks.bd_preflight.pass == false then "FAIL" else "NOT RUN" end' quality-gate-status.json)
BD_RAN_AT=$(jq -r '.checks.bd_preflight.ran_at // "not yet run"' quality-gate-status.json)
BD_ISSUES=$(jq '.checks.bd_preflight.issues | length' quality-gate-status.json 2>/dev/null || echo 0)

GATE_ID_DISPLAY=$(jq -r '.gate_id // "none"' quality-gate-status.json)
EXPIRES_DISPLAY=$(jq -r '.expires_at // "unknown"' quality-gate-status.json)
OVERALL=$(jq -r 'if .overall_pass then "YES" else "NO" end' quality-gate-status.json)
```

Print the report:

```
=== C4Flow Quality Gate Status ===

Codex Review:  [$CODEX_PASS_STATUS]  (ran: $CODEX_RAN_AT)
  Critical: $CODEX_CRITICAL  High: $CODEX_HIGH  Medium: $CODEX_MEDIUM  Low: $CODEX_LOW
bd Preflight:  [$BD_PASS_STATUS]  (ran: $BD_RAN_AT)
  Issues: $BD_ISSUES

Ready for PR: $OVERALL

Gate ID: $GATE_ID_DISPLAY
Expires: $EXPIRES_DISPLAY
```

**If `Ready for PR: YES`:**

```
Next step: Run /c4flow:pr to create the pull request.

REMINDER: When closing this task with `bd close`, you MUST include --reason:
  bd close <bead_id> --reason "Completed: <brief summary of what was done>"
This is required for audit trail compliance.
```

**If `Ready for PR: NO`:**

Print which checks need attention:

- If `codex_review.pass` is `null` (not run): `Run /c4flow:review first`
- If `codex_review.pass == false`: `Fix CRITICAL/HIGH findings, then re-run /c4flow:review`
- If `bd_preflight.pass == false`: `Fix preflight issues listed below, then re-run /c4flow:verify`
  - List each failing issue from `quality-gate-status.json` `.checks.bd_preflight.issues[]`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `C4FLOW_GATE_EXPIRY_MINUTES` | `60` | Minutes until gate status expires and requires re-run |

---

## Key Files

| File | Description |
|------|-------------|
| `quality-gate-status.json` | Ephemeral gate status file (git-ignored, read and updated each run) |
| `quality-gate-status.schema.json` | JSON Schema draft-07 validating the status file structure |

---

## Implementation Notes

- **Null means not-run:** `overall_pass` is `false` whenever any check has `pass: null` — no partial pass states.
- **Codex results preserved:** Only `bd_preflight` is updated; existing `codex_review` data is never overwritten.
- **Atomic writes:** Always write to `.tmp` then `mv` to prevent partial-write corruption (Pitfall 2).
- **Gate ID persistence:** If `gate_id` is missing, label-based fallback lookup (`c4flow-quality-gate`) recovers it before giving up.
- **Expiry check:** An expired gate status requires a fresh `/c4flow:review` run, not just a re-verify.
- **bd close audit trail:** Ready for PR output always includes the `bd close --reason` reminder (INFR-04).
- **Sync after gate resolution:** When a gate resolves, run `bd dolt push 2>/dev/null` to sync state to remote (if configured). This ensures team members see the updated gate status.
- **Use `--json` consistently:** All `bd` commands use `--json` for reliable programmatic parsing. Never parse human-readable output.

## Full Quality Pipeline

```
BEADS
  └── Tasks created (bd create) with epic

CODE (c4flow:code)
  ├── Per-task: implementer → spec review → quality review → bd close
  └── All tasks closed → advance to TEST

TEST (c4flow:test)
  └── Full test suite, coverage gate → advance to REVIEW

REVIEW (c4flow:review)
  ├── Codex review --base main (full branch diff)
  ├── Writes codex_review to quality-gate-status.json
  └── Creates/reuses beads quality gate → advance to VERIFY

VERIFY (c4flow:verify — you are here)
  ├── bd preflight --check --json
  ├── Merges with codex_review results
  ├── Both pass? → bd gate resolve → Ready for PR: YES
  └── Either fail? → Ready for PR: NO (explain what to fix)

PR (c4flow:pr)
  └── Creates pull request with gate status in description
```
