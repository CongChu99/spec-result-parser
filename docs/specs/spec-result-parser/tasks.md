# Tasks: spec-result-parser

> Spec: docs/specs/spec-result-parser/spec.md
> Design: docs/specs/spec-result-parser/design.md
> Generated: 2026-04-02T17:50:00+07:00
> Granularity: Standard (~14 tasks, 1-2 days each)
> Parallelism Score: 4/5 ✅

---

## Layer 0 (start immediately — no dependencies)

### T-01: Project scaffolding & pyproject.toml [P1] [infra,small]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** none
- **Acceptance criteria:**
  - [ ] `pyproject.toml` with `[project]`, `[project.scripts]`, `[build-system]` sections
  - [ ] `spec-parser` CLI entry point registered
  - [ ] `src/spec_result_parser/` package structure with `__init__.py` files
  - [ ] `uv` or `pip install -e .` installs the package cleanly
  - [ ] Python 3.9+ constraint declared
  - [ ] MIT license file present
- **Description:** Create the Python package skeleton. Establishes the installable package `spec-result-parser` with the `spec-parser` CLI entry point. No logic yet — just structure.
- **Input:** tech-stack.md, design.md#architecture-overview
- **Deliverables:**
  - `pyproject.toml` (click, rich, PyYAML, pandas deps)
  - `src/spec_result_parser/__init__.py`
  - `src/spec_result_parser/cli.py` (stub — `click` group with `check` + `aggregate` subcommands, each prints "TODO")
  - `LICENSE` (MIT)
  - `README.md` (stub)
  - `.gitignore`
  - `tests/__init__.py`
- **Files:** `pyproject.toml`, `src/spec_result_parser/cli.py`, `LICENSE`, `README.md`
- **Design notes:** Use `hatchling` as build backend. Register `spec-parser = "spec_result_parser.cli:main"` as script entry point via click group.
- **Spec ref:** spec.md → help and usage documentation requirement
- **Notes:** Install with `pip install -e ".[dev]"` locally. Dev extras: pytest, pytest-cov.

---

### T-02: Core data models (dataclasses) [P1] [backend,small]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** none
- **Acceptance criteria:**
  - [ ] `Measurement`, `SpecTarget`, `SpecCheck`, `Corner`, `Status`, `Format` dataclasses/enums defined
  - [ ] All fields match design.md#data-model exactly
  - [ ] 100% type-annotated
  - [ ] Unit tests for dataclass construction pass
- **Description:** Define all core data structures. All other components depend on these types. No I/O, no external deps — pure Python stdlib only.
- **Input:** design.md#data-model
- **Deliverables:**
  - `src/spec_result_parser/models.py` — all dataclasses + enums
  - `tests/test_models.py` — construction + repr tests
- **Files:** `src/spec_result_parser/models.py`, `tests/test_models.py`
- **Design notes:** `Status` enum: PASS, FAIL, MARGIN, NA. `Format` enum: PSF_ASCII, HSPICE_MT0. Use `@dataclass(frozen=True)` for `Measurement` and `SpecTarget` — they should be immutable value objects.
- **Spec ref:** spec.md → all requirements (shared types)
- **Notes:** This is the contract between all other components. Done when design.md data model is faithfully implemented.

---

### T-03: Spectre PSF-ASCII parser [P1] [backend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** none
- **Acceptance criteria:**
  - [ ] Parses valid PSF-ASCII files and returns correct `list[Measurement]`
  - [ ] Raises `ParseError` on invalid/non-PSF content
  - [ ] Correctly extracts name, float value, unit from VALUE section
  - [ ] Skips SWEEP sections (waveform data)
  - [ ] Handles scientific notation (e.g., `12.5e6`)
  - [ ] Tests cover ≥3 reference fixture files covering different Spectre output versions
  - [ ] No external dependencies (stdlib only)
