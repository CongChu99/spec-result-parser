---
name: c4flow:e2e
description: Run end-to-end browser tests against the deployed or locally-running application. Auto-detect e2e framework (Playwright, Cypress, Selenium, TestCafe, Robot Framework), manage app server lifecycle, execute tests, classify failures, and report results. Manual trigger — not part of auto-flow. Use when the user wants to run e2e tests, browser tests, integration tests against a live app, or validate user flows. Triggers on "e2e", "end-to-end", "browser test", "playwright", "cypress", or "smoke test".
---

# /c4flow:e2e — End-to-End Browser Tests

**Phase**: 4: Testing (manual trigger — not part of auto flow)
**Agent type**: Sub-agent (dispatched by orchestrator or invoked directly)
**Status**: Implemented

## Overview

Run the full end-to-end test suite against a running application. Detect the e2e framework, optionally start the app server, execute browser tests, classify failures (code bugs vs environment issues), and report results. Does NOT write test files.

**Relationship to `c4flow:test`**: `c4flow:test` handles unit + integration tests with coverage checking. `c4flow:e2e` handles browser-level user flow validation against a live app. They are complementary — run `c4flow:test` first, then `c4flow:e2e`.

## Input
- Feature name (kebab-cased) from `.state.json`
- `docs/specs/<feature>/tech-stack.md` — framework & e2e stack info
- `docs/specs/<feature>/spec.md` — expected behaviors (GIVEN/WHEN/THEN scenarios for validation)
- App URL (from config, env var, or auto-detected dev server)

## Output
- Test results: pass/fail count, duration, screenshots/videos (if available)
- Failure analysis: root cause suggestions with confidence levels
- Gate decision: pass (report success) or fail (report issues)

## Gate Condition
```
E2E pass: All critical-path tests pass
E2E warn: Non-critical tests fail (report DONE_WITH_CONCERNS)
```

> **Note**: Since e2e is a manual trigger, there is no auto-advance to a next state. Results are reported to the user.

## Capabilities

| Capability | Details |
|---|---|
| Framework detection | 5 frameworks: Playwright, Cypress, Selenium/WebDriverIO, TestCafe, Robot Framework |
| App server management | Auto-detect dev server command, start before tests, shutdown after |
| Browser management | Headless by default, configurable via env vars |
| Failure classification | Tier 1 (test/code bugs: deep analysis) / Tier 2 (env issues: quick fix) |
| Deep analysis | Up to 5 unique-file slots, ±10 lines context, HIGH/MEDIUM/LOW confidence |
| Artifact collection | Screenshots, videos, trace files (if framework supports) |

---

## Instructions

You are the `c4flow:e2e` agent. Execute the following steps in order.

---

### Step 1: Parse Input & Resolve Configuration

**Read from orchestrator context:**
- Feature name from `.state.json`
- `docs/specs/<feature>/tech-stack.md` — extract:
  - E2E testing framework (if specified)
  - App start command
  - Base URL
- `docs/specs/<feature>/spec.md` — keep available for flow validation

**Initialize internal counters:**

| Counter | Initial | Max | Purpose |
|---------|---------|-----|---------|
| `fix_attempts` | 0 | 3 | Tier 1 auto-fix attempts (Step 6) |
| `server_start_retries` | 0 | 3 | App server start attempts |

**Resolve e2e configuration — priority order:**

| Priority | Source |
|----------|--------|
| 1 | E2E config file (`playwright.config.*`, `cypress.config.*`, `wdio.conf.*`, `.testcaferc.*`) |
| 2 | `tech-stack.md` e2e section |
| 3 | Auto-detection (Step 2) |

**Resolve app URL — priority order:**

| Priority | Source |
|----------|--------|
| 1 | `E2E_BASE_URL` or `BASE_URL` env var |
| 2 | `baseURL` / `baseUrl` in e2e config file |
| 3 | `tech-stack.md` app URL |
| 4 | Default: `http://localhost:3000` |

---

### Step 2: Detect E2E Framework

If no explicit command is configured, auto-detect by scanning project files. **First match wins:**

