# spec-result-parser

**CLI tool for analog IC engineers** — automated PASS/FAIL spec checking of Spectre PSF-ASCII and HSPICE MT0 simulation results.

## Installation

```bash
pip install spec-result-parser
```

## Quick Start

### Single-file check

```bash
spec-parser check result.psf --spec opamp.spec.yaml
```

### Multi-corner aggregation

```bash
spec-parser aggregate ./corners/ --spec opamp.spec.yaml
```

## Spec File (YAML)

```yaml
specs:
  gain_dc:  { min: 60,    max: null, unit: dB  }
  ugbw:     { min: 10e6,  max: null, unit: Hz  }
  pm:       { min: 45,    max: null, unit: deg }
  offset:   { min: null,  max: 5e-3, unit: V   }
```

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Spectre PSF-ASCII | `.psf` | Cadence Spectre simulation results |
| HSPICE MT0 | `.mt0` | Synopsys HSPICE `.MEASURE` results |

## License

MIT — see [LICENSE](LICENSE)
