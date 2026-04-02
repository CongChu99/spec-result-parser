---
name: c4flow:code
description: Execute code implementation via a strict serial task loop — pick one unblocked task, TDD it, verify, review, PR, merge, then pick the next task. Each task gets its own branch (feat/bead-id-slug). Uses bd ready → atomic claim → set in-progress → dolt push → TDD (RED gate pause) → verify → review → PR/merge → close → repeat. Trigger when the user wants to start coding, implement tasks, or run the implementation phase.
---

# /c4flow:code — Strict Serial Task Loop

**Phase**: 3: Implementation
**Agent type**: Main agent (coordinator), dispatches sub-agents per task
**State**: `CODE_LOOP` in `.state.json`

One task at a time. Each task is a complete cycle: pickup → branch → TDD → verify → review → PR/merge → close. No task starts until the previous one is merged.

```
┌──────────────────────────────────────────────────────┐
│  while bd ready --assignee $ACTOR has tasks:          │
│                                                       │
│  1. PICKUP   bd ready → claim → dolt push             │
│  2. BRANCH   git checkout -b feat/<id>-<slug>         │
│  3. TDD      RED gate pause → GREEN → REFACTOR        │
│  4. VERIFY   tests + coverage + bd preflight          │
│  5. REVIEW   c4flow:review (CRITICAL/HIGH blocks)     │
│  6. PR/MERGE c4flow:pr → merge to main                │
│  7. CLOSE    bd close --reason → dolt push            │
│                                                       │
│  no tasks left → advance currentState to INFRA        │
└──────────────────────────────────────────────────────┘
```

---

## Step 0: Read State and Resolve Actor

### Read .state.json

```bash
STATE=$(cat docs/c4flow/.state.json 2>/dev/null)
CURRENT_STATE=$(echo "$STATE" | jq -r '.currentState // empty')
EPIC_ID=$(echo "$STATE" | jq -r '.beadsEpic // empty')
FEATURE_SLUG=$(echo "$STATE" | jq -r '.feature.slug // empty')
TASK_LOOP=$(echo "$STATE" | jq '.taskLoop // null')
```

**Legacy migration**: if `currentState` is `"CODE"`, update it to `"CODE_LOOP"`:

```bash
if [ "$CURRENT_STATE" = "CODE" ]; then
  jq '.currentState = "CODE_LOOP" | .taskLoop = null' \
    docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
    && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
  CURRENT_STATE="CODE_LOOP"
fi
```

Abort if state is not `CODE_LOOP`:
```bash
[ "$CURRENT_STATE" != "CODE_LOOP" ] && echo "ERROR: currentState is $CURRENT_STATE, expected CODE_LOOP" && exit 1
```

### Resolve Actor

Actor is used for both `bd ready --assignee` filtering and `bd update --claim`.

Priority order:
1. **Explicit arg** — parse skill invocation args for `--assignee <name>` or `from <name>` / `pickup task from <name>`
2. **`BD_ACTOR`** env var
3. **`git config user.name`** — always available, used as final fallback

```bash
# 1. Parse explicit assignee from args (passed in from orchestrator)
ACTOR=$(echo "$SKILL_ARGS" | grep -oP '(?<=--assignee |from )["\x27]?[A-Za-z0-9 _-]+["\x27]?' | tr -d "\"'" | head -1)

# 2. BD_ACTOR fallback
ACTOR=${ACTOR:-$BD_ACTOR}

# 3. git config fallback
ACTOR=${ACTOR:-$(git config user.name)}

echo "Actor: $ACTOR"
```

### Check for Resume

If `taskLoop` is non-null, a task was in progress when the session ended. Resume from saved `subState`:

```bash
SUBTASK_ID=$(echo "$TASK_LOOP" | jq -r '.currentTaskId // empty')
SUBSTATE=$(echo "$TASK_LOOP" | jq -r '.subState // empty')

if [ -n "$SUBTASK_ID" ] && [ -n "$SUBSTATE" ]; then
  echo "Resuming task $SUBTASK_ID from subState $SUBSTATE"
  # Run Step 0.5 (Pre-flight Sync) first, unless subState == "CLOSING"
  # Then jump to the right sub-state — see: Resume Logic section below
fi
```

