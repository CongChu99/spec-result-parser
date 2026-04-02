---
name: c4flow:review
description: AI code review via Codex subagent — writes quality-gate-status.json, resolves beads gate on pass. Use when the user wants code reviewed, needs a quality check before PR, or mentions "review", "code review", or "codex review". Also triggers before creating pull requests.
---

# /c4flow:review — AI Code Review Gate

**Phase**: 5: Review & QA
**Agent type**: Main agent (interactive with user)
**Status**: Implemented

## Handoff from CODE → TEST → REVIEW

```
BEADS → CODE (per-task: spec review + quality review) → TEST → REVIEW (you) → VERIFY → PR
```

**What CODE already checked (per task):**
- Spec compliance — does each task match its requirements?
- Basic code quality — naming, structure, test coverage per task

**What REVIEW checks (full branch):**
- Cross-task integration — do all the tasks work together?
- Security — vulnerabilities, injection, auth issues across the full diff
- Full-branch quality — patterns, consistency, dead code across all changes
- Anything the per-task reviews missed

This is the authoritative full-branch review. The per-task reviews in CODE are quick checks to catch issues early; this review is comprehensive.

## Overview

This skill orchestrates a Codex subagent review, manages the beads gate lifecycle, writes `quality-gate-status.json`, and handles tool unavailability gracefully.

**Pattern:** Report and stop — no auto-fix loop. Findings are reported; user fixes manually and re-runs.
**Blocking threshold:** CRITICAL + HIGH findings block gate resolution. MEDIUM/LOW are informational.
**Review scope:** `codex review --base main` (diff of current branch vs main).

---

## Instructions

You are the `c4flow:review` agent. Execute the following steps in order.

---

### Step 1: Tool Availability Detection

Run these checks before any other action:

```bash
command -v bd
command -v codex
```

**If `bd` is missing:**

Warn the user:

```
WARNING: beads CLI (bd) is not installed.
Gate management and task lifecycle enforcement are unavailable.
Install from: https://github.com/steveyegge/beads

MANUAL REVIEW CHECKLIST (bd fallback):
[ ] Run: codex review --base main
[ ] Verify: 0 CRITICAL findings
[ ] Verify: 0 HIGH findings
[ ] Check MEDIUM/LOW findings for informational value
[ ] Manually confirm review is complete before proceeding to PR

No quality-gate-status.json will be written (gate ID requires bd).
```

Exit gracefully — do not proceed to further steps.

**If `codex` is missing but `bd` IS available:**

Warn the user:

```
WARNING: Codex CLI (codex) is not installed.
Automated AI review is unavailable.
Install from: https://github.com/openai/codex
```

Create a manual review gate:

```bash
GATE_ID=$(bd create "Manual review required (codex not available)" \
  --labels "c4flow-quality-gate,gate,manual" \
  --description "Codex CLI not available. Complete manual code review against main branch, then resolve this gate manually." \
  --json | jq -r '.id')
echo "Manual gate created: $GATE_ID"
echo "Resolve with: bd gate resolve $GATE_ID --reason 'Manual review complete: <your findings summary>'"
```

Print manual review instructions to the user, then exit gracefully.

**If both `bd` and `codex` are available:** Proceed to Step 2.

---

### Step 2: Check for Existing Gate Status and Expiry

Read `quality-gate-status.json` if it exists at the project root.

```bash
# Check for existing status file
if [ -f quality-gate-status.json ]; then
  EXPIRES_AT=$(jq -r '.expires_at // empty' quality-gate-status.json 2>/dev/null)
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
fi
```

**Branch based on what you find:**

- **File does not exist:** Proceed to Step 3.
- **File exists AND `expires_at` is in the future (i.e., `EXPIRES_AT > NOW`):**
  - Inform the user: "A valid (non-expired) review result exists."
  - Show the existing summary: overall_pass, codex_review pass/fail, finding counts.
  - Ask: "Re-run review or use existing results? (re-run / use-existing)"
  - If user chooses `use-existing`: skip to Step 5, using the data already in the file.
  - If user chooses `re-run`: proceed to Step 3.
- **File exists but expired (`EXPIRES_AT <= NOW` or `expires_at` is null):**
  - Inform the user: "Previous review results are stale (expired). Re-running review."
  - Proceed to Step 3.

---

### Step 3: Gate Creation / Lookup

Before creating a new gate, check `quality-gate-status.json` for an existing `gate_id` (prevents duplicate gate creation across invocations — Pitfall 3).

```bash
# Read existing gate_id if file exists
EXISTING_GATE_ID=""
if [ -f quality-gate-status.json ]; then
  EXISTING_GATE_ID=$(jq -r '.gate_id // empty' quality-gate-status.json 2>/dev/null)
fi
```

**If `EXISTING_GATE_ID` is non-empty:** Verify the gate still exists:

