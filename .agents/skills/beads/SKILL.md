---
name: c4flow:beads
description: Break down a feature into a detailed beads epic with rich task metadata — priority, assignee, acceptance criteria, design notes, dependency graph (blocks/waits-for/conditional), and spec links. Use when the user wants to plan work, decompose features into tasks, create an epic, or set up a dependency-aware work graph. Triggers on task breakdown, epic creation, work planning, or "break this into tasks".
---

# /c4flow:beads — Task Breakdown & Work Graph

**Phase**: 2: Design & Beads
**Agent type**: Main agent (interactive with user)
**Status**: Implemented

## Input
- `docs/specs/<feature>/spec.md` (from SPEC phase)
- `docs/specs/<feature>/design.md` (from SPEC phase)
- `docs/c4flow/designs/<feature>/MASTER.md` (from DESIGN phase — design tokens, component list)
- `docs/c4flow/designs/<feature>/screen-map.md` (from DESIGN phase — screens and component breakdown)

> Note: If `MASTER.md` and `screen-map.md` don't exist (DESIGN phase was skipped), proceed with only `spec.md` and `design.md`. The DESIGN phase is not mandatory for the workflow to function.

## Output
- Beads epic with rich child tasks (if `bd` installed)
- OR `docs/specs/<feature>/tasks.md` (fallback)

## Instructions

You are the task breakdown agent. Read the spec and design, ask planning questions, then decompose the feature into a fully detailed beads work graph — with proper priorities, descriptions, notes, acceptance criteria, assignees, and dependencies.

### Step 1: Read Context

Read these files to understand the feature:
- `docs/specs/<feature>/spec.md`
- `docs/specs/<feature>/design.md`
- `docs/specs/<feature>/proposal.md` (if exists)

### Step 2: Pre-Breakdown Questions

Ask the user:
1. Team members? (name/role of each — "solo" if just the user)
2. Expected timeline? (days, weeks, sprint)
3. Spec + design approved?
4. Any hard ordering constraints, or mostly parallel?
5. **Granularity level** — how detailed should the breakdown be?

   After reading the spec and design, estimate how many tasks each level would produce for *this specific feature*, then present as a concrete choice:

   > Based on this feature, here's what each level looks like:
   > **A) Compact** (~N tasks) — full components or layers. Best for solo devs or short sprints.
   > **B) Standard** (~N tasks) — meaningful units of work, 1–2 days each. Good default.
   > **C) Detailed** (~N tasks) — single file or function group per task. Good for larger teams.
   > **D) Super detailed** (~N tasks) — atomic steps, hours not days. Maximum parallelism.

   The N values are your estimates based on the actual feature scope — not fixed numbers. Make them feel real and grounded.

   Default to **B (Standard)** if user doesn't specify. Remember this choice for Step 4.

### Step 2b: Pre-Breakdown Analysis (before writing tasks)

**Read the decomposition guide first:**
> See [references/task-decomposition.md](references/task-decomposition.md) for parallelism-first principles and anti-patterns.

Analyze the spec to identify:
1. **Cross-team boundaries** — where does data/interface cross people? (these are contract points)
2. **Layer 0 candidates** — what can start with zero dependencies? (schema design, API contract, scaffolding, mocks)
3. **Stub opportunities** — what can be stubbed/faked so one side doesn't wait for the other?
4. **Integration seams** — where do pieces actually need to connect? (these are the only true `blocks`)

**Critical question to answer before breaking tasks:**
> "Can every team member start working on something meaningful on Day 1?"

If no → redesign the decomposition. Layer 0 must not be empty or trivial.

> **Anti-pattern warning:** A breakdown where tasks go DB → API → UI → Integration in strict sequence scores 1/5 on parallelism. This means only one person works at a time. Break by component AND by layer instead.

### Step 3: Check Beads Installation

```bash
command -v bd 2>/dev/null && echo "BD_INSTALLED" || echo "BD_MISSING"
[ -d ".beads" ] && echo "BEADS_INIT" || echo "BEADS_NOT_INIT"
```

| `bd`? | `.beads/`? | Action |
|-------|-----------|--------|
| Yes | Yes | → Step 4a |
| Yes | No | Run `c4flow:init`, then → Step 4a |
| No | — | Offer `c4flow:init`. If declined → Step 4b |

