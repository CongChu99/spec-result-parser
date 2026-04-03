# LDO Regulator Example — 1.2V / 5V Input, Sky130 PDK

Linear regulator with <5mV output error and >50dB PSRR across PVT corners.
Result files use HSPICE MT0 format (`.mt0`).

## Commands

```bash
spec-parser aggregate corners/ --spec spec.yaml
spec-parser aggregate corners/ --spec spec.yaml --output ldo_corners.html
```
