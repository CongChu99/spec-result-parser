"""Tests for HTML exporter."""
from pathlib import Path
from spec_result_parser.models import (
    Corner, Format, Measurement, SpecCheck, SpecTarget, Status
)
from spec_result_parser.exporters.html_exporter import export_single, export_corners


def _make_check(name, value, status, margin_pct=None, min_val=None):
    m = Measurement(name=name, value=value, unit="dB", fmt=Format.PSF_ASCII)
    spec = SpecTarget(name=name, min_val=min_val, max_val=None, unit="dB")
    return SpecCheck(measurement=m, spec=spec, status=status, margin_pct=margin_pct)


def test_export_single_creates_file(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    out = tmp_path / "report.html"
    export_single(checks, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_html_contains_summary_cards(tmp_path):
    checks = [
        _make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0),
        _make_check("pm", 42.0, Status.FAIL, min_val=45.0),
    ]
    out = tmp_path / "report.html"
    export_single(checks, out)
    html = out.read_text()
    assert "PASS" in html
    assert "FAIL" in html
    assert "gain_dc" in html


def test_html_contains_table(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    out = tmp_path / "report.html"
    export_single(checks, out)
    html = out.read_text()
    assert "<table" in html.lower()


def test_html_inlines_chartjs(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    out = tmp_path / "report.html"
    export_single(checks, out)
    html = out.read_text()
    # Chart.js should be inlined, not loaded from CDN
    assert "cdn.jsdelivr.net" not in html
    assert "Chart" in html


def test_export_corners_creates_file(tmp_path):
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    corners = [Corner(name="tt_27", checks=checks)]
    out = tmp_path / "report.html"
    export_corners(corners, out)
    html = out.read_text()
    assert "tt_27" in html
