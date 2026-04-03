"""Tests for CSV exporter."""
import csv
import io
from spec_result_parser.models import (
    Corner, Format, Measurement, SpecCheck, SpecTarget, Status
)
from spec_result_parser.exporters.csv_exporter import export_single, export_corners


def _make_check(name, value, status, margin_pct=None, min_val=None, max_val=None):
    m = Measurement(name=name, value=value, unit="dB", fmt=Format.PSF_ASCII)
    spec = SpecTarget(name=name, min_val=min_val, max_val=max_val, unit="dB")
    return SpecCheck(measurement=m, spec=spec, status=status, margin_pct=margin_pct)


def test_export_single_check_mode():
    checks = [
        _make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0),
        _make_check("pm", 42.0, Status.FAIL, min_val=45.0),
    ]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    rows = list(csv.DictReader(buf))
    assert len(rows) == 2
    assert rows[0]["spec"] == "gain_dc"
    assert rows[0]["status"] == "PASS"
    assert rows[0]["margin_pct"] == "14.2"
    assert rows[1]["status"] == "FAIL"


def test_export_single_all_columns_present():
    checks = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=10.0, min_val=60.0)]
    buf = io.StringIO()
    export_single(checks, buf)
    buf.seek(0)
    reader = csv.DictReader(buf)
    assert set(reader.fieldnames) == {"spec", "value", "unit", "min", "max", "status", "margin_pct"}


def test_export_corners_aggregate_mode():
    checks1 = [_make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0)]
    checks2 = [_make_check("gain_dc", 55.0, Status.FAIL, min_val=60.0)]
    corners = [Corner(name="tt_27", checks=checks1), Corner(name="ss_125", checks=checks2)]
    buf = io.StringIO()
    export_corners(corners, buf)
    buf.seek(0)
    rows = list(csv.DictReader(buf))
    assert len(rows) == 2
    assert rows[0]["corner"] == "tt_27"
    assert rows[0]["overall"] == "PASS"
    assert rows[1]["corner"] == "ss_125"
    assert rows[1]["overall"] == "FAIL"
