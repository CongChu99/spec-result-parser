"""
Tests for task tools-7yx.3: Spectre PSF-ASCII parser.

Acceptance criteria:
- Parses valid PSF-ASCII files and returns correct list[Measurement]
- Raises ParseError on invalid/non-PSF content
- Correctly extracts name, float value, unit from VALUE section
- Skips SWEEP sections (waveform data)
- Handles scientific notation (e.g., 12.5e6)
- Tests cover >=3 reference fixture files
- No external dependencies (stdlib only)
"""
import pytest
from pathlib import Path

from spec_result_parser.parsers.psf_ascii import parse_psf_ascii
from spec_result_parser.models import Format, ParseError

FIXTURES = Path(__file__).parent / "fixtures" / "psf"


class TestPsfAsciiParser:
    def test_parse_tt_corner_measurement_count(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_tt_27.psf")
        assert len(measurements) == 6

    def test_parse_tt_corner_gain_dc(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_tt_27.psf")
        gain = next(m for m in measurements if m.name == "gain_dc")
        assert gain.value == pytest.approx(68.5, abs=0.01)
        assert gain.unit == "dB"
        assert gain.fmt == Format.PSF_ASCII

    def test_parse_tt_corner_ugbw(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_tt_27.psf")
        ugbw = next(m for m in measurements if m.name == "ugbw")
        assert ugbw.value == pytest.approx(12_500_000.0, rel=1e-3)
        assert ugbw.unit == "Hz"

    def test_parse_tt_corner_pm(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_tt_27.psf")
        pm = next(m for m in measurements if m.name == "pm")
        assert pm.value == pytest.approx(67.23, abs=0.01)
        assert pm.unit == "deg"

    def test_parse_tt_corner_all_names(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_tt_27.psf")
        names = {m.name for m in measurements}
        assert names == {"gain_dc", "ugbw", "pm", "offset_v", "cmrr", "psrr"}

    def test_parse_ss_corner_fewer_measurements(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_ss_125.psf")
        assert len(measurements) == 4

    def test_parse_ss_corner_degraded_gain(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_ss_125.psf")
        gain = next(m for m in measurements if m.name == "gain_dc")
        assert gain.value == pytest.approx(62.1, abs=0.01)

    def test_skips_sweep_section(self):
        """Parser must skip SWEEP section and only return VALUE scalars."""
        measurements = parse_psf_ascii(FIXTURES / "opamp_with_sweep.psf")
        assert len(measurements) == 2, "Should only return VALUE scalars, not SWEEP data"

    def test_sweep_file_correct_values(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_with_sweep.psf")
        names = {m.name for m in measurements}
        assert "gain_dc" in names
        assert "pm" in names

    def test_all_measurements_are_psf_format(self):
        measurements = parse_psf_ascii(FIXTURES / "opamp_tt_27.psf")
        assert all(m.fmt == Format.PSF_ASCII for m in measurements)

    def test_scientific_notation_parsed_correctly(self):
        """12.5e6 should parse to 12500000.0"""
        measurements = parse_psf_ascii(FIXTURES / "opamp_tt_27.psf")
        ugbw = next(m for m in measurements if m.name == "ugbw")
        assert ugbw.value > 1e6  # definitely a large number

    def test_negative_value(self, tmp_path):
        """Parser handles negative values."""
        psf_file = tmp_path / "neg.psf"
        psf_file.write_text(
            "HEADER\nEND HEADER\nTYPE\nEND TYPE\nVALUE\n"
            '"input_offset" FLOAT DOUBLE -1.23456e-03 V\n'
            "END VALUE\n"
        )
        measurements = parse_psf_ascii(psf_file)
        assert len(measurements) == 1
        assert measurements[0].value == pytest.approx(-0.00123456, rel=1e-4)

    def test_measurement_without_unit(self, tmp_path):
        """Parser handles VALUE lines with no unit field."""
        psf_file = tmp_path / "no_unit.psf"
        psf_file.write_text(
            "HEADER\nEND HEADER\nTYPE\nEND TYPE\nVALUE\n"
            '"ratio" FLOAT DOUBLE 1.23456e+00\n'
            "END VALUE\n"
        )
        measurements = parse_psf_ascii(psf_file)
        assert len(measurements) == 1
        assert measurements[0].unit is None or measurements[0].unit == ""

    def test_empty_value_section(self, tmp_path):
        """PSF with empty VALUE section raises ParseError."""
        psf_file = tmp_path / "empty.psf"
        psf_file.write_text("HEADER\nEND HEADER\nTYPE\nEND TYPE\nVALUE\nEND VALUE\n")
        with pytest.raises(ParseError, match="No scalar measurements"):
            parse_psf_ascii(psf_file)

    def test_invalid_format_raises_parse_error(self, tmp_path):
        """Non-PSF file raises ParseError."""
        bad_file = tmp_path / "bad.psf"
        bad_file.write_text("This is not a PSF file\nrandom garbage content\n")
        with pytest.raises(ParseError):
            parse_psf_ascii(bad_file)

    def test_missing_file_raises_error(self, tmp_path):
        """Missing file raises FileNotFoundError or ParseError."""
        with pytest.raises((FileNotFoundError, ParseError)):
            parse_psf_ascii(tmp_path / "nonexistent.psf")
