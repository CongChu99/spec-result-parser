"""SpecChecker — compares Measurement against SpecTarget and returns SpecCheck.

Logic (for a min-only spec, e.g. gain_dc >= 60 dB):
  - value < min          → FAIL  (margin_pct = (value-min)/min*100, negative)
  - value >= min and
    (value-min)/min*100 < margin_threshold → MARGIN  (close to limit)
  - value >= min and well clear             → PASS

For max-only (e.g. offset_v <= 5mV):
  - value > max          → FAIL  (margin_pct = (max-value)/max*100, negative)
  - value <= max and
    (max-value)/max*100 < margin_threshold → MARGIN
  - well clear                              → PASS

For both bounds: check the worst (most binding) limit.
If spec is None: → NA.
"""
from __future__ import annotations

from typing import Optional

from spec_result_parser.models import Measurement, SpecCheck, SpecTarget, Status

_DEFAULT_MARGIN_THRESHOLD = 10.0  # %


class SpecChecker:
    """Stateless spec checker. All methods are class-level."""

    @classmethod
    def check(
        cls,
        measurement: Measurement,
        spec: Optional[SpecTarget],
        margin_threshold: float = _DEFAULT_MARGIN_THRESHOLD,
    ) -> SpecCheck:
        """Check one measurement against its spec target.

        Args:
            measurement: The simulated value.
            spec: The spec target (min/max bounds). Pass None for NA.
            margin_threshold: % within a limit boundary to flag as MARGIN.

        Returns:
            SpecCheck with status and margin_pct.
        """
        if spec is None:
            return SpecCheck(
                measurement=measurement,
                spec=None,
                status=Status.NA,
                margin_pct=None,
            )

        value = measurement.value
        min_val = spec.min_val
        max_val = spec.max_val

        # Compute worst-case margin from all active limits
        margin_pct, status = cls._evaluate(value, min_val, max_val, margin_threshold)

        return SpecCheck(
            measurement=measurement,
            spec=spec,
            status=status,
            margin_pct=margin_pct,
        )

    @staticmethod
    def _evaluate(
        value: float,
        min_val: Optional[float],
        max_val: Optional[float],
        margin_threshold: float,
    ) -> tuple[float, Status]:
        """Return (margin_pct, Status) for a scalar value against bounds."""

        best_margin: Optional[float] = None  # most binding (smallest positive)
        failed = False

        if min_val is not None:
            # margin_pct from min: positive = clear, negative = violation
            pct = (value - min_val) / abs(min_val) * 100 if min_val != 0 else (value - min_val) * 100
            if value < min_val:
                failed = True
            if best_margin is None or pct < best_margin:
                best_margin = pct

        if max_val is not None:
            # margin_pct from max: positive = clear, negative = violation
            pct = (max_val - value) / abs(max_val) * 100 if max_val != 0 else (max_val - value) * 100
            if value > max_val:
                failed = True
            if best_margin is None or pct < best_margin:
                best_margin = pct

        margin = best_margin if best_margin is not None else 0.0

        if failed:
            return margin, Status.FAIL
        if 0 < margin < margin_threshold:
            return margin, Status.MARGIN
        return margin, Status.PASS
