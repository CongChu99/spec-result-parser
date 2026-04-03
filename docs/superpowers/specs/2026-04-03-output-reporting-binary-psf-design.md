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
│   ├── psf_ascii.py        (existing — return type unchanged: List[Measurement])
│   ├── hspice_mt0.py       (existing — return type unchanged: List[Measurement])
│   └── psf_binary.py       NEW — returns dict[str, Measurement | Waveform]
├── evaluator.py            NEW — Expression evaluator
├── models.py               EXTENDED — add Waveform dataclass, PSF_BINARY Format variant
├── renderer.py             (existing — TerminalRenderer, unchanged)
├── exporters/              NEW package
│   ├── __init__.py
│   ├── csv_exporter.py
│   ├── json_exporter.py
│   └── html_exporter.py
│   └── _vendor/
│       └── chart.min.js    vendored Chart.js 4.4.x
└── cli.py                  EXTENDED — --format / --output flags
```

### Data flow

```
result file
    ↓
[Parser] (psf_ascii / hspice_mt0 / psf_binary)
    ↓ measurements: List[Measurement]  OR  dict[str, Measurement | Waveform]
[ExpressionEvaluator]   ← only when spec has "measure:" field AND waveforms present
    ↓ scalar Measurement values (List[Measurement])
[SpecChecker]
    ↓ list[CheckResult]
[TerminalRenderer]  → stdout (always, unless --quiet)
[CSVExporter]       → file or stdout if --format csv
[JSONExporter]      → file or stdout if --format json
[HTMLExporter]      → file (required) if --format html
```

### Parser dispatch

The existing `_PARSERS` dispatch table in `cli.py` maps `Format` → parser function. Binary PSF adds a new entry:

```python
_PARSERS = {
    Format.PSF_ASCII:   parse_psf_ascii,    # returns List[Measurement]
    Format.HSPICE_MT0:  parse_hspice_mt0,   # returns List[Measurement]
    Format.PSF_BINARY:  parse_psf_binary,   # returns dict[str, Measurement | Waveform]
}
```

The CLI normalises the binary parser output through `ExpressionEvaluator` before passing to `SpecChecker`, so `SpecChecker` always receives `List[Measurement]`.

---

## 3. Models changes (`models.py`)

### `Waveform` dataclass (new)

```python
@dataclass(frozen=True)
class Waveform:
    sweep_var: str       # e.g. "freq"
    x: np.ndarray
    y: np.ndarray
    unit: str
    fmt: Format = Format.PSF_BINARY
```

### `Format` enum extension

```python
class Format(str, Enum):
    PSF_ASCII  = "psf_ascii"
    HSPICE_MT0 = "hspice_mt0"
    PSF_BINARY = "psf_binary"   # NEW
```

`format_detector.py` extended: files detected as binary PSF (magic bytes `0x00 0x00 0x00 0x01` at offset 0) return `Format.PSF_BINARY`.

### `SpecTarget` dataclass extension

```python
@dataclass(frozen=True)
class SpecTarget:
    name: str
    min: Optional[float]
    max: Optional[float]
    unit: str
    measure: Optional[str] = None   # NEW — waveform expression, YAML only
```

`measure` defaults to `None` — fully backward compatible. CSV spec files do **not** support `measure:` (YAML only). Attempting to use `measure:` in CSV raises exit code 2: `ERROR: 'measure:' is only supported in YAML spec files`.

`ExpressionEvaluator` stamps `fmt = Format.PSF_BINARY` on output `Measurement` objects it produces.

---

## 4. CLI Interface

### New flags (both `check` and `aggregate`)

```
--format [csv|json|html]   Output format (optional)
--output PATH              Output file path (optional)
--quiet                    Suppress terminal Rich output (does NOT affect exit codes)
```

### Behaviour rules

| `--format` | `--output` | Result |
|---|---|---|
| csv/json | absent | print to stdout |
| csv/json | provided | write to file |
| html | absent | ERROR exit 2: HTML requires --output |
| absent | `file.csv/json/html` | auto-detect format from extension |
| absent | `file.xyz` | ERROR exit 2: unrecognised extension, use --format |

### Backward compatibility and quiet-mode

- `--quiet` suppresses only the Rich terminal renderer; **exit codes are never affected**.
- When both a format exporter (`--format csv`) and the terminal renderer are active simultaneously, that is **intentional** — the terminal shows interactive output while the file captures machine-readable results.
- Format / extension errors are detected **before** any parsing or output is produced, so no partial output is written on error.

### Examples

```bash
spec-parser check result.psf --spec opamp.yaml --format json
spec-parser check result.psf --spec opamp.yaml --format csv --output report.csv
spec-parser aggregate ./corners/ --spec opamp.yaml --format html --output report.html
spec-parser aggregate ./corners/ --spec opamp.yaml --output report.json  # auto-detect
spec-parser check result.psf --spec opamp.yaml --format json --quiet    # JSON only, no terminal
```

---

## 5. JSON Schema

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
      "results": [ "..." ]
    }
  ]
}
```

