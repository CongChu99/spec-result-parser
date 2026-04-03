# Output Reporting + Binary PSF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CSV/JSON/HTML export flags to both CLI commands, plus a binary PSF parser and expression evaluator for waveform-based spec measurements.

**Architecture:** Incremental extension — new modules added alongside existing ones, no existing module restructured. The two subsystems (exporters and binary PSF) are independent and can be developed in parallel from Task 3 onward. Models and format-detector changes (Tasks 1–2) are shared prerequisites.

**Tech Stack:** Python 3.9+, click, rich, numpy, libpsf (optional extra), Chart.js 4.4.x (vendored)

---

## File Map

### Modified
- `src/spec_result_parser/models.py` — add `Waveform`, `PSF_BINARY` format, `SpecTarget.measure`
- `src/spec_result_parser/format_detector.py` — detect binary PSF magic bytes before null-byte guard
- `src/spec_result_parser/spec_loader.py` — read `measure:` from YAML; error on CSV
- `src/spec_result_parser/cli.py` — add `--format`, `--output`, `--quiet` to both commands
- `pyproject.toml` — add numpy dep, libpsf optional extra, binary extra
- `tests/test_models.py` — extend for Waveform / PSF_BINARY / SpecTarget.measure
- `tests/test_format_detector.py` — extend for binary PSF detection
- `tests/test_spec_loader.py` — extend for measure: YAML / CSV error

### Created
- `src/spec_result_parser/parsers/psf_binary.py`
- `src/spec_result_parser/evaluator.py`
- `src/spec_result_parser/exporters/__init__.py`
- `src/spec_result_parser/exporters/csv_exporter.py`
- `src/spec_result_parser/exporters/json_exporter.py`
- `src/spec_result_parser/exporters/html_exporter.py`
- `src/spec_result_parser/exporters/_vendor/chart.min.js` (download step)
- `tests/test_psf_binary.py`
- `tests/test_evaluator.py`
- `tests/test_csv_exporter.py`
- `tests/test_json_exporter.py`
- `tests/test_html_exporter.py`
- `tests/test_cli_output.py`

---

## Task 1: Extend models.py — Waveform, PSF_BINARY, SpecTarget.measure

**Files:**
- Modify: `src/spec_result_parser/models.py`
- Modify: `tests/test_models.py`

> NOTE: `SpecTarget` fields are `min_val` and `max_val` (not `min`/`max`) — match these exactly.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_models.py`:

```python
import numpy as np
from spec_result_parser.models import Format, Measurement, SpecTarget, Waveform


def test_format_psf_binary_value():
    assert Format.PSF_BINARY.value == "psf_binary"


def test_waveform_creation():
    w = Waveform(
        sweep_var="freq",
        x=np.array([1e6, 2e6]),
        y=np.array([0.5, 0.3]),
        unit="V",
        fmt=Format.PSF_BINARY,
    )
    assert w.sweep_var == "freq"
    assert w.unit == "V"


def test_spec_target_measure_defaults_none():
    t = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
    assert t.measure is None


def test_spec_target_measure_set():
    t = SpecTarget(name="ugbw", min_val=10e6, max_val=None, unit="Hz", measure="cross(vout_db, 0)")
    assert t.measure == "cross(vout_db, 0)"
```

- [ ] **Step 2: Run to confirm fail**

```bash
cd /home/congcp/Congcp/github/tools
python -m pytest tests/test_models.py::test_format_psf_binary_value -v
```
Expected: `FAILED` — `Format` has no `PSF_BINARY` attribute.

- [ ] **Step 3: Implement changes in models.py**

In the `Format` enum, add `PSF_BINARY = "psf_binary"` after `HSPICE_MT0`:

```python
class Format(Enum):
    PSF_ASCII  = "psf_ascii"
    HSPICE_MT0 = "hspice_mt0"
    PSF_BINARY = "psf_binary"
    UNKNOWN    = "unknown"
```

Add `Waveform` dataclass after `Measurement`:

```python
@dataclass
class Waveform:
    """A swept or waveform signal from a simulation result file."""

    sweep_var: str
    x: "np.ndarray"
    y: "np.ndarray"
    unit: Optional[str]
    fmt: Format = Format.PSF_BINARY
```

Add `numpy` import at top of file (lazy, to avoid hard dep at import time):

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import numpy as np
```

Add `measure` field to `SpecTarget`:

```python
@dataclass(frozen=True)
class SpecTarget:
    name: str
    min_val: Optional[float]
    max_val: Optional[float]
    unit: Optional[str]
    measure: Optional[str] = None   # waveform expression, YAML only
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_models.py -v
```
Expected: all `test_models.py` tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec_result_parser/models.py tests/test_models.py
git commit -m "feat: extend models — Waveform, PSF_BINARY format, SpecTarget.measure"
```

---

## Task 2: Extend format_detector.py — binary PSF magic bytes

**Files:**
- Modify: `src/spec_result_parser/format_detector.py`
- Modify: `tests/test_format_detector.py`

> CRITICAL: The magic-bytes check must come BEFORE the existing null-byte guard. The current code at line 44 returns `None` for any `.psf` file containing null bytes — if the magic-bytes check is placed after it, it will never run.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_format_detector.py`:

```python
import struct
from pathlib import Path
import pytest
from spec_result_parser.models import Format
from spec_result_parser.format_detector import detect


def test_binary_psf_detected_by_magic(tmp_path):
    # Binary PSF magic: 4-byte big-endian int 0x00000001 at offset 0
    f = tmp_path / "result.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\x00" * 100)
    assert detect(f) == Format.PSF_BINARY


def test_ascii_psf_still_detected(tmp_path):
    f = tmp_path / "result.psf"
    f.write_text('HEADER\n"simulator" "spectre"\n')
    assert detect(f) == Format.PSF_ASCII


def test_binary_psf_wrong_magic_returns_none(tmp_path):
    # Has null bytes but wrong magic — not a known binary PSF
    f = tmp_path / "result.psf"
    f.write_bytes(b"\xDE\xAD\xBE\xEF" + b"\x00" * 100)
    assert detect(f) is None
```

- [ ] **Step 2: Run to confirm fail**

```bash
python -m pytest tests/test_format_detector.py::test_binary_psf_detected_by_magic -v
```
Expected: `FAILED` — returns `None` instead of `Format.PSF_BINARY`.

- [ ] **Step 3: Implement changes in format_detector.py**

Replace the PSF-ASCII header sniff block with:

