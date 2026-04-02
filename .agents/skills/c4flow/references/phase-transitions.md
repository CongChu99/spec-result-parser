# c4flow Phase Transitions

## Gate Conditions

Each state transition requires its gate condition to be met before advancing.

| From → To | Gate Condition | How to Check |
|-----------|---------------|--------------|
| IDLE → RESEARCH | User provides feature idea | User input received |
| RESEARCH → SPEC | `research.md` exists and user confirmed | Check `docs/specs/<feature>/research.md` exists |
| SPEC → DESIGN | All spec artifacts exist and user approved | Check `proposal.md`, `tech-stack.md`, `spec.md`, `design.md` in `docs/specs/<feature>/` |
| DESIGN → BEADS | Design system + mockups approved | User confirmation |
| BEADS → CODE_LOOP | Epic + tasks created, user confirmed | Check beads epic or `tasks.md` exists |
| CODE_LOOP (per task) | TDD → verify → review → PR → merge per task | Each task: tests pass, preflight pass, 0 CRITICAL/HIGH, PR merged |
| CODE_LOOP → INFRA | All tasks closed (`bd ready` returns empty) | `bd ready --assignee <actor>` returns 0 tasks |
| INFRA → DEPLOY | Infrastructure provisioned | `infraState.githubSecretsConfigured == true` in `.state.json` |
| DEPLOY → DONE | Deploy verified healthy | Health check passed |

> **Note**: TEST, REVIEW, VERIFY, PR, and MERGE are no longer top-level states. They execute per-task inside the CODE_LOOP task loop. Each task gets its own TDD cycle, verification, review, and PR before the next task starts.

## Error Handling

### Sub-Agent Status Codes

| Status | Meaning | Orchestrator Action |
|--------|---------|-------------------|
| DONE | Task completed successfully | Close task, advance state |
| DONE_WITH_CONCERNS | Completed but with noted issues | Close task, log concerns as new issue, advance |
| BLOCKED | Cannot proceed | Pause state, ask user for guidance |
| NEEDS_CONTEXT | Missing information | Pause state, ask user for info, then resume |

### Failure Recovery

| Scenario | Behavior |
|----------|----------|
| Phase fails (build, tests, etc.) | Increment `failedAttempts`, retry up to 3 times |
| 3+ consecutive failures | Escalate: suggest re-examining spec/design, offer to go back |
| User wants to go back | Set `currentState` to desired state, remove subsequent states from `completedStates` |
| State file missing | Create fresh `.state.json` with IDLE state, warn user |
| State file corrupt (invalid JSON) | Create fresh `.state.json` with IDLE state, warn user about lost state |

### Resume Behavior

When `/c4flow:run` is invoked and `.state.json` already exists:

1. Read `.state.json`
2. If `currentState` is not IDLE or DONE:
   - Ask user: "Resume from {currentState}?"
   - Check for partial output (e.g., `research.md` exists but state is still RESEARCH)
   - If partial output found, ask user: "Found existing {file}. Reuse it or regenerate?"
3. If `currentState` is DONE:
   - Ask user: "Start new feature or review completed?"