| Priority | Signal | Framework | Command |
|----------|--------|-----------|---------|
| 1 | `playwright.config.ts` / `playwright.config.js` / `@playwright/test` in deps | Playwright | `npx playwright test` |
| 2 | `cypress.config.ts` / `cypress.config.js` / `cypress/` dir / `cypress` in deps | Cypress | `npx cypress run` |
| 3 | `wdio.conf.ts` / `wdio.conf.js` / `@wdio/cli` in deps | WebDriverIO | `npx wdio run wdio.conf.ts` |
| 4 | `.testcaferc.json` / `.testcaferc.cjs` / `testcafe` in deps | TestCafe | `npx testcafe chromium:headless` |
| 5 | `*.robot` files in test dirs / `robotframework` in Python deps | Robot Framework | `robot --outputdir results tests/` |
| 6 | `selenium-webdriver` in deps + custom config | Selenium (custom) | Check `package.json` scripts for `e2e` or `test:e2e` |

**Package manager detection:** `bun.lockb`/`bun.lock` → bun, `yarn.lock` → yarn, `pnpm-lock.yaml` → pnpm, otherwise npm.

**If no framework detected:** Report `BLOCKED` with message "No e2e test framework detected. Install Playwright (`npm init playwright@latest`) or Cypress (`npm install cypress`) and add tests."

---

### Step 3: Start App Server (If Needed)

**Check if app is already running:**

```bash
APP_URL="${E2E_BASE_URL:-http://localhost:3000}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$APP_URL" 2>/dev/null || echo "000")
```

**If app is already running (HTTP status 200/301/302):** Skip server start, proceed to Step 4.

**If app is NOT running:** Detect and start dev server.

**Dev server detection — priority order:**

| Priority | Signal | Command |
|----------|--------|---------|
| 1 | `E2E_START_CMD` env var | Use as-is |
| 2 | `package.json` has `scripts.dev` | `npm run dev` |
| 3 | `package.json` has `scripts.start` | `npm start` |
| 4 | `manage.py` exists | `python manage.py runserver` |
| 5 | `main.go` exists | `go run .` |

**Start server in background:**

```bash
# Start dev server in background
$START_CMD &
SERVER_PID=$!

# Wait for server to be ready (max 30 seconds)
for i in $(seq 1 30); do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$APP_URL" 2>/dev/null || echo "000")
  if [ "$HTTP_STATUS" != "000" ]; then
    echo "App server ready at $APP_URL (HTTP $HTTP_STATUS)"
    break
  fi
  sleep 1
done

if [ "$HTTP_STATUS" = "000" ]; then
  echo "ERROR: App server failed to start within 30 seconds"
  kill $SERVER_PID 2>/dev/null
  # Report BLOCKED
fi
```

**Record `SERVER_PID`** — needed for cleanup in Step 8.

**Playwright-specific:** If framework is Playwright and config has `webServer`, skip manual server start — Playwright manages it natively.

---

### Step 4: Run E2E Test Suite

Execute the resolved e2e command, capturing stdout and stderr.

**Apply timeout:** Default 300 seconds for e2e tests (longer than unit tests). Override via `E2E_TIMEOUT` env var.

**Headless mode flags** — append framework-specific headless flag:

| Framework | Headless Flag | Default |
|-----------|--------------|---------|
| Playwright | (headless by default in CI) | No flag needed |
| Cypress | `--headless` | Appended automatically |
| WebDriverIO | Set in `wdio.conf` capabilities | No flag needed |
| TestCafe | `chromium:headless` | Already in command |
| Robot Framework | `--variable BROWSER:headlesschrome` | Append if no display |

**Check for headless environment:**

```bash
# Detect if running headless (no display)
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  HEADLESS=true
fi
```

**Framework-specific execution:**

| Framework | Full Command |
|-----------|-------------|
| Playwright | `npx playwright test --reporter=list` |
| Cypress | `npx cypress run --reporter spec` |
| WebDriverIO | `npx wdio run wdio.conf.ts` |
| TestCafe | `npx testcafe chromium:headless tests/` |
| Robot Framework | `robot --outputdir results --loglevel INFO tests/` |

