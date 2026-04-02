"""Tests for tools-7yx.5: Spec config loader (YAML + CSV)."""
import pytest
from pathlib import Path

from spec_result_parser.spec_loader import load_spec
from spec_result_parser.models import SpecTarget, ConfigError

FIXTURES = Path(__file__).parent / "fixtures" / "specs"


class TestYamlSpecLoader:
    def test_load_yaml_returns_dict(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        assert isinstance(targets, dict)

    def test_yaml_target_count(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        assert len(targets) == 5

    def test_yaml_gain_dc_min(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        assert targets["gain_dc"].min_val == pytest.approx(60.0)

    def test_yaml_gain_dc_max_none(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        assert targets["gain_dc"].max_val is None

    def test_yaml_ugbw_min_scientific(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        assert targets["ugbw"].min_val == pytest.approx(10_000_000.0, rel=1e-3)

    def test_yaml_offset_max_only(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        assert targets["offset_v"].min_val is None
        assert targets["offset_v"].max_val == pytest.approx(0.005, rel=1e-3)

    def test_yaml_unit_preserved(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        assert targets["gain_dc"].unit == "dB"
        assert targets["pm"].unit == "deg"

    def test_yaml_returns_spec_target_objects(self):
        targets = load_spec(FIXTURES / "opamp.spec.yaml")
        for v in targets.values():
            assert isinstance(v, SpecTarget)

    def test_yaml_missing_file_raises_config_error(self, tmp_path):
        with pytest.raises(ConfigError, match="Cannot load spec file"):
            load_spec(tmp_path / "nonexistent.yaml")

    def test_yaml_malformed_raises_config_error(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("specs:\n  gain: [ unclosed bracket\n")
        with pytest.raises(ConfigError):
            load_spec(bad)

    def test_yaml_missing_specs_key_raises_config_error(self, tmp_path):
        bad = tmp_path / "bad2.yaml"
        bad.write_text("something_else:\n  gain_dc: 60\n")
        with pytest.raises(ConfigError, match="missing 'specs' key"):
            load_spec(bad)


class TestCsvSpecLoader:
    def test_load_csv_returns_dict(self):
        targets = load_spec(FIXTURES / "opamp.spec.csv")
        assert isinstance(targets, dict)

    def test_csv_target_count(self):
        targets = load_spec(FIXTURES / "opamp.spec.csv")
        assert len(targets) == 5

    def test_csv_gain_dc_min(self):
        targets = load_spec(FIXTURES / "opamp.spec.csv")
        assert targets["gain_dc"].min_val == pytest.approx(60.0)
        assert targets["gain_dc"].max_val is None

    def test_csv_offset_max_only(self):
        targets = load_spec(FIXTURES / "opamp.spec.csv")
        assert targets["offset_v"].min_val is None
        assert targets["offset_v"].max_val == pytest.approx(0.005, rel=1e-3)

    def test_csv_ugbw_scientific(self):
        targets = load_spec(FIXTURES / "opamp.spec.csv")
        assert targets["ugbw"].min_val == pytest.approx(10_000_000.0, rel=1e-3)

    def test_csv_unit_preserved(self):
        targets = load_spec(FIXTURES / "opamp.spec.csv")
        assert targets["gain_dc"].unit == "dB"

    def test_csv_missing_file_raises_config_error(self, tmp_path):
        with pytest.raises(ConfigError, match="Cannot load spec file"):
            load_spec(tmp_path / "nonexistent.csv")

    def test_csv_missing_columns_raises_config_error(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("name,limit\ngain_dc,60\n")
        with pytest.raises(ConfigError, match="missing required columns"):
            load_spec(bad)

    def test_unknown_extension_raises_config_error(self, tmp_path):
        bad = tmp_path / "spec.txt"
        bad.write_text("gain_dc=60\n")
        with pytest.raises(ConfigError, match="Unsupported spec file format"):
            load_spec(bad)
