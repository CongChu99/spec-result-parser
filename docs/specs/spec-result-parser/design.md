# Design: spec-result-parser

## Context

Analog IC engineers using Cadence Spectre or Synopsys HSPICE run 15–50 simulation files per corner sweep. Today they manually collect scalar measurement results and paste into Excel. This tool eliminates that step via a single CLI command. Greenfield Python project — no existing codebase to integrate with.

## Architecture Overview

```
spec-parser CLI (click)
        |
        +---> check subcommand
        |           |
        |           +---> FormatDetector (detect PSF / MT0 by extension + header)
        |           +---> Parser (PSFAsciiParser | HspiceMT0Parser)
        |           +---> SpecLoader (YAML | CSV)
        |           +---> SpecChecker
        |           +---> TerminalRenderer (rich table)
        |
        +---> aggregate subcommand
                    |
                    +---> CornerLoader (corners.yaml or flat-filename mode)
                    +---> FormatDetector + Parser (per file)
                    +---> SpecLoader
                    +---> CornerAggregator (pandas DataFrame pivot)
                    +---> TerminalRenderer (rich corner matrix table)
```

All components are stateless, pure-function style. No database, no daemon, no network calls.

## Components

### Component 1: FormatDetector
- **Purpose**: Auto-detect simulator file format from file extension (`.psf` → PSF-ASCII, `.mt0` → HSPICE MT0) and validate with a header check
- **Interface**: `detect(filepath: Path) -> Format | None`; returns `Format.PSF_ASCII`, `Format.HSPICE_MT0`, or `None` (unsupported)
- **Dependencies**: None (stdlib `pathlib` only)

### Component 2: PSFAsciiParser
- **Purpose**: Parse a Cadence Spectre PSF-ASCII file and return a list of scalar `Measurement` objects
- **Interface**: `parse(filepath: Path) -> list[Measurement]`; raises `ParseError` on invalid format
- **Dependencies**: stdlib `re`, `pathlib`
- **Key logic**: Scan for `VALUE` section in PSF; extract name-value-unit triplets from lines matching `"<name>" <value> <unit>`; skip waveform sections (detect via `SWEEP` keyword)

### Component 3: HspiceMT0Parser
- **Purpose**: Parse HSPICE `.mt0` / printfile and return `Measurement` objects from `.MEASURE` results
- **Interface**: `parse(filepath: Path) -> list[Measurement]`; raises `ParseError` on invalid format
- **Dependencies**: stdlib `re`, `pathlib`
- **Key logic**: Scan for lines matching variable name patterns (alphanumeric `=` value format); handle scientific notation (`12.5e6`); skip header comment lines starting with `$` or `*`

### Component 4: SpecLoader
- **Purpose**: Load SpecTarget definitions from a YAML or CSV file; auto-detect format from extension
- **Interface**: `load(filepath: Path) -> list[SpecTarget]`; raises `ConfigError` on invalid file
- **Dependencies**: `PyYAML`, `pandas`

### Component 5: SpecChecker
- **Purpose**: Compare a list of `Measurement` objects against a list of `SpecTarget` objects; return `SpecCheck` results with status and margin
- **Interface**: `check(measurements: list[Measurement], targets: list[SpecTarget], margin_threshold: float = 0.10) -> list[SpecCheck]`
- **Dependencies**: None (pure Python math)
- **Key logic**:
  ```
  margin_pct = (value - min) / abs(min)  for min-bound
  margin_pct = (max - value) / abs(max)  for max-bound
  status = FAIL if value < min or value > max
  status = MARGIN if 0 < margin_pct < margin_threshold
  status = PASS otherwise
  ```

### Component 6: CornerAggregator
- **Purpose**: Load and parse all result files in a folder; map to corners; build a `CornerMatrix` (pandas DataFrame) with worst-case row
- **Interface**: `aggregate(folder: Path, spec_file: Path, corners_file: Path | None) -> CornerMatrix`
- **Dependencies**: `pandas`, FormatDetector, all Parsers, SpecLoader, SpecChecker

