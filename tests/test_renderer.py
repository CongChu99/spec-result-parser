"""Tests for tools-7yx.10: TerminalRenderer — rich color table output."""
import pytest
from rich.console import Console
from spec_result_parser.renderer import TerminalRenderer
from spec_result_parser.models import Format, Measurement, SpecCheck, SpecTarget, Status, Corner


def _make_check(name, value, status, margin_pct=None, min_val=None, max_val=None, unit="dB"):
    m = Measurement(name=name, value=value, unit=unit, fmt=Format.PSF_ASCII)
    spec = SpecTarget(name=name, min_val=min_val, max_val=max_val, unit=unit) if (min_val or max_val) else None
    return SpecCheck(measurement=m, spec=spec, status=status, margin_pct=margin_pct)


@pytest.fixture
def console():
    return Console(record=True, width=120)


@pytest.fixture
def pass_checks():
    return [
        _make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0),
        _make_check("ugbw", 12.5e6, Status.PASS, margin_pct=25.0, min_val=10e6, unit="Hz"),
        _make_check("pm", 67.2, Status.PASS, margin_pct=49.3, min_val=45.0, unit="deg"),
    ]


@pytest.fixture
def mixed_checks():
    return [
        _make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0),
        _make_check("ugbw", 9.5e6, Status.FAIL, margin_pct=-5.0, min_val=10e6, unit="Hz"),
        _make_check("pm", 47.0, Status.MARGIN, margin_pct=4.4, min_val=45.0, unit="deg"),
        _make_check("cmrr", 80.0, Status.NA, margin_pct=None),
    ]


class TestRenderSingle:
    def test_returns_none(self, console, pass_checks):
        result = TerminalRenderer.render_single(pass_checks, console=console)
        assert result is None  # side-effect only

    def test_output_contains_spec_names(self, console, pass_checks):
        TerminalRenderer.render_single(pass_checks, console=console)
        output = console.export_text()
        assert "gain_dc" in output
        assert "ugbw" in output
        assert "pm" in output

    def test_output_contains_status_labels(self, console, mixed_checks):
        TerminalRenderer.render_single(mixed_checks, console=console)
        output = console.export_text()
        assert "PASS" in output
        assert "FAIL" in output
        assert "MARGIN" in output
        assert "NA" in output or "N/A" in output

    def test_output_contains_values(self, console, pass_checks):
        TerminalRenderer.render_single(pass_checks, console=console)
        output = console.export_text()
        assert "68" in output  # gain_dc value

    def test_summary_all_pass(self, console, pass_checks):
        TerminalRenderer.render_single(pass_checks, console=console)
        output = console.export_text()
        assert "PASS" in output
        assert "3" in output  # count of specs

    def test_summary_with_failures(self, console, mixed_checks):
        TerminalRenderer.render_single(mixed_checks, console=console)
        output = console.export_text()
        assert "FAIL" in output

    def test_margin_pct_shown(self, console, pass_checks):
        TerminalRenderer.render_single(pass_checks, console=console)
        output = console.export_text()
        assert "14" in output  # margin_pct for gain_dc

    def test_na_check_no_spec(self, console):
        checks = [_make_check("cmrr", 80.0, Status.NA, margin_pct=None)]
        TerminalRenderer.render_single(checks, console=console)
        output = console.export_text()
        assert "cmrr" in output
        assert "NA" in output or "N/A" in output


class TestRenderCorners:
    @pytest.fixture
    def corners(self):
        return [
            Corner(name="tt_27", checks=[
                _make_check("gain_dc", 68.5, Status.PASS, margin_pct=14.2, min_val=60.0),
                _make_check("pm", 67.2, Status.PASS, margin_pct=49.3, min_val=45.0, unit="deg"),
            ]),
            Corner(name="ss_125", checks=[
                _make_check("gain_dc", 61.0, Status.MARGIN, margin_pct=1.7, min_val=60.0),
                _make_check("pm", 48.0, Status.MARGIN, margin_pct=6.7, min_val=45.0, unit="deg"),
            ]),
            Corner(name="sf_m40", checks=[
                _make_check("gain_dc", 55.0, Status.FAIL, margin_pct=-8.3, min_val=60.0),
                _make_check("pm", 42.0, Status.FAIL, margin_pct=-6.7, min_val=45.0, unit="deg"),
            ]),
        ]

    def test_output_contains_corner_names(self, console, corners):
        TerminalRenderer.render_corners(corners, console=console)
        output = console.export_text()
        assert "tt_27" in output
        assert "ss_125" in output
        assert "sf_m40" in output

    def test_output_contains_spec_names(self, console, corners):
        TerminalRenderer.render_corners(corners, console=console)
        output = console.export_text()
        assert "gain_dc" in output
        assert "pm" in output

    def test_output_contains_worst_case_row(self, console, corners):
        TerminalRenderer.render_corners(corners, console=console)
        output = console.export_text()
        assert "Worst" in output or "worst" in output or "WORST" in output

    def test_output_contains_statuses(self, console, corners):
        TerminalRenderer.render_corners(corners, console=console)
        output = console.export_text()
        assert "PASS" in output
        assert "FAIL" in output
        assert "MARGIN" in output

    def test_summary_shows_fail_count(self, console, corners):
        TerminalRenderer.render_corners(corners, console=console)
        output = console.export_text()
        assert "FAIL" in output
