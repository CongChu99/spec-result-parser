# Proposal: spec-result-parser

## Why

Analog IC design engineers at Vietnamese fab-less companies (Viettel Hi-Tech, FPT Semiconductor, and similar) run dozens of SPICE simulations daily — Spectre on Cadence Virtuoso flows, HSPICE in Synopsys flows. After a corner sweep (typically 15–50 runs across PVT corners: TT/FF/SS/SF/FS × -40°C/27°C/125°C), engineers manually open each result file, extract scalar metrics (gain, bandwidth, phase margin, offset, CMRR, PSRR, slew rate, ...), and paste values into Excel to compare against spec targets.

This manual step wastes **1–3 hours per verification milestone** [estimate], introduces transcription errors, and has no traceability — the spec targets live in a Word doc or in someone's head, not in source control alongside the netlist.

No open-source tool today unifies multi-format parsing (PSF + HSPICE) with automated spec checking and multi-corner aggregation in a single CLI. Cadence ADE Maestro solves this but requires a $$$$ enterprise license and is GUI-bound. `psf-utils` only reads PSF ASCII. `hspiceParser` only handles HSPICE. Neither checks against spec targets.

**Build verdict**: BUILD — a MIT-licensed, pip-installable Python CLI that closes this gap for engineers who use Spectre and/or HSPICE and want spec verification to be as fast as running a shell command.

## What Changes

Engineers gain a unified CLI command (`spec-parser`) that:
1. Reads simulation result files (Spectre PSF-ASCII, HSPICE MT0) and extracts scalar measurements
2. Compares extracted measurements against spec targets defined in a YAML or CSV file
3. Prints a color-coded PASS/FAIL table to terminal instantly
4. Aggregates multi-corner results into a worst-case corner matrix with one command

This replaces the manual Excel workflow end-to-end for the two most common simulator formats in the VN IC design industry.

## Capabilities

### New Capabilities

- `psf-ascii-parser`: Parse Cadence Spectre PSF-ASCII result files and extract named scalar measurements
- `hspice-mt0-parser`: Parse HSPICE `.mt0` / printfile outputs and extract `.MEASURE` scalar results
- `spec-config-loader`: Load spec targets from a YAML file (Git-friendly) or CSV file (Excel-friendly), supporting min/max bounds per measurement
- `spec-checker`: Compare extracted measurements against spec targets and compute PASS/FAIL/MARGIN status per measurement per corner
- `corner-aggregator`: Aggregate results from a folder of simulation files, map to PVT corners, build a worst-case corner matrix, and report via rich terminal table

### Modified Capabilities

N/A — greenfield tool.

## Scope

### In Scope

- Spectre PSF-ASCII file parsing (`.psf`, `.raw` ASCII format output)
- HSPICE `.mt0` / `printfile` scalar measurement parsing
- YAML spec config file (`.spec.yaml`) — version-controllable, key-value of measurement → min/max
- CSV spec config file (`.spec.csv`) — two-column format: measurement, min, max
- `check` subcommand: parse single result file + spec config → terminal PASS/FAIL table
- `aggregate` subcommand: parse all result files in a folder + corner mapping YAML → worst-case corner matrix table
- Color-coded terminal output: FAIL=red, MARGIN(<10%)=yellow, PASS=green via `rich` library
- pip-installable package (`pip install spec-result-parser`); MIT license
- Exit code 0 = all PASS, exit code 1 = any FAIL, exit code 2 = config/parse error

### Out of Scope (Non-Goals)

- ngspice RAW file parsing (v2)
- Calibre LVS/DRC log parsing (v2)
- Excel/PDF/HTML report export (v2)
- `--json` machine-readable output mode (v2)
- HSPICE binary `.tr0`, `.ac0` waveform parsing (v2 — ASCII `.mt0` covers measurement data)
- Spectre PSFXL binary parsing (v2)
- Monte Carlo / statistical aggregation — mean, sigma, yield (v2)
- GUI of any kind
- Integration with Cadence/Synopsys license server

## Success Criteria

- Engineer can run `spec-parser check result.psf --spec opamp.spec.yaml` and see PASS/FAIL within 2 seconds
- Engineer can run `spec-parser aggregate ./corners/ --spec opamp.spec.yaml` on a folder of 25 result files and get a complete corner matrix within 5 seconds
- Spec YAML file can be committed to Git alongside the netlist and reviewed in a pull request
- Zero EDA vendor license required to install or run the tool
- Published to PyPI — `pip install spec-result-parser` works on Linux (primary) and macOS
- README includes quickstart with real opamp example (gain, BW, PM, CMRR specs)
- All core parsers covered by pytest test suite using reference fixture files

## Impact

- **Replaces**: Manual Excel-based result collection and spec comparison
- **Positions against**: `psf-utils` (no spec check), `hspiceParser` (no spec check, single format), Cadence ADE Maestro (GUI-only, expensive)
- **Enables**: Spec verification to be scripted into Makefile / CI pipeline via exit codes in v2
- **Dependencies added**: `rich` (terminal UI), `PyYAML` (YAML config), `pandas` (CSV + data frame for corner matrix)
- **No runtime vendor dependency**: Runs completely offline with no Cadence/Synopsys tool in PATH