---

## Step 0.5: Pre-flight Sync

> **Skip this step** if resuming from `taskLoop.subState == "CLOSING"` — go directly to Step 7.

Invoke `c4flow:sync`. This syncs both Dolt beads from DoltHub and git from GitHub origin.

**On success:**
→ Proceed to Step 1: PICKUP

**On failure (any sync error):**
→ Show the error output verbatim
→ Ask the user:
  ```
  Sync failed. How do you want to proceed?
  [continue] Use local data (may be stale — tasks you see may not reflect latest team activity)
  [stop]     Exit now to fix the sync issue
  ```
→ If user chooses **[continue]**: note the sync failure in the session, proceed to Step 1
→ If user chooses **[stop]**: exit the skill immediately, leave `.state.json` unchanged

---

## Step 1: PICKUP — Find and Claim Task

### Discover unblocked tasks

```bash
READY_JSON=$(bd ready --assignee "$ACTOR" --json 2>/dev/null)
READY_COUNT=$(echo "$READY_JSON" | jq 'length')
```

If `READY_COUNT` is 0:
```
No unblocked tasks assigned to <actor>.
All tasks may be blocked, in progress, or complete.
Check status with: bd dep tree <epic-id>
```
→ If all tasks closed, advance to INFRA (see Completion Gate).
→ Otherwise, show blocked tasks and wait for user.

If `READY_COUNT` > 1 — show list and ask user to confirm or select:
```
Ready tasks for <actor>:
  [1] bd-a1b2  [P1] "Add login endpoint"
  [2] bd-c3d4  [P2] "Add JWT validation"
  [3] bd-e5f6  [P2] "Add rate limiting"

Pick a task (default: 1, the highest priority unblocked task):
```

### Claim and set in-progress

```bash
TASK_ID=<selected-id>

# 1. Claim the task (assigns to current actor)
CLAIM_RESULT=$(bd update "$TASK_ID" --claim --json 2>&1)
CLAIM_OK=$(echo "$CLAIM_RESULT" | jq -r '.status // empty' 2>/dev/null)

if [ "$CLAIM_OK" != "ok" ]; then
  echo "Task $TASK_ID is already claimed. Re-running bd ready..."
  # Loop back to discovery — do NOT proceed
fi

# 2. Move from "active" → "in-progress" immediately
bd update "$TASK_ID" --status "in-progress" --json 2>&1
```

> **Critical:** Status must be set to `in-progress` **before** any coding starts — not at close time. This makes task progress visible to the team immediately.

### Sync to DoltHub immediately

```bash
bd dolt commit -m "claim: task $TASK_ID in_progress" 2>/dev/null
DOLT_RESULT=$(bd dolt push 2>&1)
if [ $? -eq 0 ]; then
  echo "Synced: task $TASK_ID is in-progress, visible to team on DoltHub"
else
  echo "WARNING: Dolt push failed. Task is claimed locally but team may not see it yet."
  echo "Run 'bd dolt push' manually when network is available."
fi
```

### Write taskLoop to .state.json

```bash
TASK_TITLE=$(echo "$READY_JSON" | jq -r --arg id "$TASK_ID" '.[] | select(.id == $id) | .title')
TASK_SLUG=$(echo "$TASK_TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g')
BRANCH_NAME="feat/${TASK_ID}-${TASK_SLUG}"

jq --arg id "$TASK_ID" \
   --arg slug "$TASK_SLUG" \
   --arg branch "$BRANCH_NAME" \
   '.taskLoop = {
     currentTaskId: $id,
     currentTaskSlug: $slug,
     currentBranch: $branch,
     subState: "CODING",
     completedTasks: (.taskLoop.completedTasks // []),
     failedTasks: (.taskLoop.failedTasks // [])
   }' docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
```

---

## Step 2: BRANCH — Create Task Branch

### Always cut from latest main