- **Description:** Custom pure-Python parser for Spectre PSF-ASCII format. Scans the VALUE section and extracts name→value→unit triplets. This is the primary format for VN Cadence-based flows.
- **Input:** PSF-ASCII format documentation, reference fixture files
- **Deliverables:**
  - `src/spec_result_parser/parsers/psf_ascii.py`
  - `tests/fixtures/psf/` — ≥3 reference PSF-ASCII files (to be created/generated)
  - `tests/test_psf_parser.py`
- **Files:** `src/spec_result_parser/parsers/psf_ascii.py`, `tests/fixtures/psf/*.psf`, `tests/test_psf_parser.py`
- **Design notes:** PSF-ASCII VALUE section lines look like: `"gain_dc" 68.5 dB`. Use regex `r'"(\w+)"\s+([-+eE\d.]+)\s*(\w+)?'`. Skip lines in SWEEP or TYPE sections.
- **Spec ref:** spec.md → PSF-ASCII Parsing requirement
- **Notes:** Generate fixture files from open-source ngspice opamp simulation or hand-craft representative samples. Do NOT read psf-utils source to avoid GPL contamination.

---

### T-04: HSPICE MT0 parser [P1] [backend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** none
- **Acceptance criteria:**
  - [ ] Parses valid HSPICE `.mt0` / printfile and returns correct `list[Measurement]`
  - [ ] Raises `ParseError` on invalid content
  - [ ] Correctly extracts `.MEASURE` name=value pairs
  - [ ] Handles scientific notation, signed values
  - [ ] Skips header lines (`$`, `*`, `.option`)
  - [ ] Tests cover ≥3 reference MT0 fixture files
  - [ ] No external dependencies
- **Description:** Custom pure-Python parser for HSPICE MT0 / printfile. Extracts measurement name=value lines from `.MEASURE` output. Second most common format in VN IC flows (Synopsys ecosystem).
- **Input:** HSPICE MT0 format examples, reference fixture files
- **Deliverables:**
  - `src/spec_result_parser/parsers/hspice_mt0.py`
  - `tests/fixtures/mt0/` — ≥3 reference MT0 files
  - `tests/test_hspice_parser.py`
- **Files:** `src/spec_result_parser/parsers/hspice_mt0.py`, `tests/fixtures/mt0/*.mt0`, `tests/test_hspice_parser.py`
- **Design notes:** MT0 lines format: `gain_dc=6.85000e+01`. Regex: `r'^(\w+)\s*=\s*([-+eE\d.]+)'`. Some versions use column-separated header + data rows — handle both styles.
- **Spec ref:** spec.md → HSPICE MT0 Parsing requirement
- **Notes:** Hand-craft representative MT0 fixture files from HSPICE documentation examples. Two layout styles exist (v2020 vs v2023 HSPICE) — test both.

---

### T-05: Spec config loader (YAML + CSV) [P1] [backend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** none
- **Acceptance criteria:**
  - [ ] Loads YAML spec file and returns `list[SpecTarget]` correctly
  - [ ] Loads CSV spec file (columns: measurement, min, max, unit) and returns `list[SpecTarget]`
  - [ ] Auto-detects format from file extension (`.yaml`/`.yml` vs `.csv`)
  - [ ] Handles `null`/blank min or max (one-sided spec)
  - [ ] Raises `ConfigError` on missing file, bad YAML, missing CSV columns
  - [ ] Unit tests for valid/invalid YAML and CSV
- **Description:** Load spec targets from YAML or CSV files. YAML is the Git-friendly primary format; CSV is the Excel-export-friendly secondary format. Auto-detects from extension.
- **Input:** design.md#spec-loader, sample YAML/CSV spec files
- **Deliverables:**
  - `src/spec_result_parser/spec_loader.py`
  - `tests/fixtures/specs/opamp.spec.yaml` (reference spec)
  - `tests/fixtures/specs/opamp.spec.csv` (same spec as CSV)
  - `tests/test_spec_loader.py`