### Step 4a: Create Epic + Tasks (Beads Path)

#### Check for duplicates

```bash
bd duplicates --json 2>/dev/null
bd list --status open --json 2>/dev/null
```

If overlapping open issues exist, ask user whether to reuse, merge, or create fresh.

#### Create the epic

Write a description file first to avoid shell escaping issues:

```bash
cat > /tmp/epic-desc.md << 'EOF'
## Feature: <feature-name>

**Spec:** docs/specs/<feature>/spec.md
**Design:** docs/specs/<feature>/design.md
**Proposal:** docs/specs/<feature>/proposal.md

### Summary
<2-3 sentence summary from spec>

### Success Criteria
<from spec acceptance criteria>
EOF

bd create "<feature-name>" -t epic -p 1 \
  --body-file /tmp/epic-desc.md \
  --spec-id "docs/specs/<feature>/spec.md" \
  -l "c4flow-epic,phase:beads" \
  --json
```

Save the epic ID — store in `.state.json` as `beadsEpic`.

#### Create child tasks with full metadata

For each task, write a description file, then create using `--parent` for auto-numbered hierarchical IDs:

```bash
# 1. Write detailed description to file
cat > /tmp/task-desc.md << 'EOF'
## Context
Why this task exists and how it fits the feature.

## Input
What's needed to start: files, APIs, data, outputs from other tasks.

## Deliverables
- Concrete output 1
- Concrete output 2

## Files to modify
- `src/auth/login.ts`
- `src/api/routes.ts`

## Technical notes
Implementation hints, patterns to follow, gotchas.

## Spec reference
docs/specs/<feature>/spec.md#<requirement-section>
EOF

# 2. Create task with --parent (auto-numbered child ID)
bd create "Task title" -t task \
  -p <0-4> \
  --parent <epic-id> \
  --body-file /tmp/task-desc.md \
  --spec-id "docs/specs/<feature>/spec.md" \
  -l "<component>,<size>" \
  --json
```

#### Set assignee

```bash
bd update <task-id> --assignee "<person-name>" --json
```

For solo projects, claim immediately:
```bash
bd update <task-id> --claim --json
```

#### Add acceptance criteria and notes

After creating each task, enrich it with structured metadata. Write to temp files and pipe in:

```bash
# Acceptance criteria — the "done" conditions
cat > /tmp/acceptance.md << 'EOF'
- [ ] Unit tests pass with >80% coverage
- [ ] API returns correct response format per spec
- [ ] Error handling for all edge cases in spec section 3.2
- [ ] No regressions in existing tests
EOF
cat /tmp/acceptance.md | bd edit <task-id> --acceptance --stdin

# Design notes — architecture decisions for this task
cat > /tmp/design.md << 'EOF'
Use the repository pattern from design.md section 2.1.
JWT validation middleware already exists in src/middleware/auth.ts — extend it.
Database schema change requires migration file.
EOF
cat /tmp/design.md | bd edit <task-id> --design --stdin

# Notes — implementation context, warnings, references
cat > /tmp/notes.md << 'EOF'
Related PR: #142 (similar pattern)
Watch out for race condition in concurrent token refresh.
See design.md section 4 for caching strategy.
EOF
cat /tmp/notes.md | bd edit <task-id> --notes --stdin
```

#### Set up dependencies

Dependencies control the execution order. Choose the right type based on the real relationship:

**Blocking types** (affect `bd ready`):

| Type | When | Example |
|------|------|---------|
| `blocks` (default) | B literally cannot start without A's output | DB schema → API layer |
| `conditional-blocks` | B runs only if A fails | Fallback/error paths |
| `waits-for` | B waits for ALL of A's children | Fanout aggregation |

**Non-blocking types** (graph annotations):

| Type | When | Example |
|------|------|---------|
| `related` | Loose connection | Two auth tasks |
| `discovered-from` | Found during work | Bug found while implementing |
| `caused-by` | Root cause link | Bug → underlying issue |
| `validates` | Test/verification | Test task → feature task |
| `tracks` | Progress tracking | Tracking issue → work items |
| `supersedes` | Replaces another | New approach → old approach |

```bash
# B depends on A (A blocks B) — use requirement language
bd dep add <task-B> <task-A>

# With explicit type
bd dep add <task-B> <task-A> --type validates

# Create discovered work linked to parent
bd create "Found bug" -t bug -p 1 --deps discovered-from:<parent-id> --json
```