```bash
git checkout main 2>&1
PULL_RESULT=$(git pull 2>&1)

if echo "$PULL_RESULT" | grep -qi "error\|conflict\|fatal"; then
  echo "BLOCKED: git pull failed — $PULL_RESULT"
  echo "Fix network/conflict issue, then resume."
  # Update subState to reflect BLOCKED
  jq '.taskLoop.subState = "BLOCKED"' \
    docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
    && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
  exit 1
fi
```

### Check for existing branch

```bash
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  echo "Branch $BRANCH_NAME already exists."
  echo "Options: [resume] continue from existing branch | [recreate] delete and start fresh"
  # Wait for user input
fi
```

### Create branch

```bash
git checkout -b "$BRANCH_NAME"
echo "Branch: $BRANCH_NAME"
```

---

## Step 3: TDD — Red Gate Sub-agent

Dispatch a TDD sub-agent. Provide full task context — do NOT make the sub-agent read files.

### Read task context before dispatch

```bash
TASK_DETAIL=$(bd show "$TASK_ID" --json 2>/dev/null)
TASK_DESC=$(echo "$TASK_DETAIL" | jq -r '.description // empty')
TASK_CRITERIA=$(echo "$TASK_DETAIL" | jq -r '.acceptance // empty')
TASK_SPEC_REF=$(echo "$TASK_DETAIL" | jq -r '.notes // empty' | grep -i "spec ref" | head -1)
```

### Sub-agent prompt template

Use `skills/code/implementer-prompt.md` as base, with TDD additions:

```
You are the TDD implementer for task: <task-title>

## Task
ID: <task-id>
Title: <task-title>
Description: <task-description>
Acceptance Criteria: <acceptance-criteria>
Spec Reference: <spec-ref>

## Feature Context
Feature: <feature-name>
Branch: <branch-name>
Spec: docs/specs/<feature-slug>/spec.md
Design: docs/specs/<feature-slug>/design.md
Tech Stack: docs/specs/<feature-slug>/tech-stack.md

## TDD Instructions

### Phase 1: RED (MANDATORY — do not skip)
1. Read the acceptance criteria carefully
2. Write the test file FIRST — no implementation code yet
3. Run the test suite: the new test MUST fail
4. If the test passes immediately → STOP and report TRIVIAL_TEST
   (this means implementation already exists, or test doesn't test anything real)
5. Report back with:
   - Test file path and content
   - Exact failure output
   - Confirmation: "RED state confirmed"

### Phase 2: Wait for RED gate approval
→ You will receive approval or adjustment instructions before proceeding.
→ Do NOT write implementation until approved.

### Phase 3: GREEN (after approval)
1. Write the minimum code needed to make the failing test pass
2. Run the full test suite — ALL tests (old + new) must pass
3. If existing tests break → fix the regression before proceeding
4. Report: tests passing, coverage delta

### Phase 4: REFACTOR
1. Review your implementation for: naming, duplication, complexity
2. Refactor if needed — keep it clean
3. Run tests again — must still pass
4. Report: DONE with summary of files changed, tests added

## Output Format
Use exactly these status codes:
- RED_CONFIRMED: <test file> <failure output>
- TRIVIAL_TEST: test passed immediately — something is wrong
- GREEN_DONE: all tests pass
- DONE: refactor complete, ready for verify
- NEEDS_CONTEXT: <question>
- BLOCKED: <reason>
```

### RED gate pause

After sub-agent reports `RED_CONFIRMED`, **pause and show the user**:

```
── RED STATE CONFIRMED ─────────────────────────────────────
Task: <task-title> (<task-id>)
Branch: <branch-name>

Test: <test-file-path>
<test-content-snippet>

Failure output:
<failure-output>

This test fails because the implementation doesn't exist yet.
Does this test correctly capture the requirement?

[yes] Proceed to implementation
[adjust] Revise the test — describe what to change
────────────────────────────────────────────────────────────
```

**If user says `adjust`**: pass adjustment instructions back to the sub-agent, wait for new `RED_CONFIRMED`, pause again.

**If sub-agent reports `TRIVIAL_TEST`**:
```
WARNING: Test passed immediately without implementation.
Either the code already exists, or the test is too trivial.
Sub-agent will revise — please review the new test carefully.
```

**Once user approves RED**: send approval to sub-agent → it proceeds to GREEN → REFACTOR → reports `DONE`.