`"corners"` key is only present in `aggregate` mode.

---

## 6. HTML Dashboard

Single self-contained `.html` file (no server, no CDN — all JS/CSS inlined):

- **Summary cards**: total / PASS / FAIL / MARGIN counts
- **Margin bar chart**: one bar per spec, coloured by status (Chart.js 4.4.x inlined)
- **Interactive table**: filter dropdown (All / PASS / FAIL / MARGIN), sortable columns

Chart.js is vendored as `src/spec_result_parser/exporters/_vendor/chart.min.js` (pinned to 4.4.x), committed to source control. `html_exporter.py` loads it via `importlib.resources` and inlines the content into the output HTML. No build-time step required.

---

## 7. Binary PSF Parser

### Interface

```python
# src/spec_result_parser/parsers/psf_binary.py
def parse(path: str) -> dict[str, Measurement | Waveform]:
    ...
```

Existing PSF-ASCII and HSPICE parsers are **unchanged** (still return `List[Measurement]`).

### PSF section → output mapping

| PSF section type | Output |
|---|---|
| Scalar (no sweep) | `Measurement(value=float, unit=str, fmt=Format.PSF_BINARY)` |
| Swept scalar | `Waveform(sweep_var, x=array, y=array, unit=str)` |
| Full waveform | `Waveform(sweep_var, x=array, y=array, unit=str)` |

### `libpsf` dependency strategy

`libpsf` is declared as an optional extra: `pip install spec-result-parser[binary]`.

When `libpsf` is **not installed**, `parse()` raises `ParseError` immediately:
```
ERROR: Binary PSF requires the 'binary' extra: pip install spec-result-parser[binary]
```

There is **no manual fallback parser** in v0.2.0. This avoids maintaining two code paths with potentially divergent output. A manual fallback may be considered in a future version.

---

## 8. Expression Evaluator

### Spec YAML extension

```yaml
specs:
  gain_dc:  { min: 60, unit: dB }                                     # scalar — unchanged
  ugbw:     { min: 10e6, measure: "cross(vout_db, 0)", unit: Hz }
  pm:       { min: 45,   measure: "phase_margin(vout)", unit: deg }
  peak_out: { max: 1.8,  measure: "max(vout)", unit: V }
```

`measure:` is **YAML only**. CSV spec files do not support it.

### Supported functions

| Function | Description |
|---|---|
| `max(sig)` | Maximum value of signal |
| `min(sig)` | Minimum value of signal |
| `at(sig, x)` | Signal value at specific x coordinate |
| `cross(sig, level)` | x value where signal crosses level (rising) |
| `phase_margin(sig)` | Phase at unity-gain crossing (dB signal) |

### Implementation

- Parse `measure:` string into AST — **no direct `eval()`** (security)
- Resolve signal names against the parsed waveform dict; raise `ParseError` if not found
- Compute result using NumPy operations
- Return `Measurement(value=float, unit=..., fmt=Format.PSF_BINARY)` for SpecChecker input

---

## 9. Error Handling

| Situation | Exit code | Message |
|---|---|---|
| Binary PSF unreadable | 2 | `ERROR: Cannot parse binary PSF file: <path>` |
| `libpsf` not installed | 2 | `ERROR: Binary PSF requires the 'binary' extra: pip install spec-result-parser[binary]` |
| `measure:` syntax error | 2 | `ERROR: Invalid expression '<expr>': <detail>` |
| Signal not found | 2 | `ERROR: Signal '<name>' not found in result file` |
| `--format html` without `--output` | 2 | `ERROR: HTML output requires --output <file.html>` |
| Unknown file extension in `--output` | 2 | `ERROR: Cannot detect format from '.xyz'. Use --format` |
| `measure:` used in CSV spec file | 2 | `ERROR: 'measure:' is only supported in YAML spec files` |

---

## 10. Testing

One test file per new module, following existing conventions:

| Test file | Coverage |
|---|---|
| `test_psf_binary.py` | scalar / swept / waveform parse; corrupt file; missing file; libpsf-absent (mock import) |
| `test_evaluator.py` | all 5 functions; bad expression; missing signal; scalar passthrough |
| `test_csv_exporter.py` | check mode; aggregate mode; stdout mode |
| `test_json_exporter.py` | schema validation; all metadata fields; corners key present/absent |
| `test_html_exporter.py` | file created; summary cards present; table present; Chart.js inlined |
| `test_cli_output.py` | --format; --output; auto-detect; html-without-output error; --quiet suppresses terminal not exit code |
| `test_models.py` (extend) | Waveform dataclass; PSF_BINARY Format; SpecTarget.measure default None |

Coverage gate remains **80%**.

---

## 11. Dependencies

| Package | Usage | pyproject.toml change |
|---|---|---|
| `numpy` | Waveform arrays, expression evaluation | Add to `dependencies` |
| `libpsf` | Binary PSF parsing | Add to `[project.optional-dependencies] binary = ["libpsf"]` |
| Chart.js 4.4.x | HTML dashboard charts | Vendor as static file in package — no pip dependency |
