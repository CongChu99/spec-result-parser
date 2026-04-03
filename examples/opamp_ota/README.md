# OTA Example — Two-Stage Miller Compensated

Sky130 PDK Two-Stage Miller OTA with 12.5 MHz GBW target.

## Specs

| Parameter | Min | Max | Unit |
|-----------|-----|-----|------|
| `gain_dc` | 60 | — | dB |
| `ugbw` | 10M | — | Hz |
| `pm` | 45 | — | deg |
| `offset_v` | — | 5m | V |
| `cmrr` | 70 | — | dB |
| `psrr` | 65 | — | dB |

## Commands

```bash
# Corner sweep
spec-parser aggregate corners/ --spec spec.yaml

# Monte Carlo (20 samples, σ≈3%)
spec-parser montecarlo mc_runs/ --spec spec.yaml --output mc_report.html
```