```python
_PSF_BINARY_MAGIC = struct.pack(">I", 1)   # 0x00 0x00 0x00 0x01

# Header sniff for PSF files
if fmt == Format.PSF_ASCII:
    raw = path.read_bytes()
    header = raw[:_PSF_BINARY_CHECK_BYTES]
    # Check magic bytes FIRST — binary PSF starts with 0x00000001
    if header[:4] == _PSF_BINARY_MAGIC:
        return Format.PSF_BINARY
    # Reject other binary files
    if b"\x00" in header:
        return None
```

Add `import struct` at the top of the file.

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_format_detector.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec_result_parser/format_detector.py tests/test_format_detector.py
git commit -m "feat: detect binary PSF magic bytes in format_detector"
```

---

## Task 3: Extend spec_loader.py — measure: field

**Files:**
- Modify: `src/spec_result_parser/spec_loader.py`
- Modify: `tests/test_spec_loader.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_spec_loader.py`:

```python
def test_yaml_measure_field_loaded(tmp_path):
    spec_file = tmp_path / "opamp.yaml"
    spec_file.write_text("""
specs:
  ugbw:
    min: 10.0e6
    max: null
    unit: Hz
    measure: "cross(vout_db, 0)"
""")
    targets = load_spec(spec_file)
    assert targets["ugbw"].measure == "cross(vout_db, 0)"


def test_yaml_measure_defaults_none(tmp_path):
    spec_file = tmp_path / "opamp.yaml"
    spec_file.write_text("""
specs:
  gain_dc: { min: 60, max: null, unit: dB }
""")
    targets = load_spec(spec_file)
    assert targets["gain_dc"].measure is None


def test_csv_measure_raises_config_error(tmp_path):
    from spec_result_parser.models import ConfigError
    spec_file = tmp_path / "opamp.csv"
    spec_file.write_text("measurement,min,max,unit,measure\ngain_dc,60,,dB,max(vout)\n")
    with pytest.raises(ConfigError, match="'measure:' is only supported in YAML spec files"):
        load_spec(spec_file)
```

- [ ] **Step 2: Run to confirm fail**

```bash
python -m pytest tests/test_spec_loader.py::test_yaml_measure_field_loaded -v
```
Expected: `FAILED` — `SpecTarget` has no `measure` attribute (or it's None when we expect the value).

- [ ] **Step 3: Implement changes in spec_loader.py**

In `_load_yaml`, update the `SpecTarget` construction:

```python
targets[name] = SpecTarget(
    name=name,
    min_val=_parse_float_or_none(entry.get("min")),
    max_val=_parse_float_or_none(entry.get("max")),
    unit=entry.get("unit"),
    measure=entry.get("measure") or None,
)
```

In `_load_csv`, add a check after headers validation:

```python
if "measure" in headers:
    raise ConfigError("'measure:' is only supported in YAML spec files")
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_spec_loader.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec_result_parser/spec_loader.py tests/test_spec_loader.py
git commit -m "feat: load measure: expression from YAML spec; reject in CSV"
```

---

## Task 4: Binary PSF parser

**Files:**
- Create: `src/spec_result_parser/parsers/psf_binary.py`
- Create: `tests/test_psf_binary.py`

- [ ] **Step 1: Add libpsf to pyproject.toml**

In `pyproject.toml`, add to `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]
binary = [
    "libpsf>=0.1",
]
```

Also add `numpy>=1.21` to `[project.dependencies]`.

```bash
# Install numpy for development
pip install numpy
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_psf_binary.py`:

```python
"""Tests for binary PSF parser."""
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from spec_result_parser.models import Format, Measurement, ParseError, Waveform


def test_libpsf_absent_raises_parse_error(tmp_path):
    """When libpsf is not installed, raise ParseError with install hint."""
    f = tmp_path / "result.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\x00" * 10)

    with patch.dict("sys.modules", {"libpsf": None}):
        from importlib import import_module
        import sys
        # Remove cached module if present
        sys.modules.pop("spec_result_parser.parsers.psf_binary", None)
        from spec_result_parser.parsers.psf_binary import parse
        with pytest.raises(ParseError, match="pip install spec-result-parser\\[binary\\]"):
            parse(f)


def test_parse_scalar_returns_measurement(tmp_path):
    """Scalar-only PSF file returns dict of Measurement objects."""
    f = tmp_path / "result.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\x00" * 10)

    mock_psf = MagicMock()
    mock_psf.get_signal_names.return_value = ["gain_dc"]
    mock_psf.get_signal.return_value = MagicMock(
        is_swept=False, value=68.5, units="dB"
    )

    with patch("spec_result_parser.parsers.psf_binary._load_libpsf", return_value=mock_psf):
        from spec_result_parser.parsers.psf_binary import parse
        result = parse(f)

    assert "gain_dc" in result
    assert isinstance(result["gain_dc"], Measurement)
    assert result["gain_dc"].value == 68.5
    assert result["gain_dc"].unit == "dB"
    assert result["gain_dc"].fmt == Format.PSF_BINARY


def test_parse_waveform_returns_waveform(tmp_path):
    """Swept signal returns Waveform object."""
    f = tmp_path / "result.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\x00" * 10)

    mock_signal = MagicMock()
    mock_signal.is_swept = True
    mock_signal.sweep_param = "freq"
    mock_signal.abscissa = np.array([1e6, 2e6, 3e6])
    mock_signal.ordinate = np.array([0.5, 0.3, 0.1])
    mock_signal.units = "V"

    mock_psf = MagicMock()
    mock_psf.get_signal_names.return_value = ["vout"]
    mock_psf.get_signal.return_value = mock_signal

    with patch("spec_result_parser.parsers.psf_binary._load_libpsf", return_value=mock_psf):
        from spec_result_parser.parsers.psf_binary import parse
        result = parse(f)

    assert "vout" in result
    w = result["vout"]
    assert isinstance(w, Waveform)
    assert w.sweep_var == "freq"
    np.testing.assert_array_equal(w.x, [1e6, 2e6, 3e6])
    assert w.unit == "V"


def test_parse_missing_file_raises():
    with pytest.raises((FileNotFoundError, ParseError)):
        from spec_result_parser.parsers.psf_binary import parse
        parse("/nonexistent/path.psf")


def test_parse_corrupt_file_raises(tmp_path):
    f = tmp_path / "bad.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\xff\xfe\xfd")

    mock_psf_module = MagicMock()
    mock_psf_module.PSFDataSet.side_effect = Exception("corrupt data")

    with patch.dict("sys.modules", {"libpsf": mock_psf_module}):
        import sys
        sys.modules.pop("spec_result_parser.parsers.psf_binary", None)
        from spec_result_parser.parsers.psf_binary import parse
        with pytest.raises(ParseError, match="Cannot parse binary PSF"):
            parse(f)
