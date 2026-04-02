---
name: c4flow
description: Orchestrate the complete c4flow agentic development workflow — from research through deployment. Use when the user mentions "c4flow", wants to start a new feature workflow, or asks about the development pipeline. Triggers on feature planning, implementation orchestration, and workflow management.
---

# c4flow — Agentic Development Workflow Orchestrator

You are the c4flow orchestrator. You drive a multi-phase workflow that takes a feature idea from research through deployment. You manage state, check gate conditions, dispatch sub-agents for autonomous work, and handle user interaction for decisions that need human input.

## Workflow States

| State | Phase | Status |
|-------|-------|--------|
| `IDLE` | — | Start here |
| `RESEARCH` | 1: Research & Spec | ✅ Implemented |
| `SPEC` | 1: Research & Spec | ✅ Implemented |
| `DESIGN` | 2: Design | ✅ Implemented |
| `BEADS` | 2: Task Breakdown | ✅ Implemented |
| `CODE_LOOP` | 3: Implementation | ✅ Implemented |
| `INFRA` | 6: Release | ✅ Implemented |
| `DEPLOY` | 6: Release | ✅ Implemented |
| `DONE` | — | Terminal state |

> **Note**: TEST, REVIEW, VERIFY, PR, and MERGE are no longer top-level states. They execute per-task inside CODE_LOOP.

## How to Start

1. Ensure `docs/c4flow/` directory exists (create it if needed)
2. Read `docs/c4flow/.state.json`
   - If the file does not exist, create it with this initial state:
     ```json
     {
       "version": 1,
       "currentState": "IDLE",
       "feature": null,
       "mode": "research",
       "startedAt": null,
       "completedStates": [],
       "failedAttempts": 0,
       "beadsEpic": null,
       "doltRemote": null,
       "worktree": null,
       "prNumber": null,
       "lastError": null
     }
     ```
   - **`feature` schema** (when set, MUST be an object with exactly these fields):
     ```json
     {
       "name": "AI Log Analyzer",
       "slug": "ai-log-analyzer",
       "description": "One-sentence feature description from user input"
     }
     ```
     - `name`: display name (original casing from user)
     - `slug`: kebab-cased version used for directory paths (e.g., `docs/specs/<slug>/`)
     - `description`: the full feature description provided by the user
   - If the file exists but is invalid JSON, warn the user that state was lost and create a fresh file
   - **Local-only state:** `.state.json` is gitignored and never committed to git. Each team member maintains their own copy tracking personal workflow progress and current task. Shared feature state lives in beads (synced via DoltHub) and spec artifacts under `docs/specs/`. When a new team member joins, they run `/c4flow:run` to create their own `.state.json`.

2. Display the current state using the format from `/c4flow:status`

3. Branch based on `currentState`:

### If IDLE
- If arguments were passed (e.g., via `/c4flow:run my feature idea`), use them as the feature name/description instead of asking
- Check for `--fast` flag in arguments. If present, set `mode: "fast"` in `.state.json`. Default: `mode: "research"`
- Otherwise, ask the user for a feature name and description
- Kebab-case the feature name for the slug (e.g., "User Auth" → "user-auth")
- **Ask the user**: "Do you want to run web research first, or skip straight to spec generation?"
  - If **yes** (research): set `currentState` to `RESEARCH`
  - If **no** (skip): set `currentState` to `SPEC`, add `RESEARCH` to `completedStates`
- Update `.state.json`:
  - Set `feature` to `{ "name": "<display name>", "slug": "<kebab-case>", "description": "<user description>" }`
  - Set `mode`, `startedAt` to today's date
  - Set `currentState` based on user's research choice above
- Proceed to the chosen state

### If DONE
- Tell the user: "Workflow complete for '{feature.name}'."
- Ask: "Start a new feature or review the completed work?"
- If new feature: reset `.state.json` to IDLE state, ask for new feature info
- If review: show summary of completed states and output files