- **Files:** `src/spec_result_parser/spec_loader.py`, `tests/fixtures/specs/*`, `tests/test_spec_loader.py`
- **Design notes:** YAML structure: `specs: { measurement_name: { min: float|null, max: float|null, unit: str } }`. CSV columns: `measurement,min,max,unit`. Use `PyYAML.safe_load()`, never `yaml.load()`.
- **Spec ref:** spec.md → YAML Spec Config + CSV Spec Config requirements
- **Notes:** The reference YAML/CSV fixtures should reflect a real two-stage Miller opamp: gain_dc (min 60 dB), ugbw (min 10 MHz), phase_margin (min 45 deg), offset_voltage (max 5 mV).

---

## Layer 1 (after Layer 0 — needs T-02 data models)

### T-06: FormatDetector [P1] [backend,small]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-02 (needs Format enum from models)
- **Acceptance criteria:**
  - [ ] Returns `Format.PSF_ASCII` for `.psf` extension
  - [ ] Returns `Format.HSPICE_MT0` for `.mt0` extension
  - [ ] Returns `None` for unsupported extensions (`.tr0`, `.bin`, etc.)
  - [ ] Optional header-sniff validation (peek first 4 lines)
  - [ ] Unit tests for all extension cases
- **Description:** Auto-detect simulator file format from file extension. Optionally validates by peeking at file header. Used by both `check` and `aggregate` subcommands before dispatching to the correct parser.
- **Input:** design.md#format-detector, T-02 Format enum
- **Deliverables:**
  - `src/spec_result_parser/format_detector.py`
  - `tests/test_format_detector.py`
- **Files:** `src/spec_result_parser/format_detector.py`
- **Design notes:** `detect(filepath: Path) -> Format | None`. Pure function — no side effects. Extension check first (fast), header sniff second (optional validation).
- **Spec ref:** spec.md → auto-detect format scenario
- **Notes:** Keep simple — extension-based detection covers 95% of cases. Header sniff is a nice-to-have for robustness.

---

### T-07: SpecChecker — PASS/FAIL/MARGIN logic [P1] [backend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-02 (needs Measurement, SpecTarget, SpecCheck, Status models)
- **Acceptance criteria:**
  - [ ] Returns PASS when value is within bounds and margin > threshold
  - [ ] Returns FAIL when value < min or value > max
  - [ ] Returns MARGIN when 0 < margin_pct < threshold (default 10%)
  - [ ] Returns NA when measurement name not found in results
  - [ ] Correct margin_pct calculation for both min-bound and max-bound specs
  - [ ] Unit tests cover all 4 status paths + edge cases (value exactly at bound)
- **Description:** Pure-function spec checker. Compares measurement values against spec targets and computes PASS/FAIL/MARGIN/NA status with margin percentage. Zero external dependencies.
- **Input:** design.md#spec-checker, T-02 models
- **Deliverables:**
  - `src/spec_result_parser/spec_checker.py`
  - `tests/test_spec_checker.py`
- **Files:** `src/spec_result_parser/spec_checker.py`
- **Design notes:** `margin_pct = (value - min) / abs(min)` for min-bound. `margin_pct = (max - value) / abs(max)` for max-bound. For two-sided spec, use the tighter margin. Default `margin_threshold=0.10` (10%).
- **Spec ref:** spec.md → Single-File Spec Check (margin warning scenario)
- **Notes:** Handle edge case: if `min == 0` or `max == 0`, avoid division by zero (use absolute distance instead, or skip margin calculation → report PASS directly).

---

### T-08: CornerAggregator — multi-file folder parsing [P1] [backend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-03 (PSF parser), T-04 (HSPICE parser), T-05 (SpecLoader), T-06 (FormatDetector), T-07 (SpecChecker)
- **Acceptance criteria:**
  - [ ] Scans folder and processes all `.psf` + `.mt0` files
  - [ ] Maps files to corners via `corners.yaml` if provided, else uses filename as corner name
  - [ ] Builds pandas DataFrame: rows=corners, columns=spec_names, values=SpecCheck
  - [ ] Computes and appends Worst Case row (min value per column)
  - [ ] Prints WARN and skips corrupted/unsupported files (non-fatal)
  - [ ] Raises `ConfigError` if folder is empty or no supported files found
  - [ ] Tests with ≥5 fixture files (mix of PSF + MT0)
