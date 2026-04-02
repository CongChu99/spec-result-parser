# c4flow:test — Execution Prompt

## Step 1: Parse Input & Resolve Configuration

**Read from orchestrator context:**
- Feature name from `.state.json`
- `docs/specs/<feature>/tech-stack.md` — extract:
  - Testing framework (if specified)
  - Coverage threshold (if specified, otherwise default 80%)
  - Package manager
- `docs/specs/<feature>/spec.md` — keep available for coverage gap analysis

**Initialize internal counters:**

| Counter | Initial | Max | Purpose |
|---------|---------|-----|---------|
| `fix_attempts` | 0 | 3 | Tier 1 auto-fix attempts (Step 6) |

These counters are local to the sub-agent session — not persisted to `.state.json`. The orchestrator tracks `failedAttempts` separately for cross-session retries.

**Resolve test configuration:**

| Priority | Source |
|----------|--------|
| 1 | `testconfig.yml` / `testconfig.yaml` / `testconfig.json` (walk-up from project root) |
| 2 | `tech-stack.md` testing section |
| 3 | Auto-detection (Step 2) |

---

## Step 2: Detect Test Framework

If no explicit command is configured, auto-detect by scanning project files. **First match wins:**

| Priority | Signal | Framework | Command |
|----------|--------|-----------|---------|
| 1 | `package.json` with `scripts.test` | jest/vitest/mocha/ava | `npm test` (or `yarn`/`pnpm`/`bun` if lockfile) |
| 2 | `pytest.ini` / `pyproject.toml` / `setup.cfg` / `tox.ini` | pytest | `pytest` |
| 3 | `go.mod` | go | `go test ./...` |
| 4 | `Cargo.toml` | cargo | `cargo test` |
| 5 | `*.sln` / `*.csproj` | dotnet | `dotnet test` |
| 6 | `mix.exs` | mix | `mix test` |
| 7 | `build.gradle` / `build.gradle.kts` | gradle | `gradle test` |
| 8 | `pom.xml` | mvn | `mvn test` |
| 9 | `phpunit.xml` / `phpunit.xml.dist` | phpunit | `./vendor/bin/phpunit` |
| 10 | `.rspec` / `Gemfile` with rspec | rspec | `bundle exec rspec` |
| 11 | `Gemfile` with minitest | minitest | `bundle exec rake test` |
| 12 | `pubspec.yaml` | dart | `dart test` / `flutter test` |
| 13 | `Package.swift` | swift | `swift test` |
| 14 | `Makefile` with `test` target | make | `make test` |

**JS runner differentiation:** When `package.json` is detected, refine by checking:
- Config files: `vitest.config.*`, `.mocharc.*`, `jest.config.*`, `ava.config.*`
- devDependencies: `vitest`, `mocha`, `ava`, `jest`

**Package manager detection:** `bun.lockb`/`bun.lock` → bun, `yarn.lock` → yarn, `pnpm-lock.yaml` → pnpm, otherwise npm.

**If no framework detected:** Report `BLOCKED` with message "No test framework detected. Check project setup or add a `testconfig.yml`."

---

## Step 3: Run Full Test Suite

Execute the resolved test command, capturing stdout and stderr.

**Apply timeout:** Default 120 seconds (or from config). Kill process after timeout.

**Coverage flags** — append framework-specific coverage flag to command:

| Framework | Coverage Flag |
|-----------|--------------|
| jest | `--coverage` |
| vitest | `--coverage` |
| pytest | `--cov --cov-report=term-missing` |
| go | `-cover -coverprofile=coverage.out` |
| cargo | (use `cargo tarpaulin` if available, else skip) |
| dotnet | `--collect:"XPlat Code Coverage"` |
| mix | `mix test --cover` |
| rspec | (relies on simplecov in spec_helper) |
| Other | Skip coverage flag, note in report |

---

## Step 4: Classify Results

**Exit code interpretation:**

