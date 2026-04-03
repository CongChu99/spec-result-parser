"""
Tests for task tools-7yx.2: Core data models (dataclasses + enums).

Acceptance criteria:
- Measurement, SpecTarget, SpecCheck, Corner, Status, Format dataclasses/enums defined
- All fields match design.md#data-model exactly
- 100% type-annotated
- Unit tests for dataclass construction pass
"""
import pytest
import numpy as np
from spec_result_parser.models import (
    Format,
    Status,
    Measurement,
    SpecTarget,
    SpecCheck,
    Corner,
    ParseError,
    ConfigError,
    Waveform,
)


class TestFormatEnum:
    def test_psf_ascii_member(self):
        assert Format.PSF_ASCII is not None

    def test_hspice_mt0_member(self):
        assert Format.HSPICE_MT0 is not None

    def test_unknown_member(self):
        assert Format.UNKNOWN is not None

    def test_from_extension_psf(self):
        assert Format.from_extension(".psf") == Format.PSF_ASCII

    def test_from_extension_mt0(self):
        assert Format.from_extension(".mt0") == Format.HSPICE_MT0

    def test_from_extension_unknown(self):
        assert Format.from_extension(".tr0") == Format.UNKNOWN

    def test_from_extension_case_insensitive(self):
        assert Format.from_extension(".PSF") == Format.PSF_ASCII


class TestStatusEnum:
    def test_pass_member(self):
        assert Status.PASS is not None

    def test_fail_member(self):
        assert Status.FAIL is not None

    def test_margin_member(self):
        assert Status.MARGIN is not None

    def test_na_member(self):
        assert Status.NA is not None


class TestMeasurement:
    def test_basic_construction(self):
        m = Measurement(name="gain_dc", value=68.5, unit="dB", fmt=Format.PSF_ASCII)
        assert m.name == "gain_dc"
        assert m.value == 68.5
        assert m.unit == "dB"
        assert m.fmt == Format.PSF_ASCII

    def test_unit_optional(self):
        m = Measurement(name="gain_dc", value=68.5, unit=None, fmt=Format.HSPICE_MT0)
        assert m.unit is None

    def test_is_frozen(self):
        """Measurement must be immutable (frozen dataclass)."""
        m = Measurement(name="gain_dc", value=68.5, unit="dB", fmt=Format.PSF_ASCII)
        with pytest.raises((AttributeError, TypeError)):
            m.value = 99.0  # type: ignore

    def test_repr_contains_name(self):
        m = Measurement(name="ugbw", value=12.5e6, unit="Hz", fmt=Format.PSF_ASCII)
        assert "ugbw" in repr(m)

    def test_scientific_notation_value(self):
        m = Measurement(name="ugbw", value=12.5e6, unit="Hz", fmt=Format.HSPICE_MT0)
        assert m.value == 12_500_000.0


class TestSpecTarget:
    def test_both_bounds(self):
        s = SpecTarget(name="pm", min_val=45.0, max_val=180.0, unit="deg")
        assert s.min_val == 45.0
        assert s.max_val == 180.0

    def test_min_only(self):
        s = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
        assert s.min_val == 60.0
        assert s.max_val is None

    def test_max_only(self):
        s = SpecTarget(name="offset", min_val=None, max_val=5e-3, unit="V")
        assert s.max_val == 5e-3
        assert s.min_val is None

    def test_is_frozen(self):
        s = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
        with pytest.raises((AttributeError, TypeError)):
            s.min_val = 50.0  # type: ignore


class TestSpecCheck:
    def test_pass_result(self):
        m = Measurement(name="gain_dc", value=68.5, unit="dB", fmt=Format.PSF_ASCII)
        t = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
        sc = SpecCheck(measurement=m, spec=t, status=Status.PASS, margin_pct=14.17)
        assert sc.status == Status.PASS
        assert sc.margin_pct == pytest.approx(14.17)

    def test_fail_result(self):
        m = Measurement(name="gain_dc", value=55.0, unit="dB", fmt=Format.PSF_ASCII)
        t = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
        sc = SpecCheck(measurement=m, spec=t, status=Status.FAIL, margin_pct=-8.33)
        assert sc.status == Status.FAIL

    def test_na_result_no_spec(self):
        m = Measurement(name="cmrr", value=80.0, unit="dB", fmt=Format.PSF_ASCII)
        sc = SpecCheck(measurement=m, spec=None, status=Status.NA, margin_pct=None)
        assert sc.status == Status.NA
        assert sc.spec is None

    def test_margin_result(self):
        m = Measurement(name="gain_dc", value=61.0, unit="dB", fmt=Format.PSF_ASCII)
        t = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
        sc = SpecCheck(measurement=m, spec=t, status=Status.MARGIN, margin_pct=1.67)
        assert sc.status == Status.MARGIN


class TestCorner:
    def test_corner_construction(self):
        m = Measurement(name="gain_dc", value=68.5, unit="dB", fmt=Format.PSF_ASCII)
        t = SpecTarget(name="gain_dc", min_val=60.0, max_val=None, unit="dB")
        sc = SpecCheck(measurement=m, spec=t, status=Status.PASS, margin_pct=14.17)
        c = Corner(name="tt_27", checks=[sc])
        assert c.name == "tt_27"
        assert len(c.checks) == 1

    def test_corner_overall_pass(self):
        checks = [
            SpecCheck(
                measurement=Measurement("gain_dc", 68.5, "dB", Format.PSF_ASCII),
                spec=SpecTarget("gain_dc", 60.0, None, "dB"),
                status=Status.PASS,
                margin_pct=14.17,
            ),
        ]
        c = Corner(name="tt_27", checks=checks)
        assert c.overall_status == Status.PASS

    def test_corner_overall_fail_if_any_fail(self):
        checks = [
            SpecCheck(
                measurement=Measurement("gain_dc", 68.5, "dB", Format.PSF_ASCII),
                spec=SpecTarget("gain_dc", 60.0, None, "dB"),
                status=Status.PASS,
                margin_pct=14.17,
            ),
            SpecCheck(
                measurement=Measurement("pm", 30.0, "deg", Format.PSF_ASCII),
                spec=SpecTarget("pm", 45.0, None, "deg"),
                status=Status.FAIL,
                margin_pct=-33.3,
            ),
        ]
        c = Corner(name="ss_125", checks=checks)
        assert c.overall_status == Status.FAIL

    def test_corner_overall_margin_if_no_fail(self):
        checks = [
            SpecCheck(
                measurement=Measurement("gain_dc", 61.0, "dB", Format.PSF_ASCII),
                spec=SpecTarget("gain_dc", 60.0, None, "dB"),
                status=Status.MARGIN,
                margin_pct=1.67,
            ),
        ]
        c = Corner(name="ff_0", checks=checks)
        assert c.overall_status == Status.MARGIN


# ---------------------------------------------------------------------------
# Task 1: PSF_BINARY, Waveform, SpecTarget.measure
# ---------------------------------------------------------------------------


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


class TestExceptions:
    def test_parse_error_is_exception(self):
        with pytest.raises(ParseError):
            raise ParseError("bad file format")

    def test_config_error_is_exception(self):
        with pytest.raises(ConfigError):
            raise ConfigError("bad spec config")

    def test_parse_error_has_message(self):
        e = ParseError("cannot parse result.psf as PSF-ASCII")
        assert "cannot parse" in str(e)

    def test_config_error_has_message(self):
        e = ConfigError("cannot load spec file: opamp.spec.yaml")
        assert "opamp.spec.yaml" in str(e)
