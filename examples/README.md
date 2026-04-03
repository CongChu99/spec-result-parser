# Real-World Examples

Ready-to-run examples demonstrating `spec-result-parser` on realistic analog IC designs
using Sky130 PDK characterization values.

## Examples

| Example | Circuit | Format | Corners | MC Runs |
|---------|---------|--------|---------|---------|
| [`opamp_ota/`](opamp_ota/) | Two-stage Miller OTA | PSF-ASCII | 5 | 20 |
| [`ldo_regulator/`](ldo_regulator/) | 1.2V LDO Regulator | HSPICE MT0 | 5 | — |
| [`bandgap/`](bandgap/) | 1.25V Bandgap Reference | PSF-ASCII | 5 | — |

## Quick Start

```bash
pip install spec-result-parser

# Corner sweep — OTA
spec-parser aggregate examples/opamp_ota/corners/ --spec examples/opamp_ota/spec.yaml

# Export HTML dashboard
spec-parser aggregate examples/opamp_ota/corners/ \
  --spec examples/opamp_ota/spec.yaml \
  --output ota_corners.html

# Monte Carlo analysis (20 samples)
spec-parser montecarlo examples/opamp_ota/mc_runs/ \
  --spec examples/opamp_ota/spec.yaml

# Monte Carlo HTML report with histograms
spec-parser montecarlo examples/opamp_ota/mc_runs/ \
  --spec examples/opamp_ota/spec.yaml \
  --output ota_mc_report.html

# LDO corner sweep (HSPICE MT0 format)
spec-parser aggregate examples/ldo_regulator/corners/ \
  --spec examples/ldo_regulator/spec.yaml

# Bandgap reference corner sweep
spec-parser aggregate examples/bandgap/corners/ \
  --spec examples/bandgap/spec.yaml
```

## Notes

- All fixture files are **synthetic** but use values representative of real
  Sky130 IP characterization (TT/SS/FF/SF/FS × -40°C/27°C/125°C corners).
- Monte Carlo samples model ~3% process spread (1σ) around the TT/27°C nominal.
- Exit code `0` = all PASS, `1` = any FAIL — suitable for CI/CD gating.