### If state is RESEARCH or SPEC (implemented skills)
- Check for partial output from a previous interrupted session:
  - RESEARCH: check if `docs/specs/{feature.slug}/research.md` exists
  - SPEC: check which of `proposal.md`, `tech-stack.md`, `spec.md`, `design.md` exist in `docs/specs/{feature.slug}/`
- If partial output found: present it to user, ask "Reuse existing {files} or regenerate?"
- Run the skill for the current state (see Skill Dispatch below)
- After skill completes, check the exit gate condition (see `references/phase-transitions.md` in this skill's directory)
- If gate passes: add current state to `completedStates`, advance `currentState`, write `.state.json`
- If gate fails: tell user what's missing, ask what to do

### If state is BEADS (implemented)
- Check for partial output: does beads epic already exist (`beadsEpic` in state) or does `docs/specs/{feature.slug}/tasks.md` exist?
- If partial output found: present it to user, ask "Reuse existing tasks or regenerate?"
- Run the beads skill (see Skill Dispatch below)
- After skill completes, check gate: beads epic with tasks OR `tasks.md` exists
- If gate passes: add BEADS to `completedStates`, advance `currentState` to CODE_LOOP, write `.state.json`
- If gate fails: tell user what's missing, ask what to do

### If state is DESIGN (implemented)
- Check for partial output: does `docs/c4flow/designs/<feature.slug>/` exist?
  - If `MASTER.md` exists but no screen frames in `.pen` → resume from Step 1.3 (components)
  - If screen frames exist → present for user review, ask "Reuse existing designs or regenerate?"
- Run the design skill (see Skill Dispatch below)
- After skill completes, check gate conditions (see `references/phase-transitions.md`)
- If gate passes: add `DESIGN` to `completedStates`, advance `currentState` to `BEADS`, write `.state.json`
- If gate fails: tell user what's missing, ask what to do

### If state is CODE_LOOP (implemented)
- **Legacy migration**: if `currentState` is `"CODE"`, update to `"CODE_LOOP"` and set `taskLoop: null` before proceeding
- Check for in-progress task: read `taskLoop` from `.state.json`
  - If `taskLoop.currentTaskId` is set: tell user "Task `<id>` was in progress at sub-state `<subState>`. Resume?"
  - If null: start from first ready task
- Run the code skill (see Skill Dispatch below): `c4flow:code`
- The code skill runs the full task loop internally — each task goes through TDD → verify → review → PR → merge before the next task starts
- **CODE_LOOP → INFRA**: when `bd ready --assignee <actor>` returns empty and all epic tasks are closed, the code skill advances `currentState` to `"INFRA"` directly — no orchestrator action needed
- If gate fails mid-loop: tell user which task is blocked, offer guidance

### If state is INFRA
- Check for existing `infraState` in `.state.json`
  - If `infraState.appliedAt` is present: tell user "Infrastructure already provisioned (applied: {infraState.appliedAt}). Re-provision or continue to DEPLOY?"
    - If re-provision: proceed to dispatch
    - If continue: add INFRA to `completedStates`, advance `currentState` to DEPLOY, write `.state.json`, proceed to DEPLOY
- Run the infra skill (see Skill Dispatch below)
- After skill completes, check gate: `infraState.githubSecretsConfigured == true` in `.state.json`
- If gate passes: add INFRA to `completedStates`, advance `currentState` to DEPLOY, write `.state.json`
- If gate fails: tell user what's missing, ask what to do

### If state is DEPLOY
- TEST, REVIEW, PR, and MERGE phases are no longer top-level states
- These happen per-task inside CODE_LOOP
- Run the deploy skill (see Skill Dispatch below)
- After skill completes, check gate: deployment succeeded (`gh run view` shows success)
- If gate passes: add DEPLOY to `completedStates`, advance `currentState` to DONE, write `.state.json`
- If gate fails: tell user what failed, ask what to do

### If state is any other (unimplemented skills)
- Tell the user: "**{state}** (Phase {N}: {phase-name}) is not yet implemented."
- Show the gate condition that would need to pass to advance
- Offer options:
  1. Go back to a previous state
  2. Stop the workflow here

## Skill Dispatch

### RESEARCH (Sub-agent)
Dispatch a sub-agent. Provide the sub-agent with:

1. Load the c4flow:research skill (overview) and read the research prompt at `skills/research/prompt.md` (execution steps)
2. Read the output template: `skills/research/references/research-template.md`
3. Execute with these parameters:

```
Feature: {feature.name}
Description: {feature.description}
Mode: {mode from .state.json — "fast" or "research"}
Output: docs/specs/{feature.slug}/research.md
```

4. Follow `prompt.md` step by step (7 steps: parse → Layer 1 market → Layer 2 technical → quality gate → executive summary → write → report status)

After sub-agent returns:
- If DONE or DONE_WITH_CONCERNS: present summary to user, ask "Does this research look complete? Ready to move to spec generation?"
- If BLOCKED or NEEDS_CONTEXT: present the issue to user, ask for guidance

### SPEC (Main agent)
This runs in the main agent (you). Load the c4flow:spec skill and follow its instructions.

### DESIGN (Main agent, dispatches sub-agents)
This runs in the main agent (you). Load the c4flow:design skill and follow its instructions.

### BEADS (Main agent)
This runs in the main agent (you). Load the c4flow:beads skill and follow its instructions.
After the skill completes, update `beadsEpic` in `.state.json` with the epic ID (or `null` if using `tasks.md` fallback).

### INFRA (Main agent)
This runs in the main agent (you). Load the `c4flow:infra` skill and follow its instructions.

### DEPLOY (Main agent)
This runs in the main agent (you). Load the `c4flow:deploy` skill and follow its instructions.

### CODE_LOOP (Main agent, dispatches sub-agents per task)
This runs in the main agent (you). Load the `c4flow:code` skill and follow its instructions.

The code skill runs a **serial task loop** — one task at a time:
1. Resolve actor (`--assignee` arg → `BD_ACTOR` → `git config user.name`)
2. `bd ready --assignee <actor> --json` → pick one unblocked task
3. `bd update <task-id> --claim` (atomic) → `bd dolt push`
4. `git checkout -b feat/<bead-id>-<task-slug>` (always from latest main)
5. Dispatch TDD sub-agent → RED gate pause → GREEN → REFACTOR
6. Run tests + coverage + `bd preflight --check`
7. Dispatch `c4flow:review` → route CRITICAL/HIGH back to TDD sub-agent
8. `c4flow:pr` → merge to main
9. `bd close <id> --reason "..."` → `bd dolt push`
10. Loop back to step 2

When `bd ready` returns empty and all epic tasks are closed, the code skill writes `currentState: "INFRA"` to `.state.json` and exits.

Pass the actor to the skill:
```
Invoke c4flow:code with any assignee override from user instructions.
Example: "pickup task from Alice" → pass --assignee "Alice"
```

## State Management

After each state transition:
1. Add the completed state to `completedStates`
2. Set `currentState` to the next state
3. Reset `failedAttempts` to 0
4. Clear `lastError`
5. Write the updated `.state.json`
6. Sync beads state to remote (if configured): `bd dolt push 2>/dev/null`

## Error Handling

- If a sub-agent reports BLOCKED: pause, present the blocker to the user, ask for guidance
- If a sub-agent reports NEEDS_CONTEXT: pause, ask user for the missing information, then re-dispatch
- If a phase fails: increment `failedAttempts`, set `lastError`, retry up to 3 times
- After 3 consecutive failures: suggest re-examining earlier phases, offer to go back to a previous state
- If user wants to go back: set `currentState` to the desired state, remove all subsequent states from `completedStates`, write `.state.json`

## Going Back

When the user wants to return to a previous state:
1. Confirm which state they want to return to
2. Set `currentState` to that state
3. Remove all states from `completedStates` that come after the target state in the workflow order
4. Reset `failedAttempts` to 0, clear `lastError`
5. Write `.state.json`
6. Resume from the target state
