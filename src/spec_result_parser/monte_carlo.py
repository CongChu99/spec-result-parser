"""MonteCarloAggregator — statistical analysis of N Monte Carlo simulation runs.

Usage::

    folder/
        mc_001.psf   # one PSF/MT0 file per MC sample
        mc_002.psf
        ...

    stats = MonteCarloAggregator.aggregate(folder, spec_targets)
    # → List[McSpecStat]

Cpk (Process Capability Index)
-------------------------------
For a spec with both bounds (LSL, USL)::

    cpu = (USL - μ) / (3σ)
    cpl = (μ - LSL) / (3σ)
    Cpk = min(cpu, cpl)

For a min-only spec: Cpk = (μ - LSL) / (3σ)
For a max-only spec: Cpk = (USL - μ) / (3σ)
Yield estimate:      yield_pct = erf(Cpk * 3 / sqrt(2)) × 100   (one-sided)
                     yield_pct = erf(Cpk * 3 / sqrt(2)) × 100   (two-sided, Cpk=min limit)

Status rules (based on 3σ band, i.e. 99.73% probability band):
    FAIL   — mean ± 3σ violates a spec bound
    MARGIN — mean ± 3σ is within 10% of a bound (Cpk < 1.33)
    PASS   — Cpk ≥ 1.33
"""
from __future__ import annotations

import warnings
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from spec_result_parser.checker import _DEFAULT_MARGIN_THRESHOLD
from spec_result_parser.format_detector import detect
from spec_result_parser.models import (
    ConfigError,
    McSpecStat,
    Measurement,
    ParseError,
    SpecTarget,
    Status,
)
from spec_result_parser.parsers.hspice_mt0 import parse_hspice_mt0
from spec_result_parser.parsers.psf_ascii import parse_psf_ascii

_PARSERS = {
    "psf_ascii": parse_psf_ascii,
    "hspice_mt0": parse_hspice_mt0,
}

# Cpk threshold for MARGIN: Cpk in [1.0, 1.33) → MARGIN
_CPK_MARGIN_LOW = 1.0
_CPK_PASS_MIN = 1.33


def _norm_cdf_approx(x: float) -> float:
    """CDF of standard normal via erf — avoids scipy dependency."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _yield_from_cpk(cpk: float) -> float:
    """Estimate yield % from Cpk (assumes process centred on nominal).

    Uses the one-sided formula:  Yield = erf(Cpk * 3 / sqrt(2)) * 100
    This is equivalent to Φ(3*Cpk) - Φ(-3*Cpk) for a centred process, expressed
    as a percentage. Clamped to [0, 100].
    """
    raw = erf(cpk * 3.0 / sqrt(2.0)) * 100.0
    return max(0.0, min(100.0, raw))


def _compute_cpk(
    mean: float,
    std: float,
    spec: SpecTarget,
) -> Optional[float]:
    """Return Cpk for the given spec. None if std==0 or spec is unbounded."""
    if std <= 0:
        return None  # Cannot compute Cpk for zero-variance data

    candidates: List[float] = []
    if spec.min_val is not None:
        candidates.append((mean - spec.min_val) / (3.0 * std))
    if spec.max_val is not None:
        candidates.append((spec.max_val - mean) / (3.0 * std))

    if not candidates:
        return None  # unbounded spec
    return min(candidates)


def _mc_status(
    mean: float,
    std: float,
    spec: Optional[SpecTarget],
    cpk: Optional[float],
    margin_threshold: float = _DEFAULT_MARGIN_THRESHOLD,
) -> Status:
    """Derive MC status from mean±3σ vs spec bounds.

    Strategy:
        - If mean - 3σ < LSL or mean + 3σ > USL → FAIL
        - Else if Cpk < 1.33 (within 10% headroom) → MARGIN
        - Else PASS
    """
    if spec is None:
        return Status.NA

    three_sigma = 3.0 * std

    if spec.min_val is not None and (mean - three_sigma) < spec.min_val:
        return Status.FAIL
    if spec.max_val is not None and (mean + three_sigma) > spec.max_val:
        return Status.FAIL

    if cpk is not None and cpk < _CPK_PASS_MIN:
        return Status.MARGIN

    return Status.PASS


class MonteCarloAggregator:
    """Aggregate N Monte Carlo simulation result files into per-spec statistics."""

    @classmethod
    def aggregate(
        cls,
        folder: Path,
        spec_targets: Dict[str, SpecTarget],
        margin_threshold: float = _DEFAULT_MARGIN_THRESHOLD,
        n_sigma: float = 3.0,
    ) -> List[McSpecStat]:
        """Scan folder, parse all supported files, compute per-spec statistics.

        Args:
            folder: Directory containing one file per MC sample (.psf or .mt0).
            spec_targets: Mapping of spec name → SpecTarget from spec loader.
            margin_threshold: % within a limit to flag as MARGIN (unused here,
                              status is determined via Cpk instead).
            n_sigma: Band multiplier for status check (default 3σ ≈ 99.73%).

        Returns:
            List[McSpecStat] — one entry per spec found across all samples.

        Raises:
            FileNotFoundError: If folder does not exist.
            ConfigError: If folder is empty or no samples could be parsed.
        """
        folder = Path(folder)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")

        candidates = sorted(f for f in folder.iterdir() if f.is_file())
        if not candidates:
            raise ConfigError(f"Monte Carlo folder is empty: {folder}")

        # Collect raw values per spec name: { spec_name: [v1, v2, ...] }
        collected: Dict[str, List[float]] = {}
        units: Dict[str, Optional[str]] = {}
        parsed_count = 0

        for filepath in candidates:
            fmt = detect(filepath)
            if fmt is None:
                continue
            parse_fn = _PARSERS.get(fmt.value)
            if parse_fn is None:
                continue

            try:
                measurements: List[Measurement] = parse_fn(filepath)
            except (ParseError, Exception) as exc:
                warnings.warn(
                    f"[MC WARN] Skipping {filepath.name}: {exc}",
                    stacklevel=2,
                )
                continue

            for m in measurements:
                collected.setdefault(m.name, []).append(m.value)
                units.setdefault(m.name, m.unit)

            parsed_count += 1

        if parsed_count == 0:
            raise ConfigError(
                f"No MC samples could be parsed in {folder}"
            )

        # Build McSpecStat per spec
        results: List[McSpecStat] = []
        for spec_name, spec in spec_targets.items():
            values = collected.get(spec_name)
            if not values:
                continue  # spec not found in any sample

            arr = np.array(values, dtype=float)
            mean = float(np.mean(arr))
            std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            cpk = _compute_cpk(mean, std, spec)
            yield_pct = _yield_from_cpk(cpk) if cpk is not None else None
            status = _mc_status(mean, std, spec, cpk, margin_threshold)

            results.append(McSpecStat(
                name=spec_name,
                n=len(arr),
                mean=mean,
                std=std,
                min_val=float(np.min(arr)),
                max_val=float(np.max(arr)),
                cpk=cpk,
                yield_pct=yield_pct,
                status=status,
                unit=units.get(spec_name),
                values=list(arr),
            ))

        # Also include specs found in samples but not in spec_targets (as N/A)
        for name, values in collected.items():
            if name not in spec_targets:
                arr = np.array(values, dtype=float)
                results.append(McSpecStat(
                    name=name,
                    n=len(arr),
                    mean=float(np.mean(arr)),
                    std=float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
                    min_val=float(np.min(arr)),
                    max_val=float(np.max(arr)),
                    cpk=None,
                    yield_pct=None,
                    status=Status.NA,
                    unit=units.get(name),
                    values=list(arr),
                ))

        return results