### Component 7: TerminalRenderer
- **Purpose**: Render `list[SpecCheck]` or `CornerMatrix` as a color-coded `rich` table to stdout
- **Interface**: `render_check(checks: list[SpecCheck])` | `render_matrix(matrix: CornerMatrix)`
- **Dependencies**: `rich`
- **Color rules**: Status FAIL → red, MARGIN → yellow, PASS → green, N/A → dim white

## Data Model

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Format(Enum):
    PSF_ASCII  = "psf_ascii"
    HSPICE_MT0 = "hspice_mt0"

class Status(Enum):
    PASS   = "PASS"
    FAIL   = "FAIL"
    MARGIN = "MARGIN"
    NA     = "N/A"

@dataclass
class Measurement:
    name:  str
    value: float
    unit:  Optional[str]

@dataclass
class SpecTarget:
    name:  str
    min:   Optional[float]   # None = no lower bound
    max:   Optional[float]   # None = no upper bound
    unit:  Optional[str]

@dataclass
class SpecCheck:
    measurement: Measurement
    target:      SpecTarget
    status:      Status
    margin_pct:  Optional[float]  # None if FAIL or N/A

@dataclass
class Corner:
    name:    str           # e.g., "SS_1V62_m40"
    process: str           # TT / FF / SS / SF / FS
    voltage: float         # e.g., 1.8
    temp:    float         # e.g., -40

# CornerMatrix = pandas DataFrame with index=corner_names, columns=spec_names, values=SpecCheck
```

## API Design

CLI interface (not HTTP). Subcommand signatures:

```bash
# Single-file spec check
spec-parser check <result_file> \
    --spec <spec_file.yaml|.csv> \
    [--margin-threshold <float, default=0.10>] \
    [--verbose]

# Multi-corner aggregation
spec-parser aggregate <results_folder> \
    --spec <spec_file.yaml|.csv> \
    [--corners <corners.yaml>] \
    [--margin-threshold <float>] \
    [--verbose]