```

- [ ] **Step 3: Run to confirm fail**

```bash
python -m pytest tests/test_psf_binary.py -v
```
Expected: `ERROR` — module `spec_result_parser.parsers.psf_binary` does not exist.

- [ ] **Step 4: Implement psf_binary.py**

Create `src/spec_result_parser/parsers/psf_binary.py`:

```python
"""Binary PSF parser using libpsf.

Requires: pip install spec-result-parser[binary]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Union

import numpy as np

from spec_result_parser.models import Format, Measurement, ParseError, Waveform


def _load_libpsf(path: Path):
    """Load a PSF dataset via libpsf. Separated for test mocking."""
    try:
        import libpsf  # type: ignore[import]
    except ImportError:
        raise ParseError(
            "Binary PSF requires the 'binary' extra: "
            "pip install spec-result-parser[binary]"
        )
    try:
        return libpsf.PSFDataSet(str(path))
    except Exception as exc:
        raise ParseError(f"Cannot parse binary PSF file: {path.name} — {exc}") from exc


def parse(path: Union[str, Path]) -> Dict[str, Union[Measurement, Waveform]]:
    """Parse a Cadence Spectre binary PSF file.

    Returns:
        Dict mapping signal name → Measurement (scalar) or Waveform (swept).

    Raises:
        ParseError: If libpsf is not installed or file cannot be parsed.
        FileNotFoundError: If file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    dataset = _load_libpsf(path)

    result: Dict[str, Union[Measurement, Waveform]] = {}
    for name in dataset.get_signal_names():
        sig = dataset.get_signal(name)
        if sig.is_swept:
            result[name] = Waveform(
                sweep_var=sig.sweep_param,
                x=np.asarray(sig.abscissa, dtype=float),
                y=np.asarray(sig.ordinate, dtype=float),
                unit=sig.units or None,
                fmt=Format.PSF_BINARY,
            )
        else:
            result[name] = Measurement(
                name=name,
                value=float(sig.value),
                unit=sig.units or None,
                fmt=Format.PSF_BINARY,
            )

    return result
```

- [ ] **Step 5: Run tests to confirm pass**

```bash
python -m pytest tests/test_psf_binary.py -v
```
Expected: all pass (libpsf-absent test mocks the import, others mock `_load_libpsf`).

- [ ] **Step 6: Commit**

```bash
git add src/spec_result_parser/parsers/psf_binary.py tests/test_psf_binary.py pyproject.toml
git commit -m "feat: add binary PSF parser using libpsf (optional extra)"
```

---

## Task 5: Expression evaluator

**Files:**
- Create: `src/spec_result_parser/evaluator.py`
- Create: `tests/test_evaluator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_evaluator.py`:

```python
"""Tests for expression evaluator."""
import numpy as np
import pytest

from spec_result_parser.models import Format, Measurement, ParseError, SpecTarget, Waveform
from spec_result_parser.evaluator import ExpressionEvaluator


def _make_waveform(x, y, name="vout"):
    return Waveform(
        sweep_var="freq",
        x=np.array(x, dtype=float),
        y=np.array(y, dtype=float),
        unit="V",
        fmt=Format.PSF_BINARY,
    )


def _make_target(name, measure):
    return SpecTarget(name=name, min_val=None, max_val=None, unit="V", measure=measure)


def test_max_function():
    w = _make_waveform([1, 2, 3], [0.5, 1.2, 0.8])
    t = _make_target("peak", "max(vout)")
    signals = {"vout": w}
    result = ExpressionEvaluator.evaluate(t, signals)
    assert result.value == pytest.approx(1.2)


def test_min_function():
    w = _make_waveform([1, 2, 3], [0.5, 1.2, 0.3])
    t = _make_target("trough", "min(vout)")
    result = ExpressionEvaluator.evaluate(t, {"vout": w})
    assert result.value == pytest.approx(0.3)


def test_at_function():
    w = _make_waveform([1.0, 2.0, 3.0], [0.5, 1.2, 0.8])
    t = _make_target("val_at_2", "at(vout, 2.0)")
    result = ExpressionEvaluator.evaluate(t, {"vout": w})
    assert result.value == pytest.approx(1.2)


def test_cross_function_rising():
    w = _make_waveform([1e6, 2e6, 3e6], [-10.0, 0.0, 10.0])
    t = _make_target("ugbw", "cross(vout, 0)")
    result = ExpressionEvaluator.evaluate(t, {"vout": w})
    assert result.value == pytest.approx(2e6)


def test_phase_margin():
    # Gain signal that crosses 0 dB at index 1 (freq=2e6)
    # Phase at that point is -135 deg → PM = 45 deg
    gain_w = _make_waveform([1e6, 2e6, 3e6], [10.0, 0.0, -10.0])
    phase_w = Waveform(sweep_var="freq", x=np.array([1e6, 2e6, 3e6]),
                       y=np.array([-90.0, -135.0, -180.0]), unit="deg",
                       fmt=Format.PSF_BINARY)
    t = _make_target("pm", "phase_margin(gain, phase)")
    result = ExpressionEvaluator.evaluate(t, {"gain": gain_w, "phase": phase_w})
    assert result.value == pytest.approx(45.0, abs=1.0)


def test_scalar_passthrough():
    """If spec.measure is None, evaluate() returns None (caller handles it)."""
    t = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
    result = ExpressionEvaluator.evaluate(t, {})
    assert result is None


def test_missing_signal_raises():
    t = _make_target("peak", "max(vout)")
    with pytest.raises(ParseError, match="Signal 'vout' not found"):
        ExpressionEvaluator.evaluate(t, {})


def test_bad_expression_raises():
    w = _make_waveform([1, 2], [0.5, 1.0])
    t = _make_target("bad", "unknown_fn(vout)")
    with pytest.raises(ParseError, match="Invalid expression"):
        ExpressionEvaluator.evaluate(t, {"vout": w})
