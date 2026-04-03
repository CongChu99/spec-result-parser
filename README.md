# spec-result-parser

**CLI tool for analog IC engineers** — automated PASS/FAIL spec checking of Spectre PSF-ASCII, HSPICE MT0, and Cadence binary PSF simulation results.

[![CI](https://github.com/CongChu99/spec-result-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/CongChu99/spec-result-parser/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/spec-result-parser)](https://pypi.org/project/spec-result-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why

After a corner sweep, analog IC engineers manually copy values from Spectre/HSPICE result files into Excel to check against spec targets — **1–3 hours per verification milestone**, with transcription errors and no traceability.

`spec-result-parser` reduces that to one command.

## Installation

```bash
# pip
pip install spec-result-parser

# conda / mamba (conda-forge)
conda install -c conda-forge spec-result-parser
# or
mamba install spec-result-parser
```

Requires Python ≥ 3.9.

## Quick Start

### 1. Define your spec targets (YAML or CSV)

```yaml
# opamp.spec.yaml
specs:
  gain_dc:  { min: 60,    max: null, unit: dB  }
  ugbw:     { min: 10e6,  max: null, unit: Hz  }
  pm:       { min: 45,    max: null, unit: deg }
  offset_v: { min: null,  max: 5e-3, unit: V   }
  cmrr:     { min: 70,    max: null, unit: dB  }
```

Or CSV:

```csv
name,min,max,unit
gain_dc,60,,dB
ugbw,10000000,,Hz
pm,45,,deg
offset_v,,0.005,V
cmrr,70,,dB
```

### 2. Check a single result file

```bash
spec-parser check result.psf --spec opamp.spec.yaml
```

Example output:

```
 Spec        Value         Min      Max     Status   Margin
 ─────────────────────────────────────────────────────────
 gain_dc     68.5 dB      60 dB     —       PASS    +14.2%
 ugbw        12.5 MHz     10 MHz    —       PASS    +25.0%
 pm          67.2 deg     45 deg    —       PASS    +49.3%
 offset_v    0.0001 V     —         0.005V  PASS    +98.0%
 cmrr        85 dB        70 dB     —       PASS    +21.4%

✓ All 5 specs: PASS
```

Exit codes: `0` = all PASS, `1` = any FAIL, `2` = parse/config error.

### 3. Aggregate a multi-corner sweep

```bash
spec-parser aggregate ./corners/ --spec opamp.spec.yaml
```

Example output:

```
 Corner     gain_dc    ugbw      pm        offset_v   Overall
 ──────────────────────────────────────────────────────────────
 tt_27      PASS       PASS      PASS      PASS       PASS
 ss_125     MARGIN     MARGIN    MARGIN    PASS       MARGIN
 ff_m40     PASS       PASS      PASS      PASS       PASS
 sf_m40     FAIL       FAIL      FAIL      FAIL       FAIL
 ──────────────────────────────────────────────────────────────
 Worst Case FAIL       FAIL      FAIL      PASS       FAIL

✗ 1 of 4 corners have FAIL
```

## Options

### `check`

```
spec-parser check RESULT_FILE --spec SPEC_FILE [OPTIONS]

Options:
  -s, --spec PATH               YAML or CSV spec file [required]
  --margin-threshold FLOAT      % within a limit to flag as MARGIN [default: 10.0]
  --format [csv|json|html]      Export results in this format
  --output PATH                 Write output to this file (auto-detect format from extension)
  --quiet                       Suppress terminal table output (useful for CI pipelines)
  -v, --verbose                 Enable debug output
  --version                     Show version and exit
```

### `aggregate`

```
spec-parser aggregate FOLDER --spec SPEC_FILE [OPTIONS]

Options:
  -s, --spec PATH               YAML or CSV spec file [required]
  --corners PATH                Optional YAML mapping filenames to corner names
  --margin-threshold FLOAT      % within a limit to flag as MARGIN [default: 10.0]
  --format [csv|json|html]      Export results in this format
  --output PATH                 Write output to this file (auto-detect format from extension)
  --quiet                       Suppress terminal table output
  -v, --verbose                 Enable debug output
```

### `montecarlo`

```
spec-parser montecarlo FOLDER --spec SPEC_FILE [OPTIONS]

Options:
  -s, --spec PATH               YAML or CSV spec file [required]
  --n-sigma FLOAT               Sigma band for status check [default: 3.0]
  --margin-threshold FLOAT      % within a limit to flag as MARGIN [default: 10.0]
  --format [csv|json|html]      Export results in this format
  --output PATH                 Write output to this file
  --quiet                       Suppress terminal output
```

Each file in FOLDER is treated as one Monte Carlo sample.  The command computes
`mean`, `σ`, `Cpk`, and **estimated yield %** for every spec, and flags
`FAIL` when `mean ± 3σ` violates a bound.

```bash
# Terminal summary
spec-parser montecarlo ./mc_runs/ --spec opamp.spec.yaml

# HTML dashboard with per-spec histograms
spec-parser montecarlo ./mc_runs/ --spec opamp.spec.yaml --output mc_report.html
```

## Supported Formats

| Format | Extension | Simulator |
|--------|-----------|-----------|
| Spectre PSF-ASCII | `.psf` | Cadence Spectre |
| Cadence Binary PSF | `.psf` | Cadence Spectre (binary) |
| HSPICE MT0 | `.mt0` | Synopsys HSPICE |

Binary PSF support requires an optional dependency:

```bash
pip install spec-result-parser[binary]
```

## Status Values

| Status | Meaning |
|--------|---------|
| `PASS` | Value within bounds and well clear of limit |
| `MARGIN` | Passes but within `margin_threshold`% of a limit |
| `FAIL` | Value violates min or max bound |
| `N/A` | No spec defined for this measurement |

## What's New in v0.2.0

### Export to CSV, JSON, and HTML

Export results directly from the CLI instead of copy-pasting into spreadsheets:

```bash
# Export a PASS/FAIL table as CSV
spec-parser check result.psf --spec opamp.spec.yaml --output report.csv

# Export as JSON (machine-readable, includes metadata and timestamps)
spec-parser check result.psf --spec opamp.spec.yaml --output report.json

# Export as a standalone HTML dashboard (dark theme, filterable table, Chart.js bar chart)
spec-parser check result.psf --spec opamp.spec.yaml --output report.html

# Same options work with aggregate
spec-parser aggregate ./corners/ --spec opamp.spec.yaml --output corners.html
```

Format is inferred from the file extension automatically. Use `--format` to override:

```bash
spec-parser check result.psf --spec opamp.spec.yaml --format json
```

Use `--quiet` to suppress the terminal table (useful in CI pipelines):

```bash
spec-parser check result.psf --spec opamp.spec.yaml \
  --output report.json --quiet
echo $?  # 0 = PASS, 1 = FAIL
```

### Binary PSF Support

Native Cadence binary PSF files are now auto-detected by magic bytes and parsed via
[libpsf](https://pypi.org/project/libpsf/):

```bash
pip install spec-result-parser[binary]
spec-parser check result.psf --spec opamp.spec.yaml
```

### Waveform Expression Evaluator (YAML only)

For binary PSF files with swept waveforms, define how to extract a scalar spec value
using a `measure:` expression in your YAML spec:

```yaml
specs:
  ugbw:
    min: 10.0e6
    unit: Hz
    measure: "cross(vout_db, 0)"   # x-value where vout_db crosses 0 dB
  pm:
    min: 45
    unit: deg
    measure: "phase_margin(gain, phase)"
  gain_peak:
    min: 60
    unit: dB
    measure: "max(vout_db)"
```

Supported expressions:

| Expression | Description |
|------------|-------------|
| `max(sig)` | Maximum value of waveform |
| `min(sig)` | Minimum value of waveform |
| `at(sig, x)` | Waveform value at a specific x-axis point |
| `cross(sig, level)` | x-axis value at first rising crossing of `level` |
| `phase_margin(gain, phase)` | 180° + phase at unity-gain (0 dB) crossing |

## License

MIT — see [LICENSE](LICENSE)
