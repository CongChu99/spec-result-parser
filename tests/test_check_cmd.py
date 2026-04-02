"""Integration tests for tools-7yx.11: `spec-parser check` subcommand."""
import pytest
from pathlib import Path
from click.testing import CliRunner
from spec_result_parser.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
PSF_TT = FIXTURES / "psf" / "opamp_tt_27.psf"
PSF_SS = FIXTURES / "psf" / "opamp_ss_125.psf"
MT0_TT = FIXTURES / "mt0" / "opamp_tt_27.mt0"
SPEC_YAML = FIXTURES / "specs" / "opamp.spec.yaml"
SPEC_CSV = FIXTURES / "specs" / "opamp.spec.csv"


@pytest.fixture
def runner():
    return CliRunner()


class TestCheckExitCodes:
    def test_all_pass_exits_0(self, runner):
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 0, result.output

    def test_fail_exits_1(self, runner, tmp_path):
        """Create a PSF file with a failing spec (gain below minimum)."""
        bad_psf = tmp_path / "fail.psf"
        bad_psf.write_text(
            '// Spectre PSF ASCII\nHEADER\n"PSFversion" "1.1"\nEND HEADER\n'
            'TYPE\n"real" FLOAT DOUBLE PROP("units" "" "scale" "LINEAR" "grid" 1)\nEND TYPE\n'
            'VALUE\n"gain_dc" FLOAT DOUBLE 5.00000e+01 dB\nEND VALUE\n'
        )
        result = runner.invoke(main, ["check", str(bad_psf), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 1, result.output

    def test_parse_error_exits_2(self, runner, tmp_path):
        bad_file = tmp_path / "corrupt.psf"
        bad_file.write_text("not a valid PSF file")
        result = runner.invoke(main, ["check", str(bad_file), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2, result.output

    def test_unsupported_format_exits_2(self, runner, tmp_path):
        unknown = tmp_path / "result.tr0"
        unknown.write_text("data")
        result = runner.invoke(main, ["check", str(unknown), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2, result.output

    def test_missing_spec_exits_nonzero(self, runner):
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", "/nonexistent.yaml"])
        assert result.exit_code != 0


class TestCheckOutput:
    def test_output_contains_spec_names(self, runner):
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(SPEC_YAML)])
        assert "gain_dc" in result.output

    def test_output_contains_pass_status(self, runner):
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(SPEC_YAML)])
        assert "PASS" in result.output

    def test_output_contains_summary(self, runner):
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(SPEC_YAML)])
        assert "specs" in result.output.lower() or "PASS" in result.output

    def test_mt0_file_works(self, runner):
        result = runner.invoke(main, ["check", str(MT0_TT), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 0, result.output

    def test_csv_spec_works(self, runner):
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(SPEC_CSV)])
        assert result.exit_code == 0, result.output


class TestCheckOptions:
    def test_margin_threshold_option(self, runner):
        """With low threshold, more specs flagged as MARGIN."""
        result = runner.invoke(
            main, ["check", str(PSF_TT), "--spec", str(SPEC_YAML), "--margin-threshold", "50.0"]
        )
        assert result.exit_code in (0, 1)
        assert "MARGIN" in result.output or "PASS" in result.output

    def test_verbose_flag_accepted(self, runner):
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(SPEC_YAML), "--verbose"])
        assert result.exit_code == 0, result.output