---

### Step 5: Classify Results

**Exit code interpretation:**

| Exit | Classification | Action |
|------|---------------|--------|
| 0 | All tests passed | Proceed to Step 8 (report) |
| Non-zero + test failure markers | **Tier 1** — test/code failures | Step 6 (deep analysis) |
| Non-zero + env error signals | **Tier 2** — environment failures | Step 7 (quick fix) |
| Killed by timeout | **Tier 2** — process timeout | Step 7 |

**Tier 1 markers:** `FAIL`, `FAILED`, `AssertionError`, `Expected`, `Received`, `Timed out waiting for`, `element not found`, `element not visible`, `click intercepted`, test count summaries

**Tier 2 markers:** `browserType.launch`, `Browser closed`, `ERR_CONNECTION_REFUSED`, `ECONNREFUSED`, `net::ERR_`, `No such file`, `command not found`, `Permission denied`, `OOM`, `Protocol error`, `Target closed`, `Session not created`

---

### Step 6: Analyze Tier 1 Failures (Deep Analysis)

For test/code failures, apply deep analysis with a **maximum of 5 unique-file slots**:

- All failures from the same test file share one slot
- Failures beyond the 5-slot limit: list test name and raw message only

**For each slot (up to 5 unique files):**

1. **Extract**: test file path, line number, test name(s), error message(s), stack trace, screenshot path (if available)
2. **Read**: the failing test file and relevant page object / component file (±10 lines around each error)
3. **Categorize failure type:**

| Category | Signal | Common Cause |
|----------|--------|-------------|
| Element not found | `locator.click`, `getByRole`, `cy.get` timeout | Selector changed, element not rendered, timing issue |
| Assertion mismatch | `expect(...).toBe(...)`, `should('have.text')` | UI text changed, data mismatch, race condition |
| Navigation failure | `page.goto`, `cy.visit` error | Route changed, redirect loop, 404 |
| Interaction blocked | `click intercepted`, `element not interactable` | Modal overlay, element not scrolled into view |
| Timeout | `Timed out waiting for` | Slow API, loading spinner stuck, network issue |
| Visual regression | Screenshot diff | UI layout changed |

4. **Suggest**: identify likely root cause with confidence level

**Confidence levels:**

| Level | Meaning |
|-------|---------|
| `[HIGH]` | Error points directly to a specific selector or assertion |
| `[MEDIUM]` | Error implicates a page or flow, not an exact element |
| `[LOW]` | Pattern match only — could be timing, data, or code |

### Auto-fix Decision

After analysis, decide whether to auto-fix or escalate:

| Condition | Action |
|-----------|--------|
| Failure is fixable (selector update, wait added, text change) AND `fix_attempts` < 3 | Fix test code, increment `fix_attempts`, re-run from Step 4 |
| Failure is fixable BUT `fix_attempts` ≥ 3 | Stop auto-fixing. Report `DONE_WITH_CONCERNS` |
| Failure requires user input (flow changed, new feature, spec unclear) | Report `NEEDS_CONTEXT` with the analysis |

---

### Step 7: Report Tier 2 Failures (Fast Path)

For environment/tooling failures, provide a short actionable message only. No deep analysis.

| Type | Message |
|------|---------|
| Browser not found | "Install browser: `npx playwright install` or `npx cypress install`" |
| App server not running | "Start the app server first, or set `E2E_BASE_URL` env var" |
| Connection refused | "App not responding at `{url}`. Check if the server started correctly" |
| Display/GPU error | "Running headless? Set `--headless` flag or use `xvfb-run`" |
| Process timeout | "Tests exceeded {timeout}s. Increase `E2E_TIMEOUT` or check for hanging tests" |
| Browser crashed | "Browser ran out of memory or crashed. Try reducing parallel workers" |
| SSL/certificate error | "Accept self-signed certs: set `NODE_TLS_REJECT_UNAUTHORIZED=0` for dev" |
| Docker/container error | "Check Docker is running and browser containers are healthy" |

After reporting, set status to `BLOCKED` — environment issues need user intervention.

---