```

- [ ] **Step 2: Run to confirm fail**

```bash
python -m pytest tests/test_evaluator.py -v
```
Expected: `ERROR` — module does not exist.

- [ ] **Step 3: Implement evaluator.py**

Create `src/spec_result_parser/evaluator.py`:

```python
"""Expression evaluator for waveform-based spec measurements.

Evaluates expressions like "max(vout)", "cross(vout_db, 0)", "phase_margin(gain, phase)"
against parsed Waveform objects to produce scalar Measurement values.

Security: expressions are parsed as a controlled AST, never passed to eval().
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Union

import numpy as np

from spec_result_parser.models import Format, Measurement, ParseError, SpecTarget, Waveform

# Supported functions and their arity
_FUNCTIONS = {
    "max": 1,
    "min": 1,
    "at": 2,
    "cross": 2,
    "phase_margin": 2,
}

_CALL_RE = re.compile(
    r"^(\w+)\(([^)]+)\)$"
)


def _parse_expression(expr: str) -> tuple[str, list[str]]:
    """Parse 'func(arg1, arg2)' → (func_name, [arg1, arg2]).

    Raises ParseError on unrecognised function or wrong arity.
    """
    m = _CALL_RE.match(expr.strip())
    if not m:
        raise ParseError(f"Invalid expression '{expr}': expected func(args)")
    func = m.group(1)
    raw_args = [a.strip() for a in m.group(2).split(",")]
    if func not in _FUNCTIONS:
        raise ParseError(
            f"Invalid expression '{expr}': unknown function '{func}'. "
            f"Supported: {sorted(_FUNCTIONS)}"
        )
    expected = _FUNCTIONS[func]
    if len(raw_args) != expected:
        raise ParseError(
            f"Invalid expression '{expr}': '{func}' takes {expected} argument(s), "
            f"got {len(raw_args)}"
        )
    return func, raw_args


def _resolve_signal(name: str, signals: Dict[str, Waveform]) -> Waveform:
    if name not in signals:
        raise ParseError(f"Signal '{name}' not found in result file")
    sig = signals[name]
    if not isinstance(sig, Waveform):
        raise ParseError(f"Signal '{name}' is a scalar, not a waveform")
    return sig


def _eval_max(sig: Waveform) -> float:
    return float(np.max(sig.y))


def _eval_min(sig: Waveform) -> float:
    return float(np.min(sig.y))


def _eval_at(sig: Waveform, x_val: float) -> float:
    idx = int(np.argmin(np.abs(sig.x - x_val)))
    return float(sig.y[idx])


def _eval_cross(sig: Waveform, level: float) -> float:
    """Return x value at first rising zero-crossing of (y - level)."""
    y = sig.y - level
    for i in range(len(y) - 1):
        if y[i] <= 0 and y[i + 1] > 0:
            # Linear interpolation
            frac = -y[i] / (y[i + 1] - y[i])
            return float(sig.x[i] + frac * (sig.x[i + 1] - sig.x[i]))
    raise ParseError(f"cross(): signal never crosses level {level}")


def _eval_phase_margin(gain: Waveform, phase: Waveform) -> float:
    """Phase margin = 180 + phase at unity-gain (0 dB) crossing."""
    # Find index where gain crosses 0 dB (falling)
    for i in range(len(gain.y) - 1):
        if gain.y[i] >= 0 and gain.y[i + 1] < 0:
            frac = gain.y[i] / (gain.y[i] - gain.y[i + 1])
            x_cross = gain.x[i] + frac * (gain.x[i + 1] - gain.x[i])
            phase_at_cross = float(np.interp(x_cross, phase.x, phase.y))
            return float(180.0 + phase_at_cross)
    raise ParseError("phase_margin(): gain never crosses 0 dB")


class ExpressionEvaluator:
    """Evaluate a spec measure: expression against waveform signals."""

    @classmethod
    def evaluate(
        cls,
        spec: SpecTarget,
        signals: Dict[str, Union[Measurement, Waveform]],
    ) -> Optional[Measurement]:
        """Evaluate spec.measure expression against signal dict.

        Returns:
            Measurement with computed scalar value, or None if spec.measure is None.

        Raises:
            ParseError: If expression is invalid, signal missing, or computation fails.
        """
        if spec.measure is None:
            return None

        waveforms = {k: v for k, v in signals.items() if isinstance(v, Waveform)}

        func, args = _parse_expression(spec.measure)

        if func == "max":
            sig = _resolve_signal(args[0], waveforms)
            value = _eval_max(sig)
        elif func == "min":
            sig = _resolve_signal(args[0], waveforms)
            value = _eval_min(sig)
        elif func == "at":
            sig = _resolve_signal(args[0], waveforms)
            value = _eval_at(sig, float(args[1]))
        elif func == "cross":
            sig = _resolve_signal(args[0], waveforms)
            value = _eval_cross(sig, float(args[1]))
        elif func == "phase_margin":
            gain = _resolve_signal(args[0], waveforms)
            phase = _resolve_signal(args[1], waveforms)
            value = _eval_phase_margin(gain, phase)
        else:
            raise ParseError(f"Invalid expression '{spec.measure}': unknown function '{func}'")

        return Measurement(
            name=spec.name,
            value=value,
            unit=spec.unit,
            fmt=Format.PSF_BINARY,
        )
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_evaluator.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec_result_parser/evaluator.py tests/test_evaluator.py
git commit -m "feat: add expression evaluator for waveform-based spec measurements"
```

---

## Task 6: CSV exporter

**Files:**
- Create: `src/spec_result_parser/exporters/__init__.py`
- Create: `src/spec_result_parser/exporters/csv_exporter.py`
- Create: `tests/test_csv_exporter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_csv_exporter.py`:

```python
"""Tests for CSV exporter."""
import csv
import io
from spec_result_parser.models import (
    Corner, Format, Measurement, SpecCheck, SpecTarget, Status
)
from spec_result_parser.exporters.csv_exporter import export_single, export_corners


def _make_check(name, value, status, margin_pct=None, min_val=None, max_val=None):
    m = Measurement(name=name, value=value, unit="dB", fmt=Format.PSF_ASCII)
    spec = SpecTarget(name=name, min_val=min_val, max_val=max_val, unit="dB")
    return SpecCheck(measurement=m, spec=spec, status=status, margin_pct=margin_pct)


def test_export_single_check_mode():
    checks = [
        _make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0),
        _make_check("pm", 42.0, Status.FAIL, min_val=45.0),
    ]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    rows = list(csv.DictReader(buf))
    assert len(rows) == 2
    assert rows[0]["spec"] == "gain_dc"
    assert rows[0]["status"] == "PASS"
    assert rows[0]["margin_pct"] == "14.2"
    assert rows[1]["status"] == "FAIL"


def test_export_single_all_columns_present():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=10.0, min_val=60.0)]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    reader = csv.DictReader(buf)
    assert set(reader.fieldnames) == {"spec", "value", "unit", "min", "max", "status", "margin_pct"}


def test_export_corners_aggregate_mode():
    checks1 = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    checks2 = [_make_check("gain_dc", 55.0, Status.FAIL, min_val=60.0)]
    corners = [Corner(name="tt_27", checks=checks1), Corner(name="ss_125", checks=checks2)]
    buf = io.StringIO()
    export_corners(corners, buf)
    buf.seek(0)
    rows = list(csv.DictReader(buf))
    assert len(rows) == 2
    assert rows[0]["corner"] == "tt_27"
    assert rows[0]["overall"] == "PASS"
    assert rows[1]["corner"] == "ss_125"
    assert rows[1]["overall"] == "FAIL"
```

- [ ] **Step 2: Run to confirm fail**

```bash
python -m pytest tests/test_csv_exporter.py -v
```
Expected: `ERROR` — module does not exist.

- [ ] **Step 3: Implement**

Create `src/spec_result_parser/exporters/__init__.py` (empty).

Create `src/spec_result_parser/exporters/csv_exporter.py`:

```python
"""CSV exporter for spec check results."""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from typing import List, Optional, Union

from spec_result_parser.models import Corner, SpecCheck


_SINGLE_FIELDS = ["spec", "value", "unit", "min", "max", "status", "margin_pct"]
_CORNER_FIELDS = ["corner", "overall"] + []  # spec columns added dynamically


def export_single(
    checks: List[SpecCheck],
    dest: Union[str, Path, io.IOBase, None] = None,
) -> None:
    """Write single-file check results to CSV.

    Args:
        checks: List of SpecCheck results.
        dest: File path, open file object, or None for stdout.
    """
    _write_single(checks, dest)


def export_corners(
    corners: List[Corner],
    dest: Union[str, Path, io.IOBase, None] = None,
) -> None:
    """Write corner aggregation results to CSV.

    Args:
        corners: List of Corner objects.
        dest: File path, open file object, or None for stdout.
    """
    _write_corners(corners, dest)


def _write_single(checks: List[SpecCheck], dest) -> None:
    def _rows():
        for ch in checks:
            m = ch.measurement
            spec = ch.spec
            yield {
                "spec": m.name,
                "value": m.value,
                "unit": m.unit or "",
                "min": spec.min_val if spec else "",
                "max": spec.max_val if spec else "",
                "status": ch.status.value,
                "margin_pct": f"{ch.margin_pct:.1f}" if ch.margin_pct is not None else "",
            }

    _write_csv(_SINGLE_FIELDS, list(_rows()), dest)


def _write_corners(corners: List[Corner], dest) -> None:
    if not corners:
        return
    spec_names = [ch.measurement.name for ch in corners[0].checks]
    fields = ["corner", "overall"] + spec_names

    rows = []
    for corner in corners:
        checks_by_name = {ch.measurement.name: ch for ch in corner.checks}
        row = {"corner": corner.name, "overall": corner.overall_status.value}
        for name in spec_names:
            ch = checks_by_name.get(name)
            row[name] = ch.status.value if ch else "N/A"
        rows.append(row)

    _write_csv(fields, rows, dest)


def _write_csv(fields: List[str], rows: List[dict], dest) -> None:
    if dest is None or dest is sys.stdout:
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    elif hasattr(dest, "write"):
        writer = csv.DictWriter(dest, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    else:
        with open(dest, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_csv_exporter.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec_result_parser/exporters/ tests/test_csv_exporter.py
git commit -m "feat: add CSV exporter for check and aggregate modes"
```

---

## Task 7: JSON exporter

**Files:**
- Create: `src/spec_result_parser/exporters/json_exporter.py`
- Create: `tests/test_json_exporter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_json_exporter.py`:

```python
"""Tests for JSON exporter."""
import io
import json
from spec_result_parser.models import (
    Corner, Format, Measurement, SpecCheck, SpecTarget, Status
)
from spec_result_parser.exporters.json_exporter import export_single, export_corners


def _make_check(name, value, status, margin_pct=None, min_val=None):
    m = Measurement(name=name, value=value, unit="dB", fmt=Format.PSF_ASCII)
    spec = SpecTarget(name=name, min_val=min_val, max_val=None, unit="dB")
    return SpecCheck(measurement=m, spec=spec, status=status, margin_pct=margin_pct)


def test_export_single_schema():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    buf = io.StringIO()
    export_single(checks, buf, spec_file="opamp.yaml", result_file="result.psf", version="0.2.0")
    buf.seek(0)
    data = json.load(buf)
    assert "meta" in data
    assert data["meta"]["tool"] == "spec-result-parser"
    assert data["meta"]["version"] == "0.2.0"
    assert data["meta"]["spec_file"] == "opamp.yaml"
    assert data["meta"]["result_file"] == "result.psf"
    assert "timestamp" in data["meta"]
    assert "summary" in data
    assert data["summary"]["total"] == 1
    assert data["summary"]["pass"] == 1
    assert data["summary"]["fail"] == 0
    assert "results" in data
    assert "corners" not in data


def test_export_single_result_fields():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    data = json.load(buf)
    r = data["results"][0]
    assert r["spec"] == "gain_dc"
    assert r["value"] == 68.5
    assert r["status"] == "PASS"
    assert r["margin_pct"] == pytest.approx(14.2)


def test_export_corners_has_corners_key():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    corners = [Corner(name="tt_27", checks=checks)]
    buf = io.StringIO()
    export_corners(corners, buf)
    buf.seek(0)
    data = json.load(buf)
    assert "corners" in data
    assert data["corners"][0]["name"] == "tt_27"
    assert data["corners"][0]["overall"] == "PASS"


def test_export_summary_overall_fail():
    checks = [
        _make_check("gain_dc", 68.5, Status.PASS, min_val=60.0),
        _make_check("pm", 42.0, Status.FAIL, min_val=45.0),
    ]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    data = json.load(buf)
    assert data["summary"]["overall"] == "FAIL"
    assert data["summary"]["fail"] == 1
```

Add `import pytest` at top of test file.

- [ ] **Step 2: Run to confirm fail**

```bash
python -m pytest tests/test_json_exporter.py -v
```
Expected: `ERROR` — module does not exist.

- [ ] **Step 3: Implement json_exporter.py**

Create `src/spec_result_parser/exporters/json_exporter.py`:

```python
"""JSON exporter for spec check results."""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from typing import List, Optional, Union
from pathlib import Path

from spec_result_parser.models import Corner, SpecCheck, Status

try:
    from importlib.metadata import version as _pkg_version
    _VERSION = _pkg_version("spec-result-parser")
except Exception:
    _VERSION = "unknown"


def _build_single_payload(
    checks: List[SpecCheck],
    spec_file: str = "",
    result_file: str = "",
    version: str = _VERSION,
) -> dict:
    total = len(checks)
    pass_n = sum(1 for c in checks if c.status == Status.PASS)
    fail_n = sum(1 for c in checks if c.status == Status.FAIL)
    margin_n = sum(1 for c in checks if c.status == Status.MARGIN)
    overall = "FAIL" if fail_n else ("MARGIN" if margin_n else "PASS")

    return {
        "meta": {
            "tool": "spec-result-parser",
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spec_file": spec_file,
            "result_file": result_file,
        },
        "summary": {
            "total": total,
            "pass": pass_n,
            "fail": fail_n,
            "margin": margin_n,
            "overall": overall,
        },
        "results": [_check_to_dict(c) for c in checks],
    }


def _check_to_dict(c: SpecCheck) -> dict:
    m = c.measurement
    spec = c.spec
    return {
        "spec": m.name,
        "value": m.value,
        "unit": m.unit,
        "min": spec.min_val if spec else None,
        "max": spec.max_val if spec else None,
        "status": c.status.value,
        "margin_pct": c.margin_pct,
    }


def export_single(
    checks: List[SpecCheck],
    dest=None,
    spec_file: str = "",
    result_file: str = "",
    version: str = _VERSION,
) -> None:
    payload = _build_single_payload(checks, spec_file, result_file, version)
    _write_json(payload, dest)


def export_corners(
    corners: List[Corner],
    dest=None,
    spec_file: str = "",
    result_folder: str = "",
    version: str = _VERSION,
) -> None:
    all_checks = [ch for c in corners for ch in c.checks]
    payload = _build_single_payload(all_checks, spec_file=spec_file, result_file=result_folder, version=version)
    payload["corners"] = [
        {
            "name": c.name,
            "overall": c.overall_status.value,
            "results": [_check_to_dict(ch) for ch in c.checks],
        }
        for c in corners
    ]
    _write_json(payload, dest)


def _write_json(payload: dict, dest) -> None:
    text = json.dumps(payload, indent=2, default=str)
    if dest is None:
        print(text)
    elif hasattr(dest, "write"):
        dest.write(text)
    else:
        Path(dest).write_text(text, encoding="utf-8")
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_json_exporter.py -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec_result_parser/exporters/json_exporter.py tests/test_json_exporter.py
git commit -m "feat: add JSON exporter with full metadata schema"
```

---

## Task 8: HTML exporter + vendor Chart.js

**Files:**
- Create: `src/spec_result_parser/exporters/_vendor/chart.min.js` (download)
- Create: `src/spec_result_parser/exporters/html_exporter.py`
- Create: `tests/test_html_exporter.py`

- [ ] **Step 1: Download and vendor Chart.js 4.4.4**

```bash
mkdir -p src/spec_result_parser/exporters/_vendor
curl -fsSL "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js" \
     -o src/spec_result_parser/exporters/_vendor/chart.min.js
# Verify it's not empty
wc -c src/spec_result_parser/exporters/_vendor/chart.min.js
```

- [ ] Create `src/spec_result_parser/exporters/_vendor/__init__.py` (empty — required for `importlib.resources.files()` to resolve the package):

```bash
touch src/spec_result_parser/exporters/_vendor/__init__.py
```

Add `_vendor` to `pyproject.toml` wheel sources if needed (hatchling includes all files by default).

- [ ] **Step 2: Write failing tests**

Create `tests/test_html_exporter.py`:

```python
"""Tests for HTML exporter."""
from pathlib import Path
from spec_result_parser.models import (
    Corner, Format, Measurement, SpecCheck, SpecTarget, Status
)
from spec_result_parser.exporters.html_exporter import export_single, export_corners


def _make_check(name, value, status, margin_pct=None, min_val=None):
    m = Measurement(name=name, value=value, unit="dB", fmt=Format.PSF_ASCII)
    spec = SpecTarget(name=name, min_val=min_val, max_val=None, unit="dB")
    return SpecCheck(measurement=m, spec=spec, status=status, margin_pct=margin_pct)


def test_export_single_creates_file(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    out = tmp_path / "report.html"
    export_single(checks, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_html_contains_summary_cards(tmp_path):
    checks = [
        _make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0),
        _make_check("pm", 42.0, Status.FAIL, min_val=45.0),
    ]
    out = tmp_path / "report.html"
    export_single(checks, out)
    html = out.read_text()
    assert "PASS" in html
    assert "FAIL" in html
    assert "gain_dc" in html


def test_html_contains_table(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    out = tmp_path / "report.html"
    export_single(checks, out)
    html = out.read_text()
    assert "<table" in html.lower()


def test_html_inlines_chartjs(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    out = tmp_path / "report.html"
    export_single(checks, out)
    html = out.read_text()
    # Chart.js should be inlined, not loaded from CDN
    assert "cdn.jsdelivr.net" not in html
    assert "Chart" in html


def test_export_corners_creates_file(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    corners = [Corner(name="tt_27", checks=checks)]
    out = tmp_path / "report.html"
    export_corners(corners, out)
    html = out.read_text()
    assert "tt_27" in html
```

- [ ] **Step 3: Run to confirm fail**

```bash
python -m pytest tests/test_html_exporter.py -v
```
Expected: `ERROR` — module does not exist.

- [ ] **Step 4: Implement html_exporter.py**

Create `src/spec_result_parser/exporters/html_exporter.py`:

```python
"""HTML dashboard exporter — produces a single self-contained HTML file."""
from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from typing import List, Union

from spec_result_parser.models import Corner, SpecCheck, Status

_STATUS_COLOR = {
    "PASS":   "#22c55e",
    "FAIL":   "#ef4444",
    "MARGIN": "#eab308",
    "N/A":    "#6b7280",
}


def _load_chartjs() -> str:
    try:
        ref = importlib.resources.files("spec_result_parser.exporters._vendor").joinpath("chart.min.js")
        return ref.read_text(encoding="utf-8")
    except Exception:
        return "/* Chart.js not found */"


def _checks_to_rows(checks: List[SpecCheck]) -> list:
    rows = []
    for ch in checks:
        m = ch.measurement
        spec = ch.spec
        rows.append({
            "spec": m.name,
            "value": f"{m.value:.4g} {m.unit or ''}".strip(),
            "min": f"{spec.min_val}" if spec and spec.min_val is not None else "—",
            "max": f"{spec.max_val}" if spec and spec.max_val is not None else "—",
            "status": ch.status.value,
            "margin": f"{ch.margin_pct:+.1f}%" if ch.margin_pct is not None else "—",
            "color": _STATUS_COLOR.get(ch.status.value, "#ffffff"),
        })
    return rows


def _render(title: str, summary: dict, rows: list, chart_data: dict, chartjs: str) -> str:
    rows_json = json.dumps(rows)
    chart_json = json.dumps(chart_data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:2rem; }}
  h1 {{ font-size:1.5rem; margin-bottom:1.5rem; }}
  .cards {{ display:flex; gap:1rem; margin-bottom:2rem; flex-wrap:wrap; }}
  .card {{ background:#1e293b; border-radius:8px; padding:1rem 1.5rem; min-width:120px; text-align:center; }}
  .card .num {{ font-size:2rem; font-weight:700; }}
  .card .lbl {{ font-size:0.8rem; color:#94a3b8; margin-top:4px; }}
  .pass {{ color:#22c55e; }} .fail {{ color:#ef4444; }} .margin {{ color:#eab308; }}
  .chart-wrap {{ background:#1e293b; border-radius:8px; padding:1rem; margin-bottom:2rem; max-width:900px; }}
  table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; }}
  th {{ background:#334155; padding:0.6rem 1rem; text-align:left; font-size:0.85rem; color:#94a3b8; }}
  td {{ padding:0.6rem 1rem; font-size:0.9rem; border-top:1px solid #334155; }}
  .filter {{ margin-bottom:1rem; }}
  select {{ background:#1e293b; color:#e2e8f0; border:1px solid #475569; border-radius:4px; padding:4px 8px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="cards">
  <div class="card"><div class="num">{summary['total']}</div><div class="lbl">Total</div></div>
  <div class="card"><div class="num pass">{summary['pass']}</div><div class="lbl">PASS</div></div>
  <div class="card"><div class="num fail">{summary['fail']}</div><div class="lbl">FAIL</div></div>
  <div class="card"><div class="num margin">{summary['margin']}</div><div class="lbl">MARGIN</div></div>
</div>
<div class="chart-wrap"><canvas id="marginChart" height="80"></canvas></div>
<div class="filter">
  Filter: <select id="statusFilter" onchange="filterTable()">
    <option value="ALL">All</option>
    <option value="PASS">PASS</option>
    <option value="FAIL">FAIL</option>
    <option value="MARGIN">MARGIN</option>
  </select>
</div>
<table id="resultsTable">
  <thead><tr><th>Spec</th><th>Value</th><th>Min</th><th>Max</th><th>Status</th><th>Margin</th></tr></thead>
  <tbody id="tbody"></tbody>
</table>
<script>{chartjs}</script>
<script>
const rows = {rows_json};
const chartData = {chart_json};

function renderTable(data) {{
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = data.map(r => `<tr>
    <td>${{r.spec}}</td><td>${{r.value}}</td><td>${{r.min}}</td><td>${{r.max}}</td>
    <td style="color:${{r.color}};font-weight:700">${{r.status}}</td><td>${{r.margin}}</td>
  </tr>`).join('');
}}

function filterTable() {{
  const f = document.getElementById('statusFilter').value;
  renderTable(f === 'ALL' ? rows : rows.filter(r => r.status === f));
}}

renderTable(rows);

new Chart(document.getElementById('marginChart'), {{
  type: 'bar',
  data: {{
    labels: chartData.labels,
    datasets: [{{
      label: 'Margin %',
      data: chartData.values,
      backgroundColor: chartData.colors,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ y: {{ title: {{ display: true, text: 'Margin %', color:'#94a3b8' }}, ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#334155' }} }},
               x: {{ ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#334155' }} }} }},
    responsive: true,
  }}
}});
</script>
</body>
</html>"""


