"""
Tests for task tools-7yx.4: HSPICE MT0 parser.
"""
import pytest
from pathlib import Path

from spec_result_parser.parsers.hspice_mt0 import parse_hspice_mt0
from spec_result_parser.models import Format, ParseError

FIXTURES = Path(__file__).parent / "fixtures" / "mt0"


class TestHspiceMt0Parser:
    def test_parse_tt_count(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_tt_27.mt0")
        assert len(measurements) == 6

    def test_parse_tt_gain_dc(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_tt_27.mt0")
        gain = next(m for m in measurements if m.name == "gain_dc")
        assert gain.value == pytest.approx(68.5, abs=0.01)
        assert gain.fmt == Format.HSPICE_MT0

    def test_parse_tt_ugbw(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_tt_27.mt0")
        ugbw = next(m for m in measurements if m.name == "ugbw")
        assert ugbw.value == pytest.approx(12_500_000.0, rel=1e-3)

    def test_parse_tt_all_names(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_tt_27.mt0")
        names = {m.name for m in measurements}
        assert names == {"gain_dc", "ugbw", "pm", "offset_v", "cmrr", "psrr"}

    def test_parse_ss_count(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_ss_125.mt0")
        assert len(measurements) == 4

    def test_parse_ss_degraded_gain(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_ss_125.mt0")
        gain = next(m for m in measurements if m.name == "gain_dc")
        assert gain.value == pytest.approx(62.1, abs=0.01)

    def test_parse_ff_skips_comments(self):
        """Parser skips $ and * comment lines."""
        measurements = parse_hspice_mt0(FIXTURES / "opamp_ff_0.mt0")
        names = {m.name for m in measurements}
        assert "gain_dc" in names
        assert "ugbw" in names
        assert "pm" in names

    def test_parse_ff_negative_value(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_ff_0.mt0")
        offset = next(m for m in measurements if m.name == "input_offset")
        assert offset.value == pytest.approx(-0.00123, rel=1e-2)

    def test_all_measurements_hspice_format(self):
        measurements = parse_hspice_mt0(FIXTURES / "opamp_tt_27.mt0")
        assert all(m.fmt == Format.HSPICE_MT0 for m in measurements)

    def test_hspice_measurements_have_no_unit(self):
        """MT0 files do not carry unit info — unit should be None."""
        measurements = parse_hspice_mt0(FIXTURES / "opamp_tt_27.mt0")
        assert all(m.unit is None for m in measurements)

    def test_invalid_file_raises_parse_error(self, tmp_path):
        bad = tmp_path / "bad.mt0"
        bad.write_text("random garbage\nnot mt0\n")
        with pytest.raises(ParseError):
            parse_hspice_mt0(bad)

    def test_empty_file_raises_parse_error(self, tmp_path):
        empty = tmp_path / "empty.mt0"
        empty.write_text("$ just a comment\n* another comment\n")
        with pytest.raises(ParseError, match="No measurements"):
            parse_hspice_mt0(empty)

    def test_missing_file_raises_error(self, tmp_path):
        with pytest.raises((FileNotFoundError, ParseError)):
            parse_hspice_mt0(tmp_path / "nonexistent.mt0")

    def test_scientific_notation(self, tmp_path):
        f = tmp_path / "sci.mt0"
        f.write_text("$ test\ngain_dc=6.85000e+01\n")
        meas = parse_hspice_mt0(f)
        assert meas[0].value == pytest.approx(68.5, abs=0.01)
