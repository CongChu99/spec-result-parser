"""Tests for tools-7yx.8: SpecChecker — spec check logic."""
import pytest
from spec_result_parser.checker import SpecChecker
from spec_result_parser.models import Format, Measurement, SpecTarget, Status


def m(name, value, unit="dB"):
    return Measurement(name=name, value=value, unit=unit, fmt=Format.PSF_ASCII)


def t(name, min_val=None, max_val=None, unit="dB"):
    return SpecTarget(name=name, min_val=min_val, max_val=max_val, unit=unit)


class TestSpecCheckerPass:
    def test_pass_min_only(self):
        result = SpecChecker.check(m("gain_dc", 68.5), t("gain_dc", min_val=60.0))
        assert result.status == Status.PASS

    def test_pass_max_only(self):
        result = SpecChecker.check(m("offset", 0.001, "V"), t("offset", max_val=0.005, unit="V"))
        assert result.status == Status.PASS

    def test_pass_both_bounds(self):
        result = SpecChecker.check(m("pm", 67.0, "deg"), t("pm", min_val=45.0, max_val=90.0, unit="deg"))
        assert result.status == Status.PASS

    def test_pass_exactly_at_min(self):
        result = SpecChecker.check(m("gain_dc", 60.0), t("gain_dc", min_val=60.0))
        assert result.status == Status.PASS

    def test_pass_exactly_at_max(self):
        result = SpecChecker.check(m("offset", 0.005, "V"), t("offset", max_val=0.005, unit="V"))
        assert result.status == Status.PASS


class TestSpecCheckerFail:
    def test_fail_below_min(self):
        result = SpecChecker.check(m("gain_dc", 55.0), t("gain_dc", min_val=60.0))
        assert result.status == Status.FAIL

    def test_fail_above_max(self):
        result = SpecChecker.check(m("offset", 0.010, "V"), t("offset", max_val=0.005, unit="V"))
        assert result.status == Status.FAIL

    def test_fail_margin_pct_is_negative(self):
        result = SpecChecker.check(m("pm", 30.0, "deg"), t("pm", min_val=45.0, unit="deg"))
        assert result.margin_pct < 0

    def test_fail_outside_both_bounds(self):
        result = SpecChecker.check(m("pm", 10.0, "deg"), t("pm", min_val=45.0, max_val=135.0, unit="deg"))
        assert result.status == Status.FAIL


class TestSpecCheckerMargin:
    def test_margin_close_to_min(self):
        """68.5 dB vs min 60.0 — margin = (68.5-60)/60 = 14.2% but with threshold 20% → MARGIN"""
        result = SpecChecker.check(
            m("gain_dc", 61.0), t("gain_dc", min_val=60.0), margin_threshold=10.0
        )
        assert result.status == Status.MARGIN

    def test_margin_close_to_max(self):
        result = SpecChecker.check(
            m("offset", 0.0048, "V"), t("offset", max_val=0.005, unit="V"), margin_threshold=10.0
        )
        assert result.status == Status.MARGIN

    def test_margin_pct_positive(self):
        result = SpecChecker.check(
            m("gain_dc", 61.0), t("gain_dc", min_val=60.0), margin_threshold=10.0
        )
        assert result.margin_pct > 0

    def test_no_margin_when_well_clear(self):
        """68.5 dB vs min 60 — 14.2% clear, threshold 10% → should PASS not MARGIN"""
        result = SpecChecker.check(
            m("gain_dc", 68.5), t("gain_dc", min_val=60.0), margin_threshold=10.0
        )
        assert result.status == Status.PASS

    def test_default_margin_threshold_is_10_pct(self):
        """Default threshold = 10%. 61.0 vs min 60.0 → 1.67% clear = MARGIN."""
        result = SpecChecker.check(m("gain_dc", 61.0), t("gain_dc", min_val=60.0))
        assert result.status == Status.MARGIN


class TestSpecCheckerNA:
    def test_na_when_no_spec(self):
        result = SpecChecker.check(m("cmrr", 80.0), None)
        assert result.status == Status.NA

    def test_na_margin_pct_is_none(self):
        result = SpecChecker.check(m("cmrr", 80.0), None)
        assert result.margin_pct is None

    def test_na_spec_field_is_none(self):
        result = SpecChecker.check(m("cmrr", 80.0), None)
        assert result.spec is None


class TestSpecCheckerResult:
    def test_result_carries_measurement(self):
        meas = m("gain_dc", 68.5)
        result = SpecChecker.check(meas, t("gain_dc", min_val=60.0))
        assert result.measurement is meas

    def test_result_carries_spec(self):
        spec = t("gain_dc", min_val=60.0)
        result = SpecChecker.check(m("gain_dc", 68.5), spec)
        assert result.spec is spec

    def test_margin_pct_calculation_min_bound(self):
        """margin_pct = (value - min) / min * 100 for min-only spec."""
        result = SpecChecker.check(m("gain_dc", 66.0), t("gain_dc", min_val=60.0))
        expected_pct = (66.0 - 60.0) / 60.0 * 100
        assert result.margin_pct == pytest.approx(expected_pct, rel=1e-3)
