"""Tests for tools-7yx.9: CornerAggregator — multi-corner aggregation."""
import pytest
from pathlib import Path
from spec_result_parser.corner_aggregator import CornerAggregator
from spec_result_parser.models import ConfigError, Corner, Status
from spec_result_parser.spec_loader import load_spec

FIXTURES = Path(__file__).parent / "fixtures"
CORNERS_DIR = FIXTURES / "corners"
SPEC_FILE = FIXTURES / "specs" / "opamp.spec.yaml"


@pytest.fixture
def spec_targets():
    return load_spec(SPEC_FILE)


class TestAggregateBasic:
    def test_returns_list_of_corners(self, spec_targets):
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        assert isinstance(result, list)
        assert all(isinstance(c, Corner) for c in result)

    def test_corner_count_matches_supported_files(self, spec_targets):
        # 3 PSF + 2 MT0 = 5 supported files, corners.yaml ignored (not auto-loaded)
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        assert len(result) == 5

    def test_corner_names_from_filename_stems(self, spec_targets):
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        names = {c.name for c in result}
        assert "tt_27" in names
        assert "ss_125" in names
        assert "ff_m40" in names
        assert "sf_m40" in names

    def test_each_corner_has_checks(self, spec_targets):
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        for corner in result:
            assert len(corner.checks) > 0

    def test_checks_match_spec_count(self, spec_targets):
        """Each corner should have one check per spec target."""
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        n_specs = len(spec_targets)
        for corner in result:
            assert len(corner.checks) == n_specs


class TestAggregateStatus:
    def test_tt_corner_all_pass(self, spec_targets):
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        tt = next(c for c in result if c.name == "tt_27" and c.checks[0].measurement.fmt.value == "psf_ascii")
        assert tt.overall_status in (Status.PASS, Status.MARGIN)

    def test_sf_corner_has_fail(self, spec_targets):
        """sf_m40: gain_dc=55 < min 60 → FAIL."""
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        sf = next(c for c in result if c.name == "sf_m40")
        assert sf.overall_status == Status.FAIL

    def test_fail_check_has_negative_margin(self, spec_targets):
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        sf = next(c for c in result if c.name == "sf_m40")
        fail_checks = [ch for ch in sf.checks if ch.status == Status.FAIL]
        assert len(fail_checks) > 0
        for ch in fail_checks:
            assert ch.margin_pct < 0


class TestMixedFormats:
    def test_psf_and_mt0_both_processed(self, spec_targets):
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        formats = {ch.measurement.fmt.value for c in result for ch in c.checks}
        assert "psf_ascii" in formats
        assert "hspice_mt0" in formats

    def test_duplicate_stem_both_included(self, spec_targets):
        """tt_27.psf and tt_27.mt0 are both processed as separate corners."""
        result = CornerAggregator.aggregate(CORNERS_DIR, spec_targets)
        tt_corners = [c for c in result if c.name == "tt_27"]
        assert len(tt_corners) == 2


class TestErrorHandling:
    def test_empty_folder_raises_config_error(self, tmp_path, spec_targets):
        with pytest.raises(ConfigError, match="empty|no supported"):
            CornerAggregator.aggregate(tmp_path, spec_targets)

    def test_no_supported_files_raises_config_error(self, tmp_path, spec_targets):
        (tmp_path / "result.tr0").write_text("data")
        (tmp_path / "result.bin").write_bytes(b"\x00\x01")
        with pytest.raises(ConfigError, match="[Nn]o supported"):
            CornerAggregator.aggregate(tmp_path, spec_targets)

    def test_corrupted_file_skipped_not_fatal(self, tmp_path, spec_targets):
        """A file that fails to parse is skipped with a warning, not a crash."""
        good = tmp_path / "good.psf"
        good.write_text(
            '// Spectre PSF ASCII\nHEADER\n"PSFversion" "1.1"\nEND HEADER\n'
            'TYPE\n"real" FLOAT DOUBLE PROP("units" "" "scale" "LINEAR" "grid" 1)\nEND TYPE\n'
            'VALUE\n"gain_dc" FLOAT DOUBLE 6.85e+01 dB\nEND VALUE\n'
        )
        bad = tmp_path / "corrupt.psf"
        bad.write_text("this is not a valid PSF file at all !!!")
        result = CornerAggregator.aggregate(tmp_path, spec_targets)
        names = [c.name for c in result]
        assert "good" in names
        assert "corrupt" not in names

    def test_nonexistent_folder_raises(self, spec_targets):
        with pytest.raises((FileNotFoundError, OSError, ConfigError)):
            CornerAggregator.aggregate(Path("/nonexistent/folder"), spec_targets)
