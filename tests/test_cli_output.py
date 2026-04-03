"""Tests for --format, --output, --quiet CLI flags."""
import json
import csv
from pathlib import Path
from click.testing import CliRunner
from spec_result_parser.cli import main


def _write_psf(tmp_path):
    """Write a valid PSF-ASCII file that the parser supports."""
    f = tmp_path / "result.psf"
    f.write_text(
        '// Spectre PSF ASCII\n'
        'HEADER\n"PSFversion" "1.1"\n"simulator" "spectre"\nEND HEADER\n'
        'TYPE\n"real" FLOAT DOUBLE PROP(\n"units" ""\n"scale" "LINEAR"\n"grid" 1\n)\nEND TYPE\n'
        'VALUE\n"gain_dc" FLOAT DOUBLE 6.85000e+01 dB\nEND VALUE\n'
    )
    return f


def _write_spec(tmp_path):
    f = tmp_path / "opamp.yaml"
    f.write_text("specs:\n  gain_dc: { min: 60, max: null, unit: dB }\n")
    return f


def test_format_json_to_stdout(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--format", "json"
    ])
    assert result.exit_code == 0
    out = result.output
    start = out.find("{")
    assert start != -1
    data = json.loads(out[start:])
    assert "results" in data


def test_format_csv_to_file(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    out_file = tmp_path / "report.csv"
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file),
        "--format", "csv", "--output", str(out_file)
    ])
    assert result.exit_code == 0
    assert out_file.exists()
    rows = list(csv.DictReader(out_file.read_text().splitlines()))
    assert rows[0]["spec"] == "gain_dc"


def test_output_auto_detect_json(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--output", str(out_file)
    ])
    assert result.exit_code == 0
    data = json.loads(out_file.read_text())
    assert "results" in data


def test_html_without_output_exits_2(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--format", "html"
    ])
    assert result.exit_code == 2
    assert "HTML output requires --output" in result.output


def test_unknown_extension_exits_2(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--output", "report.xyz"
    ])
    assert result.exit_code == 2
    assert "--format" in result.output


def test_quiet_suppresses_terminal(tmp_path):
    result_file = _write_psf(tmp_path)
    spec_file = _write_spec(tmp_path)
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file),
        "--format", "json", "--output", str(out_file), "--quiet"
    ])
    assert result.exit_code == 0
    # Terminal (Rich table) should not appear in output
    assert "gain_dc" not in result.output
    # But file should still be written
    assert out_file.exists()


def test_quiet_does_not_affect_exit_code(tmp_path):
    """--quiet never changes exit code."""
    result_file = _write_psf(tmp_path)
    # Spec with failing threshold
    spec_file = tmp_path / "opamp.yaml"
    spec_file.write_text("specs:\n  gain_dc: { min: 80, max: null, unit: dB }\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "check", str(result_file), "--spec", str(spec_file), "--quiet"
    ])
    assert result.exit_code == 1   # FAIL, not 0