```

Exit codes:
- `0` — all specs PASS
- `1` — one or more specs FAIL
- `2` — config/parse error (bad file, missing file, YAML syntax error)

## Error Handling

| Error Condition | Behavior | Exit Code |
|----------------|----------|-----------|
| Result file not found | `ERROR: File not found: result.psf` | 2 |
| Unsupported file format | `ERROR: Cannot detect format for result.tr0` | 2 |
| PSF/MT0 parse failure | `ERROR: Cannot parse result.psf as PSF-ASCII` | 2 |
| Spec file not found | `ERROR: Spec file not found: opamp.spec.yaml` | 2 |
| YAML syntax error in spec | `ERROR: Invalid YAML in opamp.spec.yaml: <detail>` | 2 |
| CSV spec missing required columns | `ERROR: CSV spec must have columns: measurement, min, max` | 2 |
| Measurement in spec not in result | `WARN: Spec '<name>' not found in result — skipped` (non-fatal) | — |
| File in aggregate folder fails to parse | `WARN: Skipping <file> — parse error` (non-fatal, continue) | — |
| Aggregate folder is empty | `ERROR: No supported result files found in <folder>` | 2 |
| All measurements fail | Summary: `X of Y specs FAILED` | 1 |

**Design principle**: Parse errors on individual files within `aggregate` are non-fatal warnings. Configuration errors are always fatal (exit 2). Spec failures are reported but tool runs to completion (exit 1).

## Goals / Non-Goals

**Goals:**
- Parse Spectre PSF-ASCII and HSPICE MT0 files correctly across common use cases
- Check scalar measurements against min/max spec bounds with PASS/FAIL/MARGIN status
- Aggregate multi-corner folders into a worst-case matrix with one command
- Be installable via `pip install spec-result-parser` with no EDA vendor dependency
- Produce clear, color-coded terminal output readable at a glance

**Non-Goals:**
- Binary file parsing (PSFXL, HSPICE TR0/AC0) — v2
- ngspice RAW parsing — v2
- Calibre LVS/DRC log parsing — v2
- Excel/PDF/HTML report generation — v2
- JSON output mode — v2
- Any GUI, web UI, or database
- Simulation running — this tool only reads existing output files

## Decisions

### Decision 1: Write custom ASCII parsers vs. use existing libraries
- **Chose**: Custom pure-Python parsers for PSF-ASCII and HSPICE MT0
- **Rationale**: `psf-utils` uses a GPL-adjacent license that complicates MIT distribution. `hspiceParser` is unmaintained. ASCII formats are simple enough to parse with stdlib `re` in < 100 lines per parser.
- **Alternative rejected**: `psf-utils` as backend — license risk; `spicelib` RawRead — designed for waveform data, not scalar measurements from `.MEASURE`

### Decision 2: `click` over `argparse`
- **Chose**: `click`
- **Rationale**: Multi-subcommand structure (`check`, `aggregate`) is ergonomic in click. Auto-help is better. Decorators are concise. Negligible size overhead (~100KB).
- **Alternative rejected**: `argparse` — verbose; `typer` — adds pydantic dependency unnecessarily

### Decision 3: `pandas` for corner aggregation
- **Chose**: `pandas` DataFrame for corner × spec matrix
- **Rationale**: Pivot table, min/argmin for worst-case, column slicing — all 1-liners with pandas. Alternative (nested dicts) requires 2× code for same result.
- **Alternative rejected**: plain Python dicts — works but significantly more code for aggregation logic

### Decision 4: Terminal-only output for v1
- **Chose**: Terminal-only (rich table)
- **Rationale**: Fastest to implement; engineers running CLI want immediate visual feedback. Excel/PDF export deferred to v2 to hit 2–3 week timeline.
- **Alternative rejected**: Excel first — openpyxl adds scope; terminal output covers the core loop

## Risks / Trade-offs

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| PSF-ASCII format varies across Spectre versions — parser may miss edge cases | Medium | Ship with reference fixture files from known Spectre versions; open GitHub issues for format variants |
| HSPICE MT0 column layout differs between HSPICE versions (2021 vs 2023) | Medium | Test against multiple MT0 reference files; make parser tolerant of whitespace variations |
| `pandas` dependency adds 15–20MB to install — may feel heavy for a CLI tool | Low | Acceptable for this user base (engineers who already have numpy/pandas in conda env). Document in README. |
| Open-source ASIC community may be primary adopter, not commercial VN teams | High | Acceptable trade-off — open-source community validates the tool; commercial adoption follows organically |
| GPL-contamination risk if `psf-utils` code is accidentally used as reference | Low | Write parsers from scratch using only PSF format documentation; do not read psf-utils source |

## Testing Strategy

### Unit Tests (pytest)
- **PSFAsciiParser**: Test against 3+ reference PSF-ASCII fixture files (from open-source Spectre runs); assert correct measurement names, values, units
- **HspiceMT0Parser**: Test against 3+ reference MT0 fixture files; assert correct `.MEASURE` extraction, handle scientific notation
- **SpecLoader (YAML)**: Test load/parse with valid YAML, missing fields, malformed YAML, one-sided specs (null min/max)
- **SpecLoader (CSV)**: Test with valid CSV, missing columns, blank min/max cells
- **SpecChecker**: Unit test all 3 status paths (PASS, FAIL, MARGIN), margin calculation correctness, both bound directions
- **FormatDetector**: Test extension-based detection for `.psf`, `.mt0`, `.tr0` (unsupported)

### Integration Tests (pytest)
- **`check` end-to-end**: Real PSF fixture file + YAML spec → assert correct PASS/FAIL table and exit code
- **`aggregate` end-to-end**: Folder of 5 fixture files (mix of PSF and MT0) + spec + corners YAML → assert correct corner matrix and worst-case row
- **Error path**: Missing file, bad YAML → assert exit code 2 and error message

### Manual Verification
- Run against real Spectre PSF output from ngspice/Xschem opamp design (open PDK)
- Run against real HSPICE MT0 output (if available from user)
- Verify terminal color rendering on Linux terminal (gnome-terminal, xterm, iTerm2)