- **Description:** Aggregation engine: iterate folder, detect format, parse, check specs, aggregate into corner×spec matrix. Uses pandas DataFrame for pivot and worst-case calculation.
- **Input:** T-03, T-04, T-05, T-06, T-07 components
- **Deliverables:**
  - `src/spec_result_parser/corner_aggregator.py`
  - `tests/fixtures/corners/` — 5 fixture files (3 PSF, 2 MT0) + `corners.yaml`
  - `tests/test_corner_aggregator.py`
- **Files:** `src/spec_result_parser/corner_aggregator.py`, `tests/fixtures/corners/*`
- **Design notes:** `CornerMatrix = pd.DataFrame`. Use `df.applymap()` to extract worst value per column. Corner mapping YAML: `{ corner_name: { file: "...", process: TT|FF|SS, voltage: float, temp: float } }`.
- **Spec ref:** spec.md → Multi-Corner Aggregation requirement
- **Notes:** Worst-case = min value across corners for min-bound specs. Pandas `df.min()` handles this cleanly.

---

## Layer 2 (after Layer 1 — wire core components into CLI)

### T-09: TerminalRenderer — rich color tables [P1] [frontend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-07 (SpecCheck results), T-08 (CornerMatrix)
- **Acceptance criteria:**
  - [ ] `render_check(checks)` prints color-coded table: FAIL=red, MARGIN=yellow, PASS=green
  - [ ] `render_matrix(matrix)` prints corner×spec matrix with worst-case row highlighted amber
  - [ ] FAIL rows have full row red background tint
  - [ ] Status badges match design (PASS/FAIL/MARGIN/N/A)
  - [ ] Summary line after table: `✓ All N specs: PASS` or `✗ X of N specs FAILED`
  - [ ] Visual output verified against FIG.01–FIG.03 design mockups
  - [ ] `--verbose` flag shows raw [DEBUG] parser output (blue)
- **Description:** Rich terminal renderer. Produces the color-coded output the engineer sees in their terminal. All color design tokens from MASTER.md map to `rich` Style objects.
- **Input:** T-07/T-08 data, design mockups FIG.01–FIG.03, MASTER.md color tokens
- **Deliverables:**
  - `src/spec_result_parser/renderer.py`
  - `tests/test_renderer.py` (capture rich output, assert structure — not exact color since terminal varies)
- **Files:** `src/spec_result_parser/renderer.py`
- **Design notes:** Color mapping: `--accent-green=#3FB950` → `rich.style.Style(color="#3FB950")`. FAIL row background: `rich.style.Style(bgcolor="#4D1C1C")`. Use `rich.table.Table` with `box=rich.box.SIMPLE_HEAD`. Worst Case row: amber `#1A1000` background.
- **Spec ref:** spec.md → Single-File Spec Check (color output scenarios), FIG.01–FIG.03 mockups
- **Notes:** Test with `rich.console.Console(record=True)` to capture output for assertions without needing a real terminal.

---

### T-10: `check` subcommand (end-to-end) [P1] [backend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-01 (CLI scaffold), T-03 (PSF parser), T-04 (HSPICE parser), T-05 (SpecLoader), T-06 (FormatDetector), T-07 (SpecChecker), T-09 (TerminalRenderer)
- **Acceptance criteria:**
  - [ ] `spec-parser check <file> --spec <spec>` runs end-to-end in <2 seconds
  - [ ] Exit code 0 on all PASS, 1 on any FAIL, 2 on config/parse error
  - [ ] `--margin-threshold` option works (default 0.10)
  - [ ] `--verbose` option prints [DEBUG] lines
  - [ ] WARN printed for specs not found in result file (non-fatal)
  - [ ] Integration test: fixture PSF + YAML → assert correct table + exit code
- **Description:** Wire FormatDetector → Parser → SpecLoader → SpecChecker → TerminalRenderer into the `check` click subcommand. Handle all error paths per design.md#error-handling.
- **Input:** T-01 CLI stub, all core components, design.md#api-design
- **Deliverables:**
  - `src/spec_result_parser/cli.py` (populated `check` subcommand)
  - `tests/test_check_cmd.py` (integration tests)
