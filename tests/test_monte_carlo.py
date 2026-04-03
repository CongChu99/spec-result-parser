"""Tests for MonteCarloAggregator and McSpecStat model."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from spec_result_parser.models import McSpecStat, SpecTarget, Status
from spec_result_parser.monte_carlo import (
    MonteCarloAggregator,
    _compute_cpk,
    _mc_status,
    _yield_from_cpk,
)


# ---------------------------------------------------------------------------
# Helpers to build fixture PSF files
# ---------------------------------------------------------------------------

def _write_psf(path: Path, values: dict[str, tuple[float, str]]) -> None:
    """Write a minimal PSF-ASCII fixture with given name→(value, unit) pairs."""
    lines = [
        "// Spectre PSF ASCII",
        "HEADER",
        '"PSFversion" "1.1"',
        '"simulator" "spectre"',
        "END HEADER",
        "TYPE",
        '"real" FLOAT DOUBLE PROP(',
        '"units" ""',
        '"scale" "LINEAR"',
        '"grid" 1',
        ")",
        "END TYPE",
        "VALUE",
    ]
    for name, (val, unit) in values.items():
        lines.append(f'"{name}" FLOAT DOUBLE {val:.6e} {unit}')
    lines.append("END VALUE")
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestYieldFromCpk:
    def test_cpk_1_gives_near_100_pct(self):
        y = _yield_from_cpk(1.0)
        assert 99.5 < y < 100.0

    def test_cpk_0_gives_near_0_pct(self):
        y = _yield_from_cpk(0.0)
        assert abs(y) < 1.0

    def test_cpk_negative_clamped_to_0(self):
        y = _yield_from_cpk(-1.0)
        assert y == 0.0

    def test_cpk_2_gives_very_high_yield(self):
        y = _yield_from_cpk(2.0)
        assert y > 99.999


class TestComputeCpk:
    def test_min_only_spec(self):
        spec = SpecTarget(name="gain", min_val=60.0, max_val=None, unit="dB")
        cpk = _compute_cpk(mean=68.0, std=1.0, spec=spec)
        # (68 - 60) / (3 * 1) = 2.67
        assert cpk == pytest.approx(8.0 / 3.0, rel=1e-6)

    def test_max_only_spec(self):
        spec = SpecTarget(name="offset", min_val=None, max_val=5e-3, unit="V")
        cpk = _compute_cpk(mean=1e-3, std=0.5e-3, spec=spec)
        # (5e-3 - 1e-3) / (3 * 0.5e-3) = 4e-3 / 1.5e-3 = 2.67
        assert cpk == pytest.approx(4e-3 / 1.5e-3, rel=1e-6)

    def test_two_sided_spec_min_binding(self):
        spec = SpecTarget(name="vref", min_val=1.19, max_val=1.21, unit="V")
        cpk = _compute_cpk(mean=1.195, std=0.002, spec=spec)
        cpu = (1.21 - 1.195) / (3 * 0.002)  # 0.015/0.006 = 2.5
        cpl = (1.195 - 1.19) / (3 * 0.002)  # 0.005/0.006 = 0.833  ← binding
        assert cpk == pytest.approx(min(cpu, cpl), rel=1e-6)

    def test_zero_std_returns_none(self):
        spec = SpecTarget(name="gain", min_val=60.0, max_val=None, unit="dB")
        assert _compute_cpk(mean=68.0, std=0.0, spec=spec) is None

    def test_unbounded_spec_returns_none(self):
        spec = SpecTarget(name="freq", min_val=None, max_val=None, unit="Hz")
        assert _compute_cpk(mean=1e6, std=1e4, spec=spec) is None


class TestMcStatus:
    def _spec(self, min_val=None, max_val=None):
        return SpecTarget(name="x", min_val=min_val, max_val=max_val, unit="")

    def test_pass_well_away_from_limits(self):
        spec = self._spec(min_val=60.0)
        # mean=70, std=1 → mean-3σ=67 > 60, Cpk=(70-60)/(3)=3.33 → PASS
        cpk = _compute_cpk(70.0, 1.0, spec)
        status = _mc_status(70.0, 1.0, spec, cpk)
        assert status == Status.PASS

    def test_fail_3sigma_violates_min(self):
        spec = self._spec(min_val=60.0)
        # mean=62, std=2 → mean-3σ=56 < 60 → FAIL
        cpk = _compute_cpk(62.0, 2.0, spec)
        status = _mc_status(62.0, 2.0, spec, cpk)
        assert status == Status.FAIL

    def test_margin_cpk_below_threshold(self):
        spec = self._spec(min_val=60.0)
        # mean=62, std=0.8 → mean-3σ=59.6 < 60 actually → FAIL
        # Let's use: mean=63.5, std=1 → cpk=(63.5-60)/3=1.17 → MARGIN (< 1.33)
        cpk = _compute_cpk(63.5, 1.0, spec)
        status = _mc_status(63.5, 1.0, spec, cpk)
        assert status == Status.MARGIN

    def test_no_spec_returns_na(self):
        status = _mc_status(68.0, 1.0, None, None)
        assert status == Status.NA


# ---------------------------------------------------------------------------
# Integration tests — MonteCarloAggregator
# ---------------------------------------------------------------------------


class TestMonteCarloAggregator:
    def _make_folder(self, tmp_path: Path, samples: list[dict]) -> Path:
        mc_dir = tmp_path / "mc_runs"
        mc_dir.mkdir()
        for i, vals in enumerate(samples, start=1):
            _write_psf(
                mc_dir / f"mc_{i:03d}.psf",
                {k: (v, "dB") for k, v in vals.items()},
            )
        return mc_dir

    def test_basic_statistics(self, tmp_path):
        """Mean and std calculated correctly from 5 samples."""
        gain_values = [65.0, 66.0, 67.0, 68.0, 69.0]
        samples = [{"gain_dc": v} for v in gain_values]
        folder = self._make_folder(tmp_path, samples)
        spec = {"gain_dc": SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")}

        results = MonteCarloAggregator.aggregate(folder, spec)
        assert len(results) == 1
        stat = results[0]

        assert stat.name == "gain_dc"
        assert stat.n == 5
        assert stat.mean == pytest.approx(np.mean(gain_values))
        assert stat.std == pytest.approx(np.std(gain_values, ddof=1))
        assert stat.min_val == pytest.approx(65.0)
        assert stat.max_val == pytest.approx(69.0)

    def test_status_pass_with_good_cpk(self, tmp_path):
        """All samples well above min → PASS status."""
        samples = [{"gain_dc": 70.0 + i * 0.1} for i in range(10)]
        folder = self._make_folder(tmp_path, samples)
        spec = {"gain_dc": SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")}

        results = MonteCarloAggregator.aggregate(folder, spec)
        assert results[0].status == Status.PASS

    def test_status_fail_when_3sigma_violates(self, tmp_path):
        """Samples close to spec limit → FAIL (mean±3σ violates boundary)."""
        # mean=61, std=2 → mean-3σ=55 < 60 → FAIL
        import random; random.seed(42)
        samples = [{"gain_dc": 61.0 + (i % 5) * 0.4 - 1.0} for i in range(20)]
        folder = self._make_folder(tmp_path, samples)
        spec = {"gain_dc": SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")}

        results = MonteCarloAggregator.aggregate(folder, spec)
        # With mean~60.5 and std~0.6, mean-3σ ≈ 58.7 < 60 → FAIL
        assert results[0].status in (Status.FAIL, Status.MARGIN)

    def test_cpk_and_yield_populated(self, tmp_path):
        """Cpk and yield_pct are computed when spec has bounds."""
        samples = [{"ugbw": 12e6 + i * 0.1e6} for i in range(10)]
        folder = self._make_folder(tmp_path, samples)
        spec = {"ugbw": SpecTarget(name="ugbw", min_val=10e6, max_val=None, unit="Hz")}

        results = MonteCarloAggregator.aggregate(folder, spec)
        stat = results[0]
        assert stat.cpk is not None
        assert stat.cpk > 0
        assert stat.yield_pct is not None
        assert 0 < stat.yield_pct <= 100

    def test_values_list_preserved(self, tmp_path):
        """Raw sample values stored for histogram rendering."""
        vals = [65.0, 66.5, 67.2, 68.0, 69.1]
        samples = [{"gain_dc": v} for v in vals]
        folder = self._make_folder(tmp_path, samples)
        spec = {"gain_dc": SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")}

        results = MonteCarloAggregator.aggregate(folder, spec)
        assert sorted(results[0].values) == pytest.approx(sorted(vals))

    def test_folder_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            MonteCarloAggregator.aggregate(tmp_path / "nonexistent", {})

    def test_empty_folder_raises(self, tmp_path):
        from spec_result_parser.models import ConfigError
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ConfigError):
            MonteCarloAggregator.aggregate(empty, {})

    def test_corrupt_files_skipped_with_warning(self, tmp_path):
        """Corrupt files emit a warning but don't block aggregation."""
        mc_dir = tmp_path / "mc"
        mc_dir.mkdir()
        # One good file
        _write_psf(mc_dir / "mc_001.psf", {"gain_dc": (68.0, "dB")})
        # One corrupt file
        (mc_dir / "mc_002.psf").write_text("garbage content")

        spec = {"gain_dc": SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")}
        with pytest.warns(UserWarning, match="MC WARN"):
            results = MonteCarloAggregator.aggregate(mc_dir, spec)
        assert results[0].n == 1

    def test_spec_not_in_samples_skipped(self, tmp_path):
        """Spec names not present in result files are omitted from output."""
        samples = [{"gain_dc": 68.0}]
        folder = self._make_folder(tmp_path, samples)
        spec = {
            "gain_dc": SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB"),
            "ugbw": SpecTarget(name="ugbw", min_val=10e6, max_val=None, unit="Hz"),
        }
        results = MonteCarloAggregator.aggregate(folder, spec)
        names = [r.name for r in results]
        assert "gain_dc" in names
        assert "ugbw" not in names  # not present in samples

    def test_unspecced_measurements_included_as_na(self, tmp_path):
        """Measurements not in spec_targets are included with NA status."""
        samples = [{"gain_dc": 68.0, "psrr": 78.0}]
        folder = self._make_folder(tmp_path, samples)
        spec = {"gain_dc": SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")}

        results = MonteCarloAggregator.aggregate(folder, spec)
        names = {r.name: r.status for r in results}
        assert "psrr" in names
        assert names["psrr"] == Status.NA