```bash
# Verify gate still active in beads
FOUND=$(bd gate list --json 2>/dev/null | jq -r --arg id "$EXISTING_GATE_ID" '.[] | select(.id == $id) | .id' 2>/dev/null)
if [ -n "$FOUND" ]; then
  GATE_ID="$EXISTING_GATE_ID"
  echo "Reusing existing gate: $GATE_ID"
fi
```

If gate not found (empty result): fall through to create a new gate.

**If no existing gate ID or gate not found:** Create a new gate:

```bash
GATE_ID=$(bd create "Quality gate: c4flow review+verify" \
  --labels "c4flow-quality-gate" \
  --description "Automated gate: resolves when Codex review AND bd preflight pass" \
  --json | jq -r '.id')
echo "Gate created: $GATE_ID"
```

**If gate creation fails** (empty `GATE_ID`): Try label-based fallback lookup:

```bash
GATE_ID=$(bd gate list --json 2>/dev/null | \
  jq -r '.[] | select(.labels[]? | contains("c4flow-quality-gate")) | .id' 2>/dev/null | \
  head -1)
```

If still empty after fallback: warn the user that gate tracking is unavailable for this run, but proceed with review (the file will have `gate_id: null`).

Store `GATE_ID` — it will be written to `quality-gate-status.json` in Step 4.

---

### Step 4: Dispatch code-reviewer Subagent and Write Results

Dispatch the `code-reviewer` subagent (`.claude/agents/code-reviewer.md`). The subagent runs Codex with a 120-second timeout and returns structured JSON.

**Subagent dispatch prompt:**

```
Review the current branch diff against main. Use `codex review --base main` (with a 120-second timeout). Return ONLY a JSON object with no surrounding prose. The JSON must have these exact fields: pass, critical_count, high_count, medium_count, low_count, findings (array of objects with severity, file, line, message), and summary. Set pass=true ONLY if critical_count==0 AND high_count==0.
```

**After receiving subagent output, parse and validate:**

```bash
# Extract JSON from output (handles prose wrapping — Pitfall 1)
REVIEW_JSON=$(echo "$SUBAGENT_OUTPUT" | grep -o '{.*}' | jq . 2>/dev/null)

# Validate required fields
VALID=$(echo "$REVIEW_JSON" | jq 'has("pass") and has("critical_count") and has("findings")' 2>/dev/null)
```

**If parse fails or `VALID` is not `true`:**
- Set `codex_review.pass = false`
- Set `codex_review` summary: "Failed to parse subagent output — gate remains blocked"
- Set findings to empty array `[]`
- Set all counts to 0

**Write results to `quality-gate-status.json` using atomic write pattern (Pitfall 2):**

1. Read existing file to preserve `bd_preflight` results if present:

```bash
if [ -f quality-gate-status.json ]; then
  BD_PREFLIGHT=$(jq '.checks.bd_preflight // {"pass": null, "ran_at": null, "issues": []}' quality-gate-status.json 2>/dev/null)
else
  BD_PREFLIGHT='{"pass": null, "ran_at": null, "issues": []}'
fi
```

2. Compute timestamps:

```bash
GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EXPIRY_MINUTES=${C4FLOW_GATE_EXPIRY_MINUTES:-60}
# Add expiry minutes to current time
EXPIRES_AT=$(date -u -d "+${EXPIRY_MINUTES} minutes" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v+${EXPIRY_MINUTES}M +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null)
```

3. Build the complete status object. Set `overall_pass = true` ONLY if BOTH `codex_review.pass == true` AND `bd_preflight.pass == true`. If `bd_preflight.pass` is `null`, `overall_pass` MUST be `false`:

```bash
CODEX_PASS=$(echo "$REVIEW_JSON" | jq '.pass')
BD_PASS=$(echo "$BD_PREFLIGHT" | jq '.pass')
if [ "$CODEX_PASS" = "true" ] && [ "$BD_PASS" = "true" ]; then
  OVERALL_PASS=true
else
  OVERALL_PASS=false
fi
```

4. Write to temp file, then atomically rename:

```bash
jq -n \
  --arg schema_version "1" \
  --arg generated_at "$GENERATED_AT" \
  --arg expires_at "$EXPIRES_AT" \
  --arg gate_id "${GATE_ID:-null}" \
  --argjson overall_pass $OVERALL_PASS \
  --argjson codex_review "$REVIEW_JSON_WITH_RAN_AT" \
  --argjson bd_preflight "$BD_PREFLIGHT" \
  '{
    schema_version: $schema_version,
    generated_at: $generated_at,
    expires_at: $expires_at,
    gate_id: (if $gate_id == "null" then null else $gate_id end),
    overall_pass: $overall_pass,
    checks: {
      codex_review: ($codex_review + {ran_at: $generated_at}),
      bd_preflight: $bd_preflight
    }
  }' > quality-gate-status.json.tmp && mv quality-gate-status.json.tmp quality-gate-status.json

echo "quality-gate-status.json written (expires: $EXPIRES_AT)"
```

Log a validation entry every time the file is written (required per research warning):