| Exit | Classification | Action |
|------|---------------|--------|
| 0 | All tests passed | Proceed to Step 5 (coverage check) |
| Non-zero + test failure markers | **Tier 1** — code failures | Step 6 (deep analysis) |
| Non-zero + env error signals | **Tier 2** — environment failures | Step 7 (quick fix) |
| Killed by timeout | **Tier 2** — process timeout | Step 7 |

**Tier 1 markers:** `FAIL`, `FAILED`, `AssertionError`, test count summaries
**Tier 2 markers:** `ModuleNotFoundError`, `command not found`, `Permission denied`, `ECONNREFUSED`, `OOM`

---

## Step 5: Check Coverage

Parse the coverage output from the test run. Extract:
- **Overall coverage %** (line coverage preferred, then branch, then statement)
- **Per-file breakdown** (if available)
- **Uncovered lines/files**

### Coverage Parsing Patterns

Each framework outputs coverage data differently. Parse by matching the detected framework:

| Framework | Pattern to Match | Example Output |
|-----------|-----------------|----------------|
| jest/vitest | Table with `% Stmts`, `% Branch`, `% Funcs`, `% Lines` columns | `All files \| 87.5 \| 82.1 \| 91.3 \| 89.2` |
| pytest-cov | `TOTAL` line with `N M P%` format | `TOTAL    120    15    87%` |
| go | `coverage: N% of statements` | `coverage: 78.5% of statements` |
| cargo tarpaulin | `N% coverage, X/Y lines covered` | `78.35% coverage, 120/153 lines covered` |
| dotnet (coverlet) | XML report — parse `line-rate` attribute | `<coverage line-rate="0.87">` |
| mix | `N% [M of P relevant lines]` | `100.0% [42 of 42 relevant lines]` |
| rspec (simplecov) | `Coverage report: N% covered` | `Coverage report generated: 156 / 180 LOC (86.67%) covered` |
| gradle (JaCoCo) | `Total: N%` in console or XML report | Parse `INSTRUCTION` counter in `jacocoTestReport.xml` |
| phpunit | `Lines: N% (X/Y)` | `Lines:   87.50% (105/120)` |

**For frameworks not listed above**: Scan stdout/stderr for patterns matching `N%` near words like `coverage`, `covered`, `lines`, `statements`. If multiple percentages found, prefer the one labeled "lines" or "total".

### No Coverage Data Available

If no coverage data can be parsed from the output:

| Cause | Action |
|-------|--------|
| Coverage flag was skipped (framework not in Step 3 table) | Report `DONE_WITH_CONCERNS`: "Coverage tool not available for {framework}. Cannot verify threshold." |
| Coverage tool not installed (e.g., `cargo-tarpaulin`, `simplecov` not in Gemfile) | Report `DONE_WITH_CONCERNS`: "Coverage tool `{tool}` not installed. Install it and re-run, or skip coverage check." |
| Coverage flag attached but no coverage in output | Try running dedicated coverage command. If still no data → report `DONE_WITH_CONCERNS` |
| Tests passed with coverage data | Proceed to decision table below |

### Coverage Decision

| Condition | Action |
|-----------|--------|
| Coverage ≥ threshold | ✅ Pass — proceed to Step 8 (report) |
| Coverage < threshold | Report DONE_WITH_CONCERNS — list uncovered areas, do NOT write additional tests |

---

## Step 6: Analyze Tier 1 Failures (Deep Analysis)

For code/test failures, apply deep analysis with a **maximum of 5 unique-file slots**:

- All failures from the same source file share one slot
- Failures beyond the 5-slot limit: list test name and raw message only

**For each slot (up to 5 unique files):**

1. **Extract**: file path, line number, test name(s), error message(s), stack trace
2. **Read**: the failing test file and the source file it tests (±10 lines around each error)
3. **Categorize**: assertion mismatch, wrong return value, unhandled exception, or type/schema error
4. **Suggest**: identify likely root cause with confidence level

**Confidence levels:**

| Level | Meaning |
|-------|---------|
| `[HIGH]` | Error points directly to a specific line in source |
| `[MEDIUM]` | Error implicates a file or function, not an exact line |
| `[LOW]` | Pattern match only — could be multiple causes |