def export_single(
    checks: List[SpecCheck],
    dest: Union[str, Path],
    title: str = "Spec Check Report",
) -> None:
    """Write single-file check result as HTML dashboard."""
    rows = _checks_to_rows(checks)
    summary = {
        "total": len(checks),
        "pass": sum(1 for c in checks if c.status == Status.PASS),
        "fail": sum(1 for c in checks if c.status == Status.FAIL),
        "margin": sum(1 for c in checks if c.status == Status.MARGIN),
    }
    chart_data = {
        "labels": [r["spec"] for r in rows],
        "values": [float(r["margin"].rstrip("%")) if r["margin"] != "—" else 0 for r in rows],
        "colors": [r["color"] for r in rows],
    }
    html = _render(title, summary, rows, chart_data, _load_chartjs())
    Path(dest).write_text(html, encoding="utf-8")


def export_corners(
    corners: List[Corner],
    dest: Union[str, Path],
    title: str = "Corner Aggregation Report",
) -> None:
    """Write corner aggregation result as HTML dashboard."""
    all_checks = [ch for c in corners for ch in c.checks]
    export_single(all_checks, dest, title=title)
```

- [ ] **Step 5: Run tests to confirm pass**

```bash
python -m pytest tests/test_html_exporter.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/spec_result_parser/exporters/html_exporter.py \
        src/spec_result_parser/exporters/_vendor/ \
        tests/test_html_exporter.py
