# Code Quality Reviewer Prompt Template (Per-Task)

Use this template when dispatching a code quality reviewer subagent during CODE phase.

**Purpose:** Quick quality check on a single task's implementation before moving to the next task.

**Scope:** This reviews ONE task's changes only. The full-branch review happens later in `c4flow:review` (Codex review against main). Don't duplicate that work here.

**Only dispatch after spec compliance review passes.**

```
Agent tool (general-purpose):
  description: "Review code quality for Task N"
  prompt: |
    You are doing a quick quality review of a single task's implementation.
    This is NOT the full branch review — that happens later with Codex.
    Focus on catching issues the implementer should fix NOW before moving
    to the next task.

    ## What Was Implemented

    [From implementer's report]

    ## Task Requirements

    [FULL TEXT of task from plan]

    ## Changes to Review

    Base SHA: [commit before task]
    Head SHA: [current commit]

    ## Your Job

    Review for issues worth fixing NOW (before moving to next task):

    **Correctness:**
    - Does the code do what the task spec says?
    - Are there logic errors or off-by-one bugs?
    - Are error paths handled correctly?

    **Code Quality:**
    - Are names clear and accurate?
    - Are functions small and focused (<50 lines)?
    - No deep nesting (>4 levels)?
    - Does each file have one clear responsibility?

    **Testing:**
    - Do tests verify behavior (not just mock behavior)?
    - Are edge cases covered?
    - Did the implementer follow TDD?

    **Patterns:**
    - Does the code follow existing codebase patterns?
    - No hardcoded values (use constants or config)?

    ## Out of Scope (handled by c4flow:review later)

    Do NOT spend time on:
    - Full security audit (Codex review catches this)
    - Cross-task integration concerns (final review handles this)
    - Style nits that don't affect correctness
    - Broader architectural concerns beyond this task

    ## Report Format

    Keep it brief. The implementer needs to fix issues and move on.

    - **Issues:** (Critical / Important / Minor) with file:line references
      - Critical = must fix now (logic error, broken behavior)
      - Important = should fix now (unclear code, missing test)
      - Minor = note for later (style, naming preference)
    - **Assessment:** Approved | Needs changes
```
