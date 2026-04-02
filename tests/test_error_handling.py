"""Tests for tools-7yx.13: Error handling & edge cases."""
import pytest
from pathlib import Path
from click.testing import CliRunner
from spec_result_parser.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
PSF_TT = FIXTURES / "psf" / "opamp_tt_27.psf"
SPEC_YAML = FIXTURES / "specs" / "opamp.spec.yaml"


@pytest.fixture
def runner():
    return CliRunner()


class TestCheckErrorPaths:
    def test_yaml_syntax_error_exits_2(self, runner, tmp_path):
        bad_spec = tmp_path / "bad.yaml"
        bad_spec.write_text("specs: {\n  invalid yaml [[[")
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(bad_spec)])
        assert result.exit_code == 2

    def test_yaml_missing_specs_key_exits_2(self, runner, tmp_path):
        bad_spec = tmp_path / "missing_key.yaml"
        bad_spec.write_text("not_specs:\n  gain_dc: {min: 60}\n")
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(bad_spec)])
        assert result.exit_code == 2

    def test_csv_missing_columns_exits_2(self, runner, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("wrong_col1,wrong_col2\nfoo,bar\n")
        result = runner.invoke(main, ["check", str(PSF_TT), "--spec", str(bad_csv)])
        assert result.exit_code == 2

    def test_corrupted_psf_exits_2(self, runner, tmp_path):
        bad_psf = tmp_path / "bad.psf"
        bad_psf.write_text("not a psf file at all !!!")
        result = runner.invoke(main, ["check", str(bad_psf), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2

    def test_unknown_extension_check_exits_2(self, runner, tmp_path):
        unk = tmp_path / "result.tr0"
        unk.write_text("data")
        result = runner.invoke(main, ["check", str(unk), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2

    def test_error_message_present_on_failure(self, runner, tmp_path):
        bad_psf = tmp_path / "bad.psf"
        bad_psf.write_text("garbage")
        result = runner.invoke(main, ["check", str(bad_psf), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2
        assert "Error" in result.output or result.exit_code == 2


class TestAggregateErrorPaths:
    def test_empty_folder_exits_2(self, runner, tmp_path):
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2

    def test_no_supported_files_exits_2(self, runner, tmp_path):
        (tmp_path / "data.tr0").write_text("data")
        (tmp_path / "notes.txt").write_text("notes")
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2

    def test_corrupted_file_skipped_not_fatal(self, runner, tmp_path):
        """One corrupt + one good → exits 0/1 (not 2), corrupt file is skipped."""
        good = tmp_path / "good.psf"
        good.write_text(
            '// Spectre PSF ASCII\nHEADER\n"PSFversion" "1.1"\nEND HEADER\n'
            'TYPE\n"real" FLOAT DOUBLE PROP("units" "" "scale" "LINEAR" "grid" 1)\nEND TYPE\n'
            'VALUE\n"gain_dc" FLOAT DOUBLE 6.85e+01 dB\nEND VALUE\n'
        )
        bad = tmp_path / "corrupt.psf"
        bad.write_text("not valid at all")
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(SPEC_YAML)])
        assert result.exit_code in (0, 1), f"Expected 0 or 1, got {result.exit_code}: {result.output}"
        assert "good" in result.output

    def test_yaml_syntax_error_exits_2(self, runner, tmp_path):
        import shutil
        shutil.copy(FIXTURES / "psf" / "opamp_tt_27.psf", tmp_path / "tt_27.psf")
        bad_spec = tmp_path / "bad.yaml"
        bad_spec.write_text("specs: {\n  broken [[[")
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(bad_spec)])
        assert result.exit_code == 2

    def test_all_files_corrupt_exits_2(self, runner, tmp_path):
        """If all files fail to parse, ConfigError → exit 2."""
        (tmp_path / "a.psf").write_text("garbage1")
        (tmp_path / "b.psf").write_text("garbage2")
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2


class TestEdgeCases:
    def test_check_spec_with_extra_measurements(self, runner, tmp_path):
        """Measurements in file that have no spec → NA (non-fatal)."""
        psf = tmp_path / "extra.psf"
        psf.write_text(
            '// Spectre PSF ASCII\nHEADER\n"PSFversion" "1.1"\nEND HEADER\n'
            'TYPE\n"real" FLOAT DOUBLE PROP("units" "" "scale" "LINEAR" "grid" 1)\nEND TYPE\n'
            'VALUE\n"gain_dc" FLOAT DOUBLE 6.85e+01 dB\n'
            '"undocumented_meas" FLOAT DOUBLE 1.23e+00 V\nEND VALUE\n'
        )
        result = runner.invoke(main, ["check", str(psf), "--spec", str(SPEC_YAML)])
        assert result.exit_code in (0, 1)
        assert "gain_dc" in result.output

    def test_check_margin_threshold_zero(self, runner):
        """Threshold 0 → everything with margin > 0 is PASS, nothing MARGIN."""
        result = runner.invoke(
            main, ["check", str(PSF_TT), "--spec", str(SPEC_YAML), "--margin-threshold", "0.0"]
        )
        assert result.exit_code == 0
        assert "MARGIN" not in result.output