git commit -m "feat: add HTML dashboard exporter with vendored Chart.js 4.4.4"
```

---

## Task 9: Extend CLI — --format, --output, --quiet flags

**Files:**
- Modify: `src/spec_result_parser/cli.py`
- Create: `tests/test_cli_output.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_output.py`:

```python
"""Tests for --format, --output, --quiet CLI flags."""
import json
import csv
from pathlib import Path
from click.testing import CliRunner
from spec_result_parser.cli import main


def _write_psf(tmp_path):
    """Write a minimal PSF-ASCII file."""
    f = tmp_path / "result.psf"
    f.write_text('HEADER\n"simulator" "spectre"\nVALUE\n"gain_dc" 68.5\nEND\n')
    return f


def _write_spec(tmp_path):
    f = tmp_path / "opamp.yaml"
    f.write_text("specs:\n  gain_dc: { min: 60, max: null, unit: dB }\n")
    return f


def test_format_json_to_stdout(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--format", "json"
    ])
    assert result.exit_code == 0
    # stdout should contain valid JSON somewhere
    # (terminal output may precede it — find the JSON block)
    out = result.output
    start = out.find("{")
    assert start != -1
    data = json.loads(out[start:])
    assert "results" in data


def test_format_csv_to_file(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    out_file = tmp_path / "report.csv"
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file),
        "--format", "csv", "--output", str(out_file)
    ])
    assert result.exit_code == 0
    assert out_file.exists()
    rows = list(csv.DictReader(out_file.read_text().splitlines()))
    assert rows[0]["spec"] == "gain_dc"


