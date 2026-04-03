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


def _parse_expression(expr: str) -> tuple:
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
