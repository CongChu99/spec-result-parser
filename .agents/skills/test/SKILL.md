---
name: c4flow:test
description: Run unit and integration tests with coverage checking. Auto-detect framework, classify failures, enforce coverage threshold before advancing to review. Use when the user wants to run tests, check coverage, or validate implementation quality. Triggers on "run tests", "check coverage", "test suite", or when the code phase completes.
---

# /c4flow:test — Unit + Integration Tests

**Phase**: 4: Testing
**Agent type**: Sub-agent (dispatched by orchestrator)
**Status**: Implemented

## Overview

Run the full test suite after implementation is complete. Detect the test framework, execute tests, classify failures (code bugs vs environment issues), and check coverage against threshold. Does NOT write test files.

**Based on**: [run-tests](https://github.com/CongChu99/automation-test) skill with coverage checking added for c4flow workflow.

## Input
- Feature name (kebab-cased) from `.state.json`
- `docs/specs/<feature>/tech-stack.md` — framework & testing stack info
- `docs/specs/<feature>/spec.md` — expected behaviors (Given/When/Then scenarios)
- Coverage threshold (from `tech-stack.md` or default 80%)

## Output
- Test results: pass/fail count, duration, coverage percentage
- Failure analysis: root cause suggestions with confidence levels
- Gate decision: pass (advance to REVIEW) or fail (report issues)

## Gate Condition
```
TEST → REVIEW: Tests pass, coverage >= threshold
```

## Capabilities

| Capability | Source | Details |
|---|---|---|
| Framework detection | run-tests | 16 frameworks: Jest, Vitest, Mocha, Ava, pytest, Go, Cargo, .NET, Mix, Gradle, Maven, PHPUnit, RSpec, Minitest, Dart, Swift, Make |
| JS runner differentiation | run-tests | Detects Jest vs Vitest vs Mocha vs Ava from config + devDependencies |
| Monorepo awareness | run-tests | nx, turbo, lerna, pnpm-workspace detection |
| Failure classification | run-tests | Tier 1 (code bugs: deep analysis) / Tier 2 (env issues: quick fix) |
| Deep analysis | run-tests | Up to 5 unique-file slots, ±10 lines context, HIGH/MEDIUM/LOW confidence |
| Coverage checking | **NEW** | Parse coverage output, check against threshold |

## Helper Scripts

Located in `skills/test/scripts/`:

| Script | Used by sub-agent? | Purpose |
|--------|:------------------:|---------|
| `detect-framework.sh` | ✅ Yes | Auto-detect test framework from project files (16 frameworks) |
| `classify-failure.sh` | ✅ Yes | Classify test output as Tier 1 (code) or Tier 2 (env) |
| `format-output.sh` | ✅ Yes | Format results in concise/detailed/JSON mode |
| `parse-args.sh` | ❌ No | Inherited from `run-tests` for standalone usage. Sub-agent receives params from orchestrator, not CLI args |

## Execution

Follow `prompt.md` step by step.

## How Other Phases Use This Output

| Test Output | Used By |
|---|---|
| Pass/fail status | Gate condition for REVIEW phase |
| Coverage % | Gate condition for REVIEW phase |
| Uncovered file list | REVIEW phase uses as context for code review |
| Failure analysis | If BLOCKED, orchestrator presents to user for guidance |
