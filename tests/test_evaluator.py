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
