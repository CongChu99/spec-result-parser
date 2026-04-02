# Task Decomposition: Parallelism-First

## Core Principle

**Minimize sequential chains.** Every `blocks` dependency is a tax on velocity — someone waits idle while someone else finishes. Decompose so the team is always working.

---

## Layer Analysis (Critical)

After drafting tasks, analyze them in layers:

1. **Layer 0 (zero dependencies)** — tasks with no blockers. Assign all to start immediately.
2. **Layer 1** — tasks blocked only by Layer 0.
3. **Layer 2** — tasks blocked only by Layer 1.
4. ...

If a team member owns multiple layers, they're a **bottleneck**. Redistribute.

### Layer Command

```bash
bd graph <epic-id> --box
# Or manually:
bd ready --json   # shows what's unblocked right now
```

---

## Anti-Patterns

### ❌ Sequential Chain (BAD — screenshot example)
```
Task A → Task B → Task C → Task D → Task E
```
Only one person can work at a time. Velocity = 1 task per sprint.

**Why it happens:** Breaking by "phase" (DB → API → UI → Integration) instead of by component.

**Fix:** Extract Layer 0 tasks from every component. Design mock contracts so frontend and backend can start in parallel.

### ❌ Mega-Task (BAD)
A single task takes 2 weeks. No granularity for progress or parallel work.

**Fix:** Break at natural seams — API contract, data model, UI component, etc.

### ❌ False Dependency (BAD)
Two tasks "seem related" so they're marked `blocks`. In reality they can be stubbed/faked.

**Examples:**
- "API" and "DB schema" can start in parallel if schema is designed from spec first
- "Login UI" and "Auth middleware" can start in parallel with a mock auth function
- "Frontend" and "Backend" can start in parallel if API contract is defined upfront

---

## How to Maximize Parallelism

### 1. Define contracts before breaking

Before writing tasks, answer:
- What interfaces cross team boundaries?
- What can each side do with just the contract (no real implementation)?

### 2. Stub/contract-first decomposition

```
Layer 0:
  - Define API contract (OpenAPI spec)
  - Design DB schema
  - Set up project scaffolding
  - Create mock auth function

Layer 1 (uses Layer 0 outputs):
  - Implement DB schema (from schema design)
  - Implement API endpoints (from contract)
  - Build UI components (from mock auth + contract)

Layer 2:
  - Wire real auth
  - Integration tests
```

### 3. Design interfaces upward

When frontend and backend both need data:
1. Agree on the data shape first (shared type/interface)
2. Frontend builds UI against the shape
3. Backend implements to match the shape
4. Neither waits on the other

### 4. Feature flags for unfinished dependencies

If B needs A but A is behind schedule:
- Add a feature flag to disable B's dependency on A
- B starts, uses stub/mock for A's output
- When A lands, flip the flag

### 5. Use `waits-for` not `blocks` for fan-in

```
Task: Aggregate dashboard
waits-for: Task A (user data), Task B (order data), Task C (inventory data)
```
The aggregate task genuinely needs all three. But A, B, C are fully parallel.

---

## Parallelism Score

After drafting, rate the graph:

| Score | Description | Indicator |
|-------|-------------|-----------|
| 5 | Maximum parallel | Multiple people working every day |
| 4 | Good | Some sequential chains, < 3 layers |
| 3 | Acceptable | Occasional bottlenecks, ~4 layers |
| 2 | Poor | One person drives most, > 5 layers |
| 1 | Terrible | Sequential chain (screenshot example) |

**Target: Score ≥ 4.** If lower, redesign the decomposition.

---

## Team-Based Decomposition

### Solo
- Break by component (backend / frontend / infra)
- Sequential only when truly necessary
- Use stubs to unblock frontend from backend

### 2-3 people
- Assign tasks by component, not by layer
- Each person owns their full stack (DB + API + UI for their feature)
- Cross-component tasks = integration layer (last)

### 4+ people
- Assign by component layer (DB person, API person, UI person)
- Design contracts early so all layers can start Day 1
- Use `waits-for` for integration tasks

---

## Quick Checklist

- [ ] Layer 0 tasks exist and are non-trivial (not just "setup")
- [ ] No sequential chains longer than 3 tasks
- [ ] Team members can work independently on Layer 0
- [ ] API contracts / data shapes are defined before breaking tasks
- [ ] `waits-for` used for fan-in aggregation tasks
- [ ] Parallelism score ≥ 4