def test_output_auto_detect_json(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--output", str(out_file)
    ])
    assert result.exit_code == 0
    data = json.loads(out_file.read_text())
    assert "results" in data


def test_html_without_output_exits_2(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--format", "html"
    ])
    assert result.exit_code == 2
    assert "HTML output requires --output" in result.output


def test_unknown_extension_exits_2(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--output", "report.xyz"
    ])
    assert result.exit_code == 2
    assert "--format" in result.output


def test_quiet_suppresses_terminal(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file),
        "--format", "json", "--output", str(out_file), "--quiet"
    ])
    assert result.exit_code == 0
    # Terminal (Rich table) should not appear in output
    assert "gain_dc" not in result.output
    # But file should still be written
    assert out_file.exists()


def test_quiet_does_not_affect_exit_code(tmp_path):
    """--quiet never changes exit code."""
    result_file = _write_psf(tmp_path)
    # Spec with failing threshold
    spec_file = tmp_path / "opamp.yaml"
    spec_file.write_text("specs:\n  gain_dc: { min: 80, max: null, unit: dB }\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--quiet"
    ])
    assert result.exit_code == 1   # FAIL, not 0
```

- [ ] **Step 2: Run to confirm fail**

```bash
python -m pytest tests/test_cli_output.py -v
```
Expected: `FAILED` — `main` has no `--format`/`--output`/`--quiet` options.

- [ ] **Step 3: Implement CLI changes**

Replace both `check` and `aggregate` commands in `cli.py`. Key changes:

Add the three new options to `check`:

```python
@main.command()
@click.argument("result_file", type=click.Path(exists=True))
@click.option("--spec", "-s", required=True, type=click.Path(exists=True))
@click.option("--margin-threshold", default=10.0, show_default=True)
@click.option("--verbose", "-v", is_flag=True)
@click.option("--format", "output_format", type=click.Choice(["csv", "json", "html"]), default=None)
@click.option("--output", "output_file", type=click.Path(), default=None)
@click.option("--quiet", is_flag=True, help="Suppress terminal output.")
def check(result_file, spec, margin_threshold, verbose, output_format, output_file, quiet):
    ...
