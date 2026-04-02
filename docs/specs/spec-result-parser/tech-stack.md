# Tech Stack: spec-result-parser

## Frontend
N/A — CLI tool only. No web UI.

## CLI Framework
- **Framework**: `click` (Python) — industry-standard CLI framework; supports subcommands (`check`, `aggregate`), options/flags, auto-help generation
- **Alternative considered**: `argparse` (stdlib) — simpler but verbose; `typer` — cleaner but extra dependency. `click` wins: well-maintained, widely known, pip-installable.
- **Terminal UI**: `rich` — color-coded tables, progress bars, styled output. Zero config. MIT licensed.

## Core Parsing Libraries
- **PSF-ASCII parser**: Custom pure-Python regex/line parser (no external dep)
  - Rationale: PSF-ASCII is a text format with well-understood structure; rolling own parser avoids GPL license contamination from `psf-utils`
  - Lock-in risk: Low — we own the parser
- **HSPICE MT0 parser**: Custom pure-Python line parser
  - Rationale: MT0 / printfile is plain ASCII with fixed column layout; trivially parseable with Python stdlib
  - Lock-in risk: Low
- **Alternative considered**: Use `spicelib` or `hspiceParser` as backends — rejected due to GPL/unclear license terms and single-format scope

## Spec Config
- **YAML**: `PyYAML` — standard, widely used, well-maintained, MIT License
- **CSV**: `pandas` — for CSV loading + corner matrix DataFrame operations
  - Alternative considered: stdlib `csv` — sufficient for simple CSV but pandas gives free DataFrame for corner aggregation
  - Lock-in risk: Low

## Data Processing
- **Core data structures**: Python `dataclasses` + `typing` — zero deps, clean models for `Measurement`, `SpecTarget`, `SpecCheck`, `CornerMatrix`
- **Aggregation engine**: `pandas` DataFrame — pivot table for corner × spec matrix; worst-case margin via `df.min()`

## Backend / Database
N/A — stateless CLI tool. No persistent storage. All state is in-memory per invocation.

## Infrastructure
N/A — not a hosted service.

## Packaging & Distribution
- **Package manager**: `pip` / PyPI — `pip install spec-result-parser`
- **Build backend**: `pyproject.toml` + `hatchling` (modern, PEP 517/518 compliant)
- **Entry point**: `spec-parser` CLI command registered via `[project.scripts]`
- **Python version support**: Python 3.9+ (covers all modern Linux environments at VN IC companies)
- **Platform**: Linux primary (all EDA environments run Linux); macOS secondary

## CI/CD
- **Pipeline**: GitHub Actions
  - `pytest` on push/PR (Linux + macOS matrix)
  - `pypi-publish` action on version tag push
- **Test fixtures**: `tests/fixtures/` — reference PSF-ASCII and HSPICE MT0 sample files (generated from open-source simulations)

## Monitoring & Logging
N/A — CLI tool. No production monitoring.

- **Debug output**: `--verbose` / `-v` flag prints parser debug trace to stderr
- **Logging**: Python `logging` stdlib — DEBUG level enabled with `-v`

## Dependency Summary

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| `click` | >=8.0 | CLI framework | BSD |
| `rich` | >=12.0 | Terminal color output | MIT |
| `PyYAML` | >=6.0 | YAML spec config | MIT |
| `pandas` | >=1.5 | CSV loading + corner matrix | BSD |

**Total runtime deps**: 4 packages. No compiled extensions. Pure Python.
