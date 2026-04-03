# spec-result-parser

**CLI tool for analog IC engineers** — automated PASS/FAIL spec checking of Spectre PSF-ASCII, HSPICE MT0, and Cadence binary PSF simulation results, with Monte Carlo statistical analysis.

[![CI](https://github.com/CongChu99/spec-result-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/CongChu99/spec-result-parser/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/spec-result-parser)](https://pypi.org/project/spec-result-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why

After a corner sweep, analog IC engineers manually copy values from Spectre/HSPICE result files into Excel to check against spec targets — **1–3 hours per verification milestone**, with transcription errors and no traceability.

`spec-result-parser` reduces that to one command:

```bash
spec-parser aggregate ./corners/ --spec opamp.spec.yaml --output report.html
```

---

## Installation

```bash
# pip
pip install spec-result-parser

# conda / mamba (conda-forge)
conda install -c conda-forge spec-result-parser
mamba install spec-result-parser

# Binary PSF support (optional)
pip install spec-result-parser[binary]
```

Requires Python ≥ 3.9.

---

## Quick Start

### Step 1 — Define your spec targets

Create a YAML file listing each measurement's min/max bounds:

```yaml
# opamp.spec.yaml
specs:
  gain_dc:  { min: 60,     max: null,  unit: dB  }   # DC open-loop gain
  ugbw:     { min: 10.0e6, max: null,  unit: Hz  }   # Unity-gain bandwidth
  pm:       { min: 45,     max: null,  unit: deg }   # Phase margin
  offset_v: { min: null,   max: 5.0e-3, unit: V  }   # Input offset voltage
  cmrr:     { min: 70,     max: null,  unit: dB  }   # CMRR
```

Or use CSV format:

```csv
name,min,max,unit
gain_dc,60,,dB
ugbw,10000000,,Hz
pm,45,,deg
offset_v,,0.005,V
cmrr,70,,dB
```

### Step 2 — Check a single result file

```bash
spec-parser check result.psf --spec opamp.spec.yaml
```

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

### Step 3 — Aggregate a multi-corner sweep

```bash
spec-parser aggregate ./corners/ --spec opamp.spec.yaml
```

```
 Corner     gain_dc    ugbw      pm        offset_v   Overall
 ──────────────────────────────────────────────────────────────
 tt_27      PASS       PASS      PASS      PASS       PASS
 ss_125     MARGIN     FAIL      PASS      PASS       FAIL
 ff_m40     PASS       PASS      PASS      PASS       PASS
 sf_27      MARGIN     PASS      PASS      PASS       MARGIN
 ──────────────────────────────────────────────────────────────
 Worst Case MARGIN     FAIL      PASS      PASS       FAIL

✗ 1 of 4 corners have FAIL
```

### Step 4 — Monte Carlo statistical analysis

```bash
spec-parser montecarlo ./mc_runs/ --spec opamp.spec.yaml
```

Each file in `mc_runs/` is one MC sample. The tool computes **mean, σ, Cpk, and estimated yield %**:

```
 Spec       N     Mean         σ       Min       Max      Cpk    Yield %   Status
 ──────────────────────────────────────────────────────────────────────────────────
 gain_dc   20    67.95 dB   2.10 dB  64.5 dB   72.6 dB   1.26   99.98%   MARGIN
 ugbw      20    12.3 MHz   681kHz   11.3MHz   13.5MHz    1.15   99.94%   MARGIN
 pm        20    65.7 deg   2.79 deg  59.8 deg  71.3 deg  2.47   100.0%   PASS
 offset_v  20   0.000 V    4.28e-5 V  ...       ...       38.0   100.0%   PASS
 cmrr      20    85.9 dB    3.1 dB   79.4 dB   91.7 dB   1.71   100.0%   PASS

✓ Monte Carlo: 5 specs checked, all PASS
```

Status rules:
- `FAIL` — `mean ± 3σ` violates a spec bound
- `MARGIN` — passes, but Cpk < 1.33 (< 99.99% yield headroom)
- `PASS` — Cpk ≥ 1.33

---

## Export Reports

All three commands support `--output` / `--format`:

```bash
# Export corner sweep as HTML dashboard (dark theme, filterable table, Chart.js)
spec-parser aggregate ./corners/ --spec opamp.spec.yaml --output corners.html

# Monte Carlo HTML report with per-spec histogram distributions
spec-parser montecarlo ./mc_runs/ --spec opamp.spec.yaml --output mc_report.html

# Machine-readable JSON (includes timestamps and metadata)
spec-parser check result.psf --spec opamp.spec.yaml --output report.json

# CSV (import into Excel or pandas)
spec-parser aggregate ./corners/ --spec opamp.spec.yaml --output corners.csv
```

Format is auto-detected from the file extension. Use `--format` to override:

```bash
spec-parser check result.psf --spec opamp.spec.yaml --format json
```

Use `--quiet` to suppress the terminal table (useful in CI):

```bash
spec-parser check result.psf --spec opamp.spec.yaml --output report.json --quiet
echo $?   # 0 = PASS, 1 = FAIL, 2 = error
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/verify.yml
name: Spec Verification
on: [push]

jobs:
  spec-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install spec-result-parser
      - name: Corner sweep
        run: |
          spec-parser aggregate ./sim_results/corners/ \
            --spec design/opamp.spec.yaml \
            --output corners.html --quiet
      - name: Monte Carlo yield check
        run: |
          spec-parser montecarlo ./sim_results/mc_runs/ \
            --spec design/opamp.spec.yaml --quiet
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: spec-reports
          path: "*.html"
```

### GitLab CI

```yaml
spec_verify:
  script:
    - pip install spec-result-parser
    - spec-parser aggregate corners/ --spec opamp.spec.yaml --quiet
  artifacts:
    paths: ["*.html"]
    when: always
```

Exit codes: `0` = all PASS, `1` = any FAIL, `2` = parse/config error.

---

## Command Reference

### `check` — Single file

```
spec-parser check RESULT_FILE --spec SPEC_FILE [OPTIONS]

Arguments:
  RESULT_FILE     Path to a .psf or .mt0 result file

Options:
  -s, --spec PATH               YAML or CSV spec file [required]
  --margin-threshold FLOAT      % within a limit to flag as MARGIN [default: 10.0]
  --format [csv|json|html]      Export format
  --output PATH                 Output file path (format inferred from extension)
  --quiet                       Suppress terminal output
  -v, --verbose                 Debug output
  --version                     Show version and exit
```

### `aggregate` — Multi-corner sweep

```
spec-parser aggregate FOLDER --spec SPEC_FILE [OPTIONS]

Arguments:
  FOLDER          Directory containing one result file per PVT corner

Options:
  -s, --spec PATH               YAML or CSV spec file [required]
  --corners PATH                YAML file mapping filenames to corner names
  --margin-threshold FLOAT      % within a limit to flag as MARGIN [default: 10.0]
  --format [csv|json|html]      Export format
  --output PATH                 Output file path
  --quiet                       Suppress terminal output
  -v, --verbose                 Debug output
```

### `montecarlo` — Statistical analysis

```
spec-parser montecarlo FOLDER --spec SPEC_FILE [OPTIONS]

Arguments:
  FOLDER          Directory containing one result file per MC sample

Options:
  -s, --spec PATH               YAML or CSV spec file [required]
  --n-sigma FLOAT               Sigma band for status check [default: 3.0]
  --margin-threshold FLOAT      % within a limit to flag as MARGIN [default: 10.0]
  --format [csv|json|html]      Export format
  --output PATH                 Output file (HTML includes per-spec histograms)
  --quiet                       Suppress terminal output
  -v, --verbose                 Debug output
```

---

## Supported Formats

| Format | Extension | Simulator |
|--------|-----------|-----------|
| Spectre PSF-ASCII | `.psf` | Cadence Spectre |
| Cadence Binary PSF | `.psf` | Cadence Spectre (binary mode) |
| HSPICE MT0 | `.mt0` | Synopsys HSPICE |

Format is auto-detected from file extension and header/magic bytes.
Binary PSF requires an optional dependency:

```bash
pip install spec-result-parser[binary]
```

---

## Waveform Expression Evaluator

For binary PSF files with swept waveforms, define a `measure:` expression in
your YAML spec to extract a scalar value automatically:

```yaml
specs:
  ugbw:
    min: 10.0e6
    unit: Hz
    measure: "cross(vout_db, 0)"        # x-value where Bode plot crosses 0 dB
  pm:
    min: 45
    unit: deg
    measure: "phase_margin(gain, phase)" # 180° + phase at 0 dB crossing
  gain_peak:
    min: 60
    unit: dB
    measure: "max(vout_db)"             # peak gain
```

| Expression | Description |
|------------|-------------|
| `max(sig)` | Maximum value of waveform |
| `min(sig)` | Minimum value of waveform |
| `at(sig, x)` | Waveform value at a specific x-axis point |
| `cross(sig, level)` | x-axis value at first rising crossing of `level` |
| `phase_margin(gain, phase)` | 180° + phase at unity-gain (0 dB) crossing |

`measure:` is only supported in YAML spec files, not CSV.

---

## Status Values

| Status | Meaning |
|--------|---------|
| `PASS` | Value within bounds, margin > threshold |
| `MARGIN` | Passes but within `margin_threshold`% of a limit (or Cpk < 1.33 for MC) |
| `FAIL` | Value violates min or max bound (or mean±3σ violates bound for MC) |
| `N/A` | No spec defined for this measurement |

---

## Real-World Examples

The [`examples/`](examples/) directory contains ready-to-run Sky130 PDK fixtures:

```bash
# OTA: 5 PVT corners (PSF-ASCII)
spec-parser aggregate examples/opamp_ota/corners/ \
  --spec examples/opamp_ota/spec.yaml --output ota_corners.html

# OTA: Monte Carlo yield analysis (20 samples)
spec-parser montecarlo examples/opamp_ota/mc_runs/ \
  --spec examples/opamp_ota/spec.yaml --output ota_mc.html

# LDO Regulator: 5 corners (HSPICE MT0)
spec-parser aggregate examples/ldo_regulator/corners/ \
  --spec examples/ldo_regulator/spec.yaml

# Bandgap Reference: 5 corners
spec-parser aggregate examples/bandgap/corners/ \
  --spec examples/bandgap/spec.yaml
```

| Example | Circuit | Format | Corners | MC |
|---------|---------|--------|---------|----|
| `opamp_ota/` | Two-Stage Miller OTA | PSF-ASCII | 5 | 20 |
| `ldo_regulator/` | 1.2V LDO Regulator | HSPICE MT0 | 5 | — |
| `bandgap/` | 1.25V Bandgap Reference | PSF-ASCII | 5 | — |

---

## Conda Packaging

A conda-forge recipe is provided in [`conda/`](conda/meta.yaml).

To submit to conda-forge:
1. Fork [conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes)
2. Copy `conda/meta.yaml` into `recipes/spec-result-parser/meta.yaml`
3. Update the `sha256` checksum after the PyPI release
4. Open a Pull Request

---

## License

MIT — see [LICENSE](LICENSE)