### Step 8: Report Status & Cleanup

**Cleanup first:**

```bash
# Stop dev server if we started it
if [ -n "${SERVER_PID:-}" ]; then
  kill $SERVER_PID 2>/dev/null
  wait $SERVER_PID 2>/dev/null
  echo "Dev server stopped (PID: $SERVER_PID)"
fi
```

**Collect artifacts** (if available):

| Framework | Artifacts Location |
|-----------|-------------------|
| Playwright | `test-results/`, `playwright-report/` |
| Cypress | `cypress/screenshots/`, `cypress/videos/` |
| WebDriverIO | `allure-results/`, custom output dir |
| TestCafe | `reports/`, screenshots in test output |
| Robot Framework | `results/output.xml`, `results/log.html`, `results/report.html` |

**Report one of:**

### DONE
All e2e tests pass.

```
E2E Tests: {passed}/{total} passed  ({duration}s)
Framework: {framework}
Base URL:  {app_url}

Artifacts:
  Screenshots: {screenshot_count} captured
  Videos: {video_count} recorded

All critical user flows validated.
```

### DONE_WITH_CONCERNS
Tests mostly pass but some non-critical failures.

```
E2E Tests: {passed}/{total} passed, {failed} failed  ({duration}s)
Framework: {framework}
Base URL:  {app_url}

Failures (non-blocking):
  - {test_name}: {error_summary}

Concerns:
  - {concern_description}

Screenshots of failures available at: {artifact_path}
```

### BLOCKED
Cannot proceed:
- Tier 2 environment failure → include env error and fix instructions
- No e2e framework detected → include detection failure details
- App server failed to start → include server error output

### NEEDS_CONTEXT
Test failures that require user decisions:
- Flow changed (test expects old behavior, app shows new)
- Spec ambiguity (test expects A, app does B, spec unclear)
- Include the failure analysis from Step 6

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `E2E_BASE_URL` or `BASE_URL` | `http://localhost:3000` | App URL to test against |
| `E2E_START_CMD` | Auto-detected | Command to start the app server |
| `E2E_TIMEOUT` | `300` | Timeout in seconds for the full e2e suite |
| `E2E_HEADLESS` | `true` (if no display) | Force headless browser mode |
| `E2E_WORKERS` | Framework default | Number of parallel browser workers |
| `E2E_RETRIES` | `0` | Number of retries for failed tests |

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No e2e tests found in project | Report `BLOCKED`: "No e2e test files found. Write tests first or check test directory configuration." |
| App server starts but returns 500 | Proceed with tests — the 500 may be limited to certain routes. Tests will surface the issues. |
| Flaky tests (pass on retry) | If `E2E_RETRIES` > 0, use framework retry. Report flaky tests in `DONE_WITH_CONCERNS` even if they pass on retry. |
| Multiple e2e frameworks detected | Use the first match from detection priority. Note others in output. |
| Tests require auth/login | Tests should handle auth themselves (test fixtures, env vars, setup hooks). If auth fails, classify as Tier 1. |
| Tests need seeded data | Tests should handle data seeding. If data missing, classify as Tier 2 (environment setup needed). |
| Playwright `webServer` in config | Skip Step 3 entirely — Playwright manages the server lifecycle. |
| Tests pass locally but fail in CI | Common causes: timing, viewport, font rendering. Report `DONE_WITH_CONCERNS` with environment diff. |
| Browser install needed | Report `BLOCKED`: "Run `npx playwright install` to download browsers." |

---

## Guardrails

- Always detect framework before running — never guess
- Always apply timeout (default 300s — e2e tests are slow)
- Always run in headless mode unless display is available
- Never read more than 5 unique test files for deep analysis
- **Never write or create test files** — only run existing tests
- If framework detection fails, report `BLOCKED` — do not proceed without a runner
- Environment issues (Tier 2) are always `BLOCKED` — never try to fix environment
- **Always clean up** — stop the dev server if you started it, even on failure
- Report honestly — don't hide failures or claim tests passed without evidence
- Never install browsers or dependencies — only report what's needed
- Never run tests against production URLs unless explicitly configured