- **Files:** `src/spec_result_parser/cli.py`
- **Design notes:** Use `click.option` for `--spec`, `--margin-threshold`, `--verbose`. Call `sys.exit(exit_code)` at end. Catch `ParseError` → exit 2. Catch `ConfigError` → exit 2.
- **Spec ref:** spec.md → Single-File Spec Check requirement, exit codes
- **Notes:** Run the check command on the opamp fixture as a smoke test in CI.

---

### T-11: `aggregate` subcommand (end-to-end) [P1] [backend,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-01, T-08 (CornerAggregator), T-09 (TerminalRenderer)
- **Acceptance criteria:**
  - [ ] `spec-parser aggregate <folder> --spec <spec>` runs on 25-file folder in <5 seconds
  - [ ] `--corners <corners.yaml>` option works; falls back to filename if omitted
  - [ ] Exit codes correct (0/1/2)
  - [ ] WARN for skipped files (corrupted/unsupported)
  - [ ] Integration test: fixture folder of 5 files → assert corner matrix + worst case row
- **Description:** Wire CornerAggregator → TerminalRenderer into the `aggregate` click subcommand. The hero command that replaces the Excel workflow.
- **Input:** T-01, T-08, T-09
- **Deliverables:**
  - `src/spec_result_parser/cli.py` (populated `aggregate` subcommand)
  - `tests/test_aggregate_cmd.py`
- **Files:** `src/spec_result_parser/cli.py`
- **Design notes:** `--corners` is optional. If omitted, infer corner name from filename stem (e.g., `tt_27.psf` → corner `tt_27`). Use `pathlib.Path.glob("*.psf")` + `glob("*.mt0")` to scan folder.
- **Spec ref:** spec.md → Multi-Corner Aggregation requirement
- **Notes:** Validate timing with 25-file test (generate synthetic fixture set in test_aggregate_cmd.py).

---

## Layer 3 (polish, packaging, documentation)

### T-12: Error handling & edge cases [P1] [backend,small]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-10 (check cmd), T-11 (aggregate cmd)
- **Acceptance criteria:**
  - [ ] All error conditions in design.md#error-handling table trigger correct exit code + message
  - [ ] Empty folder → ConfigError (exit 2)
  - [ ] Corrupted file in aggregate → WARN + skip (non-fatal)
  - [ ] Missing spec → ConfigError (exit 2)
  - [ ] YAML syntax error → ConfigError with yaml detail (exit 2)
  - [ ] Error messages match design.md#error-handling text exactly
  - [ ] Tests for every row in the error table
- **Description:** Systematic testing and fixing of all error paths. Ensure every error condition in design.md produces the correct exit code, message, and behavior (fatal vs. non-fatal).
- **Input:** design.md#error-handling table
- **Deliverables:**
  - `tests/test_error_handling.py`
  - Fixes to `cli.py`, `parsers/`, `spec_loader.py` as needed
- **Files:** `tests/test_error_handling.py`
- **Spec ref:** spec.md → exit codes requirement, all error scenarios
- **Notes:** Use `click.testing.CliRunner` to invoke CLI in tests and assert exit code + output.

---

### T-13: CI + pytest coverage gate [P2] [infra,small]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-12 (all tests written)
- **Acceptance criteria:**
  - [ ] `.github/workflows/ci.yml` runs `pytest` on push/PR for Python 3.9, 3.11, 3.12
  - [ ] Coverage gate ≥80% enforced via `pytest-cov --cov-fail-under=80`
  - [ ] CI passes on Linux; macOS optional
  - [ ] No hardcoded paths in tests
- **Description:** GitHub Actions CI pipeline. Runs full test suite on all supported Python versions. Coverage gate ensures parsers stay well-tested as the codebase grows.
- **Input:** T-12 (all tests done)
- **Deliverables:**
  - `.github/workflows/ci.yml`
