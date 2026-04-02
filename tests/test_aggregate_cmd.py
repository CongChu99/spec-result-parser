"""Integration tests for tools-7yx.12: `spec-parser aggregate` subcommand."""
import pytest
from pathlib import Path
from click.testing import CliRunner
from spec_result_parser.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
CORNERS_DIR = FIXTURES / "corners"
SPEC_YAML = FIXTURES / "specs" / "opamp.spec.yaml"
SPEC_CSV = FIXTURES / "specs" / "opamp.spec.csv"
CORNERS_YAML = CORNERS_DIR / "corners.yaml"


@pytest.fixture
def runner():
    return CliRunner()


class TestAggregateExitCodes:
    def test_mixed_pass_fail_exits_1(self, runner):
        """sf_m40 corner has FAIL — should exit 1."""
        result = runner.invoke(main, ["aggregate", str(CORNERS_DIR), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 1, result.output

    def test_all_pass_exits_0(self, runner, tmp_path):
        """Folder with only passing corners exits 0."""
        # Copy tt_27.psf (all PASS) to a fresh folder
        import shutil
        shutil.copy(CORNERS_DIR / "tt_27.psf", tmp_path / "tt_27.psf")
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 0, result.output

    def test_empty_folder_exits_2(self, runner, tmp_path):
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2, result.output

    def test_no_supported_files_exits_2(self, runner, tmp_path):
        (tmp_path / "data.tr0").write_text("data")
        result = runner.invoke(main, ["aggregate", str(tmp_path), "--spec", str(SPEC_YAML)])
        assert result.exit_code == 2, result.output

    def test_missing_spec_exits_nonzero(self, runner):
        result = runner.invoke(
            main, ["aggregate", str(CORNERS_DIR), "--spec", "/nonexistent.yaml"]
        )
        assert result.exit_code != 0


class TestAggregateOutput:
    def test_output_contains_corner_names(self, runner):
        result = runner.invoke(main, ["aggregate", str(CORNERS_DIR), "--spec", str(SPEC_YAML)])
        assert "tt_27" in result.output or "sf_m40" in result.output

    def test_output_contains_spec_names(self, runner):
        result = runner.invoke(main, ["aggregate", str(CORNERS_DIR), "--spec", str(SPEC_YAML)])
        assert "gain_dc" in result.output

    def test_output_contains_worst_case_row(self, runner):
        result = runner.invoke(main, ["aggregate", str(CORNERS_DIR), "--spec", str(SPEC_YAML)])
        assert "Worst" in result.output or "worst" in result.output

    def test_output_contains_statuses(self, runner):
        result = runner.invoke(main, ["aggregate", str(CORNERS_DIR), "--spec", str(SPEC_YAML)])
        assert "PASS" in result.output or "FAIL" in result.output

    def test_csv_spec_works(self, runner):
        result = runner.invoke(main, ["aggregate", str(CORNERS_DIR), "--spec", str(SPEC_CSV)])
        assert result.exit_code in (0, 1), result.output
        assert "gain_dc" in result.output

    def test_verbose_flag_accepted(self, runner):
        result = runner.invoke(
            main, ["aggregate", str(CORNERS_DIR), "--spec", str(SPEC_YAML), "--verbose"]
        )
        assert result.exit_code in (0, 1), result.output
