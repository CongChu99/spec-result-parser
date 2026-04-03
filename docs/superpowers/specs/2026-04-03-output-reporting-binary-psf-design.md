# Design: Output & Reporting + Binary PSF Parser

**Date:** 2026-04-03
**Project:** spec-result-parser
**Scope:** Group A (CSV/JSON/HTML export) + Group B (Binary PSF parser, expression evaluator)

---

## 1. Overview

Extend `spec-result-parser` v0.1.0 with:

1. **Multi-format output** — `--format` and `--output` flags on both `check` and `aggregate` subcommands, producing CSV, JSON, and HTML reports in addition to the existing terminal renderer.
2. **Binary PSF parser** — read Cadence Spectre binary PSF files (scalar, swept, and full waveform data).
3. **Expression evaluator** — allow spec YAML to define `measure:` expressions (e.g. `max(vout/vin)`) that are evaluated against waveform data to produce scalar values for spec checking.

---

## 2. Architecture

### New modules

```
src/spec_result_parser/
├── parsers/
│   ├── psf_ascii.py        (existing)
│   ├── hspice_mt0.py       (existing)
│   └── psf_binary.py       NEW — Binary PSF parser
├── evaluator.py            NEW — Expression evaluator
├── renderer.py             (existing — TerminalRenderer, unchanged)
├── exporters/              NEW package
│   ├── __init__.py
│   ├── csv_exporter.py
│   ├── json_exporter.py
│   └── html_exporter.py
└── cli.py                  EXTENDED — --format / --output flags
```

### Data flow

```
result file
    ↓
[Parser] (psf_ascii / hspice_mt0 / psf_binary)
    ↓ measurements: dict[str, Measurement | Waveform]
[ExpressionEvaluator]   ← only when spec has "measure:" field
    ↓ scalar Measurement values
[SpecChecker]
    ↓ list[CheckResult]
[TerminalRenderer]  → stdout (always, unless --quiet)
[CSVExporter]       → file or stdout if --format csv
[JSONExporter]      → file or stdout if --format json
[HTMLExporter]      → file (required) if --format html
```

---

## 3. CLI Interface

### New flags (both `check` and `aggregate`)

```
--format [csv|json|html]   Output format (optional)
--output PATH              Output file path (optional)
--quiet                    Suppress terminal output
```

### Behaviour rules

| `--format` | `--output` | Result |
|---|---|---|
| csv/json | absent | print to stdout |
| csv/json | provided | write to file |
| html | absent | ERROR: HTML requires --output |
| absent | `file.csv/json/html` | auto-detect format from extension |
| absent | `file.xyz` | ERROR: unrecognised extension, use --format |

### Examples

```bash
spec-parser check result.psf --spec opamp.yaml --format json
spec-parser check result.psf --spec opamp.yaml --format csv --output report.csv
spec-parser aggregate ./corners/ --spec opamp.yaml --format html --output report.html
spec-parser aggregate ./corners/ --spec opamp.yaml --output report.json  # auto-detect
```

---

## 4. JSON Schema

```json
{
  "meta": {
    "tool": "spec-result-parser",
    "version": "0.2.0",
    "timestamp": "2026-04-03T10:00:00Z",
    "spec_file": "opamp.spec.yaml",
    "result_file": "result.psf"
  },
  "summary": {
    "total": 5,
    "pass": 4,
    "fail": 1,
    "margin": 0,
    "overall": "FAIL"
  },
  "results": [
    {
      "spec": "gain_dc",
      "value": 68.5,
      "unit": "dB",
      "min": 60.0,
      "max": null,
      "status": "PASS",
      "margin_pct": 14.2
    }
  ],
  "corners": [
    {
      "name": "tt_27",
      "file": "tt_27.psf",
      "overall": "PASS",
      "results": [ ... ]
    }
  ]
}
```

`"corners"` key is only present in `aggregate` mode.

---

## 5. HTML Dashboard

Single self-contained `.html` file (no server, no CDN — all JS/CSS inlined):

- **Summary cards**: total / PASS / FAIL / MARGIN counts
- **Margin bar chart**: one bar per spec, coloured by status (Chart.js inlined)
- **Interactive table**: filter dropdown (All / PASS / FAIL / MARGIN), sortable columns

---

## 6. Binary PSF Parser

### Interface (matches existing parsers)

```python
# src/spec_result_parser/parsers/psf_binary.py
def parse(path: str) -> dict[str, Measurement | Waveform]:
    ...
```

### Data types

```python
@dataclass
class Waveform:
    sweep_var: str          # e.g. "freq"
    x: np.ndarray
    y: np.ndarray
    unit: str
```

### PSF section → output mapping

| PSF section type | Output |
|---|---|
| Scalar (no sweep) | `Measurement(value=float, unit=str)` |
| Swept scalar | `Waveform(x=array, y=array, unit=str)` |
| Full waveform | `Waveform(x=array, y=array, unit=str)` |

Use **`libpsf`** (pure Python, MIT) if available; fall back to manual binary parsing if not installed.

---

## 7. Expression Evaluator

### Spec YAML extension

```yaml
specs:
  gain_dc:  { min: 60, unit: dB }                                     # scalar — unchanged
  ugbw:     { min: 10e6, measure: "cross(vout_db, 0)", unit: Hz }
  pm:       { min: 45,   measure: "phase_margin(vout)", unit: deg }
  peak_out: { max: 1.8,  measure: "max(vout)", unit: V }
```

### Supported functions

| Function | Description |
|---|---|
| `max(sig)` | Maximum value of signal |
| `min(sig)` | Minimum value of signal |
| `at(sig, x)` | Signal value at specific x coordinate |
| `cross(sig, level)` | x value where signal crosses level (rising) |
| `phase_margin(sig)` | Phase at unity-gain crossing (dB signal) |

### Implementation

- Parse `measure:` string into AST — no direct `eval()` (security)
- Resolve signal names against the parsed waveform dict
- Compute result using NumPy operations
- Return `Measurement(value=float, unit=...)` for SpecChecker input

---

## 8. Error Handling

| Situation | Exit code | Message |
|---|---|---|
| Binary PSF unreadable | 2 | `ERROR: Cannot parse binary PSF file: <path>` |
| `measure:` syntax error | 2 | `ERROR: Invalid expression '<expr>': <detail>` |
| Signal not found | 2 | `ERROR: Signal '<name>' not found in result file` |
| `--format html` without `--output` | 2 | `ERROR: HTML output requires --output <file.html>` |
| Unknown file extension | 2 | `ERROR: Cannot detect format from '.xyz'. Use --format` |

---

## 9. Testing

One test file per new module, following existing conventions:

| Test file | Coverage |
|---|---|
| `test_psf_binary.py` | scalar / swept / waveform parse; corrupt file; missing file |
| `test_evaluator.py` | all 5 functions; bad expression; missing signal; scalar passthrough |
| `test_csv_exporter.py` | check mode; aggregate mode; stdout mode |
| `test_json_exporter.py` | schema validation; all metadata fields; corners key present/absent |
| `test_html_exporter.py` | file created; summary cards present; table present |
| `test_cli_output.py` | --format; --output; auto-detect; html-without-output error |

Coverage gate remains **80%**.

---

## 10. Dependencies

| Package | Usage | Already in pyproject.toml? |
|---|---|---|
| `numpy` | Waveform arrays, expression evaluation | No — add |
| `libpsf` | Binary PSF parsing (optional) | No — add as optional extra |
| `chart.js` | HTML dashboard charts | No — bundle inline at build time |

`libpsf` is declared as an optional dependency: `pip install spec-result-parser[binary]`.