```
[GATE-STATUS WRITE] generated_at=$GENERATED_AT gate_id=$GATE_ID codex_pass=$CODEX_PASS overall_pass=$OVERALL_PASS
```

---

### Step 5: Gate Resolution or Report

Read the current `quality-gate-status.json` to determine the outcome.

**If `codex_review.pass == false`:**

Report findings to the user in a readable grouped format:

```
CODE REVIEW FAILED
==================
Gate: $GATE_ID
Reviewed at: $GENERATED_AT

CRITICAL findings ($CRITICAL_COUNT):
  - <file>:<line> — <message>

HIGH findings ($HIGH_COUNT):
  - <file>:<line> — <message>

MEDIUM findings ($MEDIUM_COUNT) [informational]:
  - <file>:<line> — <message>

LOW findings ($LOW_COUNT) [informational]:
  - <file>:<line> — <message>

Action required: Fix all CRITICAL and HIGH issues, then re-run /c4flow:review.
Gate $GATE_ID remains open until all checks pass.
```

Gate remains open — do NOT call `bd gate resolve`.

**If `codex_review.pass == true`:**

Check whether `bd_preflight.pass` is also `true` (from the file):

- **If `bd_preflight.pass == true` (BOTH pass — gate can be resolved):**

  Resolve gate with audit trail:

  ```bash
  TIMESTAMP=$(jq -r '.checks.codex_review.ran_at' quality-gate-status.json)
  MEDIUM_COUNT=$(jq -r '.checks.codex_review.medium_count' quality-gate-status.json)
  LOW_COUNT=$(jq -r '.checks.codex_review.low_count' quality-gate-status.json)

  bd gate resolve "$GATE_ID" \
    --reason "Codex review: 0 critical, 0 high (M:${MEDIUM_COUNT}, L:${LOW_COUNT}). bd preflight: passed. Reviewed at: ${TIMESTAMP}"
  ```

  Update `overall_pass: true` in `quality-gate-status.json` (atomic write as in Step 4).

- **If `bd_preflight.pass` is `null` or `false` (codex passed, preflight not yet run or failed):**

  Inform the user:

  ```
  Codex review PASSED (0 critical, 0 high).
  bd preflight has not run yet (or did not pass).

  Next step: Run /c4flow:verify to complete the preflight check.
  Gate $GATE_ID will auto-resolve when BOTH checks pass.
  ```

  Gate remains open until both checks pass.

---

### Step 6: Summary Output

Print a summary box at the end of every run:

```
╔══════════════════════════════════════════════════════╗
║             C4FLOW REVIEW SUMMARY                    ║
╠══════════════════════════════════════════════════════╣
║ Overall status : PASS / FAIL                         ║
║ Gate ID        : bd-xxxx                             ║
║ Expires at     : 2026-03-16T11:30:00Z                ║
╠══════════════════════════════════════════════════════╣
║ Codex review   : PASS/FAIL (C:0 H:0 M:2 L:1)        ║
║ bd preflight   : PASS/FAIL/NOT RUN                   ║
╚══════════════════════════════════════════════════════╝
```

**On review pass:**
```
Review passed. Quality gate status written to quality-gate-status.json.
Run /c4flow:verify to complete the preflight check and close the gate.
```

**On review fail:**
```
Review FAILED. $CRITICAL_COUNT critical, $HIGH_COUNT high findings must be resolved.
Fix the issues listed above, then re-run /c4flow:review.
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `C4FLOW_GATE_EXPIRY_MINUTES` | `60` | Minutes until gate status expires and requires re-run |

---

## Key Files

| File | Description |
|------|-------------|
| `quality-gate-status.json` | Ephemeral gate status file (git-ignored, written each run) |
| `.claude/agents/code-reviewer.md` | Subagent definition dispatched for Codex review |
| `quality-gate-status.schema.json` | JSON Schema draft-07 validating the status file structure |

---

## Implementation Notes

- **No auto-fix loop:** This skill reports findings and stops. The user fixes manually and re-runs.
- **Atomic writes:** Always write to `.tmp` then `mv` to prevent partial-write corruption (Pitfall 2).
- **Gate ID persistence:** Always read existing `gate_id` from file before creating a new gate (Pitfall 3).
- **Parse safety:** Extract JSON with `grep -o '{.*}'` to handle prose wrapping (Pitfall 1).
- **Null means not-run:** `overall_pass` is `false` whenever any check has `pass: null`.
- **Subagent timeout:** Codex runs with `timeout 120` — synchronous only, never backgrounded (Pitfall 6).

## Handoff to VERIFY

After REVIEW passes (0 CRITICAL, 0 HIGH):
- `quality-gate-status.json` has `codex_review.pass = true`
- `bd_preflight.pass` is still `null` (not yet run)
- `overall_pass` is `false` (both checks needed)

Next step: `c4flow:verify` runs `bd preflight`, merges results, and resolves the gate when both pass.

```
REVIEW writes codex_review → VERIFY writes bd_preflight → both pass? → gate resolved → PR
```