```

Add a `_resolve_format` helper at module level:

```python
_EXT_FORMAT = {".csv": "csv", ".json": "json", ".html": "html"}

def _resolve_format(output_format, output_file):
    """Return (fmt, path) or raise ConfigError."""
    if output_format is None and output_file is None:
        return None, None
    if output_format is None and output_file is not None:
        ext = Path(output_file).suffix.lower()
        fmt = _EXT_FORMAT.get(ext)
        if fmt is None:
            raise ConfigError(
                f"Cannot detect format from '{ext}'. Use --format [csv|json|html]"
            )
        return fmt, output_file
    if output_format == "html" and output_file is None:
        raise ConfigError("HTML output requires --output <file.html>")
    return output_format, output_file
```

Add export dispatch after `TerminalRenderer.render_single(checks)`:

```python
    # Validate format/output BEFORE parsing (early exit on error)
    try:
        fmt, out_path = _resolve_format(output_format, output_file)
    except ConfigError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    # ... parse and check as before ...

    if not quiet:
        TerminalRenderer.render_single(checks)

    if fmt == "csv":
        from spec_result_parser.exporters.csv_exporter import export_single as csv_export
        csv_export(checks, out_path)
    elif fmt == "json":
        from spec_result_parser.exporters.json_exporter import export_single as json_export
        json_export(checks, out_path, spec_file=spec, result_file=result_file)
    elif fmt == "html":
        from spec_result_parser.exporters.html_exporter import export_single as html_export
        html_export(checks, out_path)
```

Apply the same pattern to the `aggregate` command. For the JSON exporter call in aggregate mode, pass the folder path as `result_folder`:

```python
    elif fmt == "json":
        from spec_result_parser.exporters.json_exporter import export_corners as json_export
        json_export(corner_list, out_path, spec_file=spec, result_folder=folder)
    elif fmt == "csv":
        from spec_result_parser.exporters.csv_exporter import export_corners as csv_export
        csv_export(corner_list, out_path)
    elif fmt == "html":
        from spec_result_parser.exporters.html_exporter import export_corners as html_export
        html_export(corner_list, out_path)
```

Also move `_resolve_format` validation to be the **very first thing** inside the command body (before `load_spec`), so malformed flag combinations exit before any file I/O occurs.

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v --cov=src/spec_result_parser --cov-report=term-missing
```
Expected: all pass, coverage ≥ 80%.

- [ ] **Step 5: Commit**

```bash
git add src/spec_result_parser/cli.py tests/test_cli_output.py
git commit -m "feat: add --format, --output, --quiet flags to check and aggregate commands"
```

---

## Task 10: Wire binary PSF into CLI + integration smoke test

**Files:**
- Modify: `src/spec_result_parser/cli.py` (add PSF_BINARY to `_PARSERS`, evaluator call)
- Modify: `tests/test_cli_output.py` (extend)

- [ ] **Step 1: Wire PSF_BINARY into _PARSERS**

In `cli.py`:

```python
from spec_result_parser.parsers.psf_binary import parse as parse_psf_binary
from spec_result_parser.evaluator import ExpressionEvaluator
from spec_result_parser.models import Format, Waveform

_PARSERS = {
    Format.PSF_ASCII:   parse_psf_ascii,
    Format.HSPICE_MT0:  parse_hspice_mt0,
    Format.PSF_BINARY:  parse_psf_binary,
}
```

After calling the parser in `check`, add evaluator step:

```python
raw = parse_fn(path)

# Normalise: if binary parser returned dict[str, Measurement|Waveform], evaluate expressions
if fmt == Format.PSF_BINARY:
    signals = raw  # dict[str, Measurement|Waveform]
    measurements = []
    for target in spec_targets.values():
        if target.measure is not None:
            m = ExpressionEvaluator.evaluate(target, signals)
            if m is not None:
                measurements.append(m)
        elif target.name in signals:
            sig = signals[target.name]
            if not isinstance(sig, Waveform):
                measurements.append(sig)
else:
    measurements = raw  # List[Measurement] from ascii/mt0 parsers
```

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -v --cov=src/spec_result_parser --cov-report=term-missing
```
Expected: all pass, coverage ≥ 80%.

- [ ] **Step 3: Bump version to 0.2.0**

In `pyproject.toml`:
```toml
version = "0.2.0"
```

- [ ] **Step 4: Final commit**

```bash
git add src/spec_result_parser/cli.py pyproject.toml
git commit -m "feat: wire binary PSF + evaluator into CLI; bump version to 0.2.0"
```

---

## Done

All features implemented. Run full suite one final time:

```bash
python -m pytest tests/ -v --cov=src/spec_result_parser --cov-report=term-missing
```

Then verify CLI end-to-end:

```bash
spec-parser check --help    # should show --format, --output, --quiet
spec-parser aggregate --help
```
