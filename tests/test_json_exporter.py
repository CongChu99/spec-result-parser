"""Tests for JSON exporter."""
import io
import json
import pytest
from spec_result_parser.models import (
    Corner, Format, Measurement, SpecCheck, SpecTarget, Status
)
from spec_result_parser.exporters.json_exporter import export_single, export_corners


def _make_check(name, value, status, margin_pct=None, min_val=None):
    m = Measurement(name=name, value=value, unit="dB", fmt=Format.PSF_ASCII)
    spec = SpecTarget(name=name, min_val=min_val, max_val=None, unit="dB")
    return SpecCheck(measurement=m, spec=spec, status=status, margin_pct=margin_pct)


def test_export_single_schema():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    buf = io.StringIO()
    export_single(checks, buf, spec_file="opamp.yaml", result_file="result.psf", version="0.2.0")
    buf.seek(0)
    data = json.load(buf)
    assert "meta" in data
    assert data["meta"]["tool"] == "spec-result-parser"
    assert data["meta"]["version"] == "0.2.0"
    assert data["meta"]["spec_file"] == "opamp.yaml"
    assert data["meta"]["result_file"] == "result.psf"
    assert "timestamp" in data["meta"]
    assert "summary" in data
    assert data["summary"]["total"] == 1
    assert data["summary"]["pass"] == 1
    assert data["summary"]["fail"] == 0
    assert "results" in data
    assert "corners" not in data


def test_export_single_result_fields():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    data = json.load(buf)
    r = data["results"][0]
    assert r["spec"] == "gain_dc"
    assert r["value"] == 68.5
    assert r["status"] == "PASS"
    assert r["margin_pct"] == pytest.approx(14.2)


def test_export_corners_has_corners_key():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    corners = [Corner(name="tt_27", checks=checks)]
    buf = io.StringIO()
    export_corners(corners, buf)
    buf.seek(0)
    data = json.load(buf)
    assert "corners" in data
    assert data["corners"][0]["name"] == "tt_27"
    assert data["corners"][0]["overall"] == "PASS"


def test_export_summary_overall_fail():
    checks = [
        _make_check("gain_dc", 68.5, Status.PASS, min_val=60.0),
        _make_check("pm", 42.0, Status.FAIL, min_val=45.0),
    ]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    data = json.load(buf)
    assert data["summary"]["overall"] == "FAIL"
    assert data["summary"]["fail"] == 1