### Update subState during TDD

```bash
# After RED confirmed (waiting for approval)
jq '.taskLoop.subState = "CODING"' \
  docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
```

---

## Step 4: VERIFY — Tests + Preflight

Update subState:
```bash
jq '.taskLoop.subState = "VERIFYING"' \
  docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
```

### Run test suite + coverage

Read coverage threshold from tech stack (default 80%):
```bash
THRESHOLD=$(grep -i "coverage" "docs/specs/$FEATURE_SLUG/tech-stack.md" 2>/dev/null \
  | grep -oP '\d+(?=%)' | head -1)
THRESHOLD=${THRESHOLD:-80}
```

Run tests and check coverage. If coverage < threshold:
```
Coverage is <X>%. Threshold is <THRESHOLD>%.
Options:
  [add-tests]  Add more tests to reach threshold (routes back to TDD sub-agent)
  [proceed]    Proceed anyway (recorded as known gap)
```

If any tests fail → set subState back to CODING, re-dispatch TDD sub-agent with failure context.

### bd preflight check

```bash
PREFLIGHT=$(bd preflight --check --json 2>/dev/null)
PREFLIGHT_PASS=$(echo "$PREFLIGHT" | jq '.pass // false')
```

If preflight fails → route back to CODING:
```bash
echo "Preflight failed. Failing checks:"
echo "$PREFLIGHT" | jq -r '.issues[]?.message' 2>/dev/null
echo "Routing back to CODING sub-state to fix preflight issues."
jq '.taskLoop.subState = "CODING"' \
  docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
# Re-dispatch TDD sub-agent with preflight issues as context
```

---

## Step 5: REVIEW — Per-task Code Review

Update subState:
```bash
jq '.taskLoop.subState = "REVIEWING"' \
  docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
```

Dispatch `c4flow:review` sub-agent for the current task branch diff vs main.

### Severity routing

| Severity | Action |
|----------|--------|
| CRITICAL | Block — fix required. Route back to CODING |
| HIGH | Block — fix required. Route back to CODING |
| MEDIUM | Advisory — surface to user, proceed to PR |
| LOW | Advisory — surface to user, proceed to PR |
| Clean | Proceed directly to PR |

If CRITICAL/HIGH findings:
```bash
echo "Review blocked by CRITICAL/HIGH findings. Routing back to TDD sub-agent."
jq '.taskLoop.subState = "CODING"' \
  docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
# Dispatch implementer sub-agent with review findings as context
```

---

## Step 6: PR + MERGE

After review passes, invoke `c4flow:pr` for the task branch:

```bash
# c4flow:pr creates the PR for the current branch
# After PR is created and merged to main, capture PR number
PR_NUMBER=<returned-by-c4flow:pr>
MERGED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

---

## Step 7: CLOSE + SYNC

> **Resume entry point for `subState == "CLOSING"`** — if arriving here via resume (Step 0.5 was skipped), start from the `bd close` command below.

Update subState to CLOSING:
```bash
jq '.taskLoop.subState = "CLOSING"' \
  docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
```

### Close the bead

```bash
bd close "$TASK_ID" --reason "Implemented: $TASK_TITLE. PR: #$PR_NUMBER. Branch: $BRANCH_NAME merged to main."
```

### Sync to DoltHub

```bash
bd dolt commit -m "close: task $TASK_ID done" 2>/dev/null
bd dolt push 2>/dev/null && echo "Synced: task $TASK_ID closed"
```

### Record in completedTasks + clear current

```bash
jq --arg id "$TASK_ID" \
   --argjson pr "$PR_NUMBER" \
   --arg merged_at "$MERGED_AT" \
   '.taskLoop.completedTasks += [{ id: $id, pr: $pr, mergedAt: $merged_at }]
    | .taskLoop.currentTaskId = null
    | .taskLoop.currentTaskSlug = null
    | .taskLoop.currentBranch = null
    | .taskLoop.subState = null' \
  docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json