**Common pitfall — temporal language inverts dependencies:**
- ❌ "Phase 1 comes before Phase 2" → `bd dep add phase1 phase2`
- ✅ "Phase 2 needs Phase 1" → `bd dep add phase2 phase1`

Always think in terms of "what does this task **need** to start?"

#### Add gates for external conditions

When a task depends on something outside beads (PR merge, CI pass, manual approval):

```bash
# Wait for PR to merge before deploying
bd create --type=gate --title="Wait for PR #42" \
  --await-type=gh:pr --await-id=42 --json
bd dep add <deploy-task> <gate-id>

# Manual approval gate
bd create --type=gate --title="Deploy approval" --json
bd dep add <deploy-task> <gate-id>
# Later: bd gate resolve <gate-id> --reason "Approved"
```

#### Labels for categorization

Use lowercase, hyphen-separated. Keep it small:

**Component:** `backend`, `frontend`, `api`, `database`, `infra`
**Size:** `small` (<1 day), `medium` (1-3 days), `large` (>3 days)
**Quality:** `needs-review`, `needs-tests`, `breaking-change`
**C4Flow:** `c4flow-epic`, `phase:beads`, `phase:code`

```bash
bd label add <task-id> backend,medium --json
```

#### Verify the work graph

```bash
# Check for dependency cycles
bd dep cycles 2>/dev/null

# View dependency tree
bd dep tree <epic-id>

# Visualize as layer diagram (parallel vs sequential)
bd graph <epic-id> --box

# What's ready now?
bd ready --json

# What's blocked and by what?
bd blocked
```

#### Self-check: Parallelism Score

After verifying the graph, score the decomposition:

| Score | Description | Indicator |
|-------|-------------|-----------|
| 5 | Maximum parallel | Multiple people working every day |
| 4 | Good | Some sequential chains, < 3 layers |
| 3 | Acceptable | Occasional bottlenecks, ~4 layers |
| 2 | Poor | One person drives most, > 5 layers |
| 1 | **Terrible** | Sequential chain — one task blocks everything |

If score ≤ 3, redesign. Common fixes:
- Extract contract/schema design into Layer 0
- Stub/mock a dependency so the blocked side can proceed
- Reassign tasks so each person has Layer 0 work

**Never present a score ≤ 2 to the user without flagging it.**

#### Present to user

Show the full breakdown with all metadata:

```
Epic: bd-a1b2 "Feature Name" [P1]
  Spec: docs/specs/<feature>/spec.md

├── Person A (Backend):
│   ├── bd-a1b2.1 [P1] "Create DB schema" [backend,medium]
│   │   Acceptance: migration file, indexes, rollback tested
│   │   Notes: Use design.md section 2.1 schema
│   │
│   └── bd-a1b2.2 [P1] "Build API endpoints" [backend,medium]
│       ⛓ blocked by: bd-a1b2.1 (needs schema)
│       Acceptance: REST endpoints match spec, auth middleware
│
├── Person B (Frontend):
│   └── bd-a1b2.3 [P2] "Login UI component" [frontend,medium]
│       Acceptance: matches Figma, form validation, a11y
│
└── Integration:
    └── bd-a1b2.4 [P1] "Wire frontend to API" [frontend,small]
        ⛓ blocked by: bd-a1b2.2, bd-a1b2.3
        Acceptance: end-to-end login flow works

Layer 0 (parallel): bd-a1b2.1, bd-a1b2.3  ← start immediately
Layer 1:            bd-a1b2.2              ← after schema
Layer 2:            bd-a1b2.4              ← after API + UI
```

Also show `bd ready --json` output. Ask user to review and iterate.

**Include parallelism score in the presentation:**
```
Parallelism Score: 4/5 ✅
Layer 0 (start now): 3 tasks — all unblocked
Layer 1 (after Layer 0): 2 tasks
Layer 2 (integration): 1 task
```

If score ≤ 3, explicitly call it out and propose fixes before finalizing.

### Step 4b: Fallback to tasks.md (no Beads)

Create `docs/specs/<feature>/tasks.md` with the same level of detail as the Beads path. The format must be machine-readable by `c4flow:code` — keep the headings and field names exact.