### Auto-fix Decision

After analysis, decide whether to auto-fix or escalate:

| Condition | Action |
|-----------|--------|
| Failure is fixable (simple assertion, import, typo) AND `fix_attempts` < 3 | Fix code, increment `fix_attempts`, re-run from Step 3 |
| Failure is fixable BUT `fix_attempts` ≥ 3 | Stop auto-fixing. Report `DONE_WITH_CONCERNS`: "Auto-fix limit reached after 3 attempts. Remaining failures need manual review." |
| Failure requires user input (spec ambiguity, design conflict) | Report `NEEDS_CONTEXT` with the analysis — do not attempt to fix |

---

## Step 7: Report Tier 2 Failures (Fast Path)

For environment/tooling failures, provide a short actionable message only. No deep analysis.

| Type | Message |
|------|---------|
| Missing module/import | "Run `npm install` / `pip install -r requirements.txt`" |
| Command not found | "Tool not installed or not in PATH" |
| Permission denied | "Check file permissions" |
| Process timeout | "Increase timeout or check for hanging process" |
| Config parse error | "Check `testconfig.yml` syntax" |
| Out of memory | "Increase Node `--max-old-space-size` or system memory" |
| Port in use | "Kill the process using the port or use a different port" |
| Docker error | "Start Docker daemon or check container configuration" |
| Database error | "Check database connection and schema migration" |

After reporting, set status to `BLOCKED` — environment issues need user intervention.

---

## Step 8: Report Status

Compile the final report and return one of:

### DONE
All tests pass, coverage ≥ threshold.

```
Tests: {passed}/{total} passed  ({duration}s)
Coverage: {coverage}% (threshold: {threshold}%)
  Branches: {branch_cov}%
  Functions: {func_cov}%
  Lines: {line_cov}%

Ready to advance to REVIEW.
```

### DONE_WITH_CONCERNS
Tests pass but coverage < threshold.

```
Tests: {passed}/{total} passed  ({duration}s)
Coverage: {coverage}% (threshold: {threshold}%) ⚠️ BELOW THRESHOLD

Uncovered areas:
  - {file}:{lines} — {description}

Concerns:
  - Coverage is {coverage}% vs {threshold}% threshold
  - Recommend manual review of uncovered paths
```

### BLOCKED
Cannot proceed:
- Tier 2 environment failure → include env error and fix instructions
- No test framework detected → include detection failure details

### NEEDS_CONTEXT
Test failures that require user decisions:
- Spec ambiguity (test expects A, code does B, spec unclear)
- Design conflict (test reveals architecture issue)
- Include the failure analysis from Step 6

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No tests found in project | Report `BLOCKED`: "No test files found. Verify tests were written during CODE phase." |
| Tests pass on first run but fail on coverage re-run | Investigate flaky tests — report `DONE_WITH_CONCERNS` with flaky test list |
| Coverage tool not installed for framework | Report `DONE_WITH_CONCERNS` — do not install tools, note what's needed |
| Monorepo with multiple test suites | If `nx.json`, `turbo.json`, etc. found: run all test suites. Report aggregate coverage |
| Test file references missing source file | Skip that source read, downgrade confidence to `[LOW]` |
| All tests pass but 0% coverage reported | Likely misconfigured coverage — report `DONE_WITH_CONCERNS`, suggest checking config |
| Timeout kills a long-running test suite | Report `BLOCKED` with timeout value and suggestion to increase |

---

## Guardrails

- Always detect framework before running — never guess
- Always apply timeout (default 120s)
- Always append coverage flags when running the full suite
- Never read more than 5 unique source files for deep analysis
- **Never write or create test files** — only run existing tests
- If framework detection fails, report BLOCKED — do not proceed without a runner
- Environment issues (Tier 2) are always BLOCKED — never try to fix environment
- Report honestly — don't inflate coverage numbers or hide failures
- If no coverage data can be parsed, report DONE_WITH_CONCERNS — never claim coverage passed without data
- Never install coverage tools (cargo-tarpaulin, simplecov, etc.) — only report what's needed