```

---

## Completion Gate → Advance to INFRA

After closing each task, check if more work remains:

```bash
REMAINING=$(bd ready --assignee "$ACTOR" --json 2>/dev/null | jq 'length')
```

If `REMAINING` > 0: run inter-iteration beads sync before the next pickup:

```bash
# Inter-iteration sync: pull latest bead states to prevent stale claims
bd dolt pull 2>/dev/null && echo "Beads synced before next pickup" \
  || echo "WARNING: Beads sync failed — using local data"
```

Then loop back to Step 1 (PICKUP). Step 0.5 (full Dolt+Git sync) runs once per session on entry; inter-iteration sync only refreshes bead state from DoltHub.

If `REMAINING` == 0, verify all epic tasks are closed:
```bash
OPEN_COUNT=$(bd list --json 2>/dev/null | \
  jq --arg epic "$EPIC_ID" '[.[] | select(.status != "closed")] | length')
```

If `OPEN_COUNT` == 0:
```bash
# All tasks done — advance to DEPLOY
jq '
  .currentState = "INFRA"
  | .completedStates += ["CODE_LOOP"]
  | .taskLoop = null
  | .failedAttempts = 0
  | .lastError = null
' docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
  && mv -f docs/c4flow/.state.json.tmp docs/c4flow/.state.json

echo "CODE_LOOP complete. All tasks closed. Advancing to INFRA."
```

If `OPEN_COUNT` > 0 but `REMAINING` == 0:
```
Some tasks exist but none are ready for <actor>.
Possible: tasks blocked on external dependencies, or assigned to other people.
```
Show blocked tasks and ask user how to proceed.

---

## Resume Logic

On entry to CODE_LOOP skill, if `taskLoop.subState` is non-null:

> **Step 0.5 (Pre-flight Sync)** runs for all resume states **except `CLOSING`**. Run Step 0.5 first, then jump to the resume action below.

| subState | Run Step 0.5? | Resume action |
|----------|--------------|---------------|
| `CODING` | ✅ Yes | Ask user: "Re-run TDD from RED, or continue from where you left off?" |
| `VERIFYING` | ✅ Yes | Re-run test suite + bd preflight (skip TDD) |
| `REVIEWING` | ✅ Yes | Re-dispatch `c4flow:review` (skip TDD + verify) |
| `CLOSING` | ❌ Skip | Re-run `bd close` + `bd dolt push` (skip everything else) |
| `BLOCKED` | ✅ Yes | Show block reason, wait for user to resolve |

Always confirm branch checkout before resuming:
```bash
git checkout "$CURRENT_BRANCH" 2>/dev/null || echo "WARNING: branch not found — may need to recreate"
```

---

## Rules

**Never:**
- Start on `main` — always create task branch first
- Skip the RED gate pause — human approval is required before GREEN
- Run multiple task loops in parallel — this is a serial loop
- Proceed when preflight fails — fix and re-verify
- Proceed when CRITICAL/HIGH review findings exist — fix first
- Use `bd list --status open` for task discovery — use `bd ready` (blocker-aware)
- Forget `--reason` on `bd close` — audit trail is required

**Always:**
- Resolve actor before any `bd` command
- `git pull` before branching
- Sync (`bd dolt push`) at claim and at close
- Write `subState` to `.state.json` at every transition
- Provide full task text to sub-agents — don't make them read files

---

## Prompt Templates

- `skills/code/implementer-prompt.md` — base TDD sub-agent template
- `skills/code/spec-reviewer-prompt.md` — spec compliance reviewer
- `skills/code/code-quality-reviewer-prompt.md` — quality reviewer

---

## .state.json taskLoop Schema

```json
{
  "currentState": "CODE_LOOP",
  "taskLoop": {
    "currentTaskId": "bd-a1b2",
    "currentTaskSlug": "add-login-endpoint",
    "currentBranch": "feat/bd-a1b2-add-login-endpoint",
    "subState": "CODING",
    "completedTasks": [
      { "id": "bd-0001", "pr": 12, "mergedAt": "2026-03-19T10:00:00Z" }
    ],
    "failedTasks": []
  }
}
```

`subState` values: `CODING` | `VERIFYING` | `REVIEWING` | `CLOSING` | `BLOCKED`