- **Files:** `.github/workflows/ci.yml`
- **Design notes:** Use `actions/checkout@v4`, `actions/setup-python@v5`. Matrix: `[3.9, 3.11, 3.12]`.
- **Spec ref:** proposal.md → success criteria (pip-installable, pytest test suite)
- **Notes:** Keep CI fast — all tests should complete in <30 seconds.

---

### T-14: README + PyPI release [P2] [infra,medium]
- **Status:** open
- **Assignee:** solo
- **Claimed by:** —
- **Depends on:** T-13 (CI passes), T-10, T-11 (CLI complete)
- **Acceptance criteria:**
  - [ ] README has: quickstart, install instructions, YAML spec example, `check` example, `aggregate` example, opamp reference output (copy of FIG.01)
  - [ ] `pip install spec-result-parser` works from PyPI
  - [ ] Version tagged and released via GitHub tag → `pypi-publish` action
  - [ ] CHANGELOG.md with v0.1.0 entry
- **Description:** Documentation and PyPI publishing. The README is the first thing an IC engineer sees — it must show real opamp output and get them from `pip install` to first `spec-parser check` in <5 minutes.
- **Input:** T-10, T-11 (working CLI), FIG.01 mockup PNG
- **Deliverables:**
  - `README.md` (complete)
  - `CHANGELOG.md`
  - `.github/workflows/publish.yml` (trigger on tag)
  - v0.1.0 GitHub release
- **Files:** `README.md`, `CHANGELOG.md`, `.github/workflows/publish.yml`
- **Design notes:** README quickstart: `pip install spec-result-parser` → create `opamp.spec.yaml` → run `spec-parser check result.psf --spec opamp.spec.yaml` → show FIG.01 terminal output.
- **Spec ref:** proposal.md → success criteria (PyPI, quickstart)
- **Notes:** Use `hatch build` + `twine upload` or the `pypa/gh-action-pypi-publish@v1` action.

---

## Dependency Graph Summary

```
Layer 0 (parallel — start now):
  T-01 Project scaffold   ──────────────────────────────────────────────────┐
  T-02 Data models ────────────────────────┐                                │
  T-03 PSF-ASCII parser ─────────┐         │                                │
  T-04 HSPICE MT0 parser ────────┤         │                                │
  T-05 Spec loader ──────────────┘         │                                │
                                           │                                │
Layer 1 (needs T-02 data models):          │                                │
  T-06 FormatDetector ← T-02 ─────────────┤                                │
  T-07 SpecChecker    ← T-02 ─────────────┘                                │
  T-08 CornerAggregator ← T-03,T-04,T-05,T-06,T-07 ─────────────┐         │
                                                                   │         │
Layer 2 (wire into CLI):                                           │         │
  T-09 TerminalRenderer ← T-07, T-08 ──────────────────┐          │         │
  T-10 `check` cmd ← T-01,T-03..T-07,T-09 ─────────┐  │          │         │
  T-11 `aggregate` cmd ← T-01,T-08,T-09 ────────────┤  │          │         │
                                                      │  │          │         │
Layer 3 (polish):                                     │  │          │         │
  T-12 Error handling  ← T-10, T-11 ─────────────────┤  │          │         │
  T-13 CI pipeline     ← T-12 ────────────────────────┘  │          │         │
  T-14 README + PyPI   ← T-13, T-10, T-11 ───────────────┘          │         │
```

**Parallelism Score: 4/5** ✅
- Layer 0: 5 tasks — all can start on Day 1
- Layer 1: 3 tasks — T-06, T-07 start after T-02 (fast); T-08 needs all L0+L1
- Layer 2: 3 tasks — T-09, T-10, T-11 can largely overlap
- Layer 3: 2 tasks — sequential cleanup + release

**Estimated timeline (solo):** 2–3 weeks
- Week 1: T-01 to T-07 (scaffold + core parsers + models)
- Week 2: T-08 to T-11 (aggregator + CLI wiring)
- Week 3: T-12 to T-14 (polish + CI + release)