```markdown
# Tasks: <feature-name>

> Spec: docs/specs/<feature>/spec.md
> Generated: <ISO date>

## Layer 0 (start immediately — no dependencies)

### T-01: <title> [P1] [backend,medium]
- **Status:** open
- **Assignee:** Person A
- **Claimed by:** —
- **Depends on:** none
- **Acceptance criteria:**
  - [ ] ...
  - [ ] ...
- **Description:** Why this task exists and how it fits the feature.
- **Input:** What's needed to start (files, APIs, outputs from other tasks).
- **Deliverables:** Concrete outputs (files, endpoints, migrations).
- **Files:** `src/auth/login.ts`, `src/api/routes.ts`
- **Design notes:** Architecture decisions — patterns to follow, gotchas.
- **Spec ref:** spec.md#requirement-section
- **Notes:** Implementation context, warnings, related work.

### T-02: <title> [P2] [frontend,medium]
- **Status:** open
- **Assignee:** Person B
- **Claimed by:** —
- **Depends on:** none
...

## Layer 1 (after Layer 0 completes)

### T-03: <title> [P1] [backend,medium]
- **Status:** open
- **Assignee:** Person A
- **Claimed by:** —
- **Depends on:** T-01 (needs schema), T-02 (needs UI contract)
...

## Layer 2 (integration)

### T-04: <title> [P1] [fullstack,small]
- **Status:** open
- **Assignee:** Person A
- **Claimed by:** —
- **Depends on:** T-01, T-02, T-03
...
```

**Status lifecycle** — `c4flow:code` updates these fields in place:

| Status | Meaning | Transition |
|--------|---------|-----------|
| `open` | Not started | → `in-progress` when claimed |
| `in-progress` | Being worked on | → `done` or `blocked` |
| `blocked` | Dependency not met | → `open` when unblocked |
| `done` | Completed and merged | Terminal state |

**When claiming a task** (in `c4flow:code`), update the line:
```
- **Status:** in-progress
- **Claimed by:** <actor-name> (<ISO datetime>)
```

**When completing a task**, update:
```
- **Status:** done
```

**Dependency resolution** — `c4flow:code` uses the `Depends on:` field to determine what's safe to start. A task is "ready" when all tasks listed in its `Depends on:` field have `Status: done`. Tasks with `Depends on: none` are always ready.

Tell user: "Using `tasks.md` fallback. Run `/c4flow:init` to install Beads for dependency resolution and atomic task claiming."

### Step 5: Sync to Dolt Remote

After all tasks are created, check if a Dolt remote is configured and push:

```bash
# Check if doltRemote is configured in .state.json
DOLT_REMOTE=$(jq -r '.doltRemote // empty' docs/c4flow/.state.json 2>/dev/null)

if [ -n "$DOLT_REMOTE" ]; then
  echo "Syncing beads to Dolt remote: $DOLT_REMOTE"
  bd dolt push 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ Beads synced to remote"
  else
    echo "⚠️ Dolt push failed — tasks created locally. Run 'bd dolt push' manually to retry."
  fi
fi
```

If push fails due to auth, tell the user to run `dolt login` first, then `bd dolt push`.

### Step 6: Update State

Update `docs/c4flow/.state.json`:
- Set `beadsEpic` to the epic ID (or `null` if fallback)
- Orchestrator handles state transition after gate check

### Step 7: Report Completion

Gate condition:
- **Beads path**: epic exists with ≥1 child task, each has description + acceptance criteria + priority
- **Fallback**: `tasks.md` exists with ≥1 task

```bash
bd dep tree <epic-id>
bd stats --json 2>/dev/null
```

## Quality Checklist

Every task created by this skill should have:
- ✅ Meaningful priority (P0-P4, not all P2)
- ✅ Detailed description via `--body-file` (context, input, deliverables, files, tech notes)
- ✅ Acceptance criteria via `bd edit --acceptance`
- ✅ Assignee (or claimed for solo)
- ✅ Spec link via `--spec-id`
- ✅ Component + size labels
- ✅ Correct dependency type (`blocks` only when truly sequential)
- ✅ Notes with implementation context via `bd edit --notes`
- ✅ Design notes when architecture decisions apply via `bd edit --design`
- ✅ **Parallelism score ≥ 4** — no sequential chains longer than 3 tasks
- ✅ **Layer 0 is non-empty** — every team member can start Day 1
