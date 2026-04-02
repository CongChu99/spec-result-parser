"""Tests for tools-7yx.7: FormatDetector — auto-detect simulation file format."""
import pytest
from pathlib import Path
from spec_result_parser.format_detector import detect
from spec_result_parser.models import Format


class TestExtensionDetection:
    def test_psf_extension_returns_psf_ascii(self, tmp_path):
        f = tmp_path / "result.psf"
        f.write_text("")
        assert detect(f) == Format.PSF_ASCII

    def test_mt0_extension_returns_hspice_mt0(self, tmp_path):
        f = tmp_path / "result.mt0"
        f.write_text("")
        assert detect(f) == Format.HSPICE_MT0

    def test_psf_case_insensitive(self, tmp_path):
        f = tmp_path / "result.PSF"
        f.write_text("")
        assert detect(f) == Format.PSF_ASCII

    def test_mt0_case_insensitive(self, tmp_path):
        f = tmp_path / "result.MT0"
        f.write_text("")
        assert detect(f) == Format.HSPICE_MT0

    def test_tr0_returns_none(self, tmp_path):
        f = tmp_path / "result.tr0"
        f.write_text("")
        assert detect(f) is None

    def test_bin_returns_none(self, tmp_path):
        f = tmp_path / "result.bin"
        f.write_text("")
        assert detect(f) is None

    def test_no_extension_returns_none(self, tmp_path):
        f = tmp_path / "result"
        f.write_text("")
        assert detect(f) is None

    def test_unknown_extension_returns_none(self, tmp_path):
        f = tmp_path / "result.csv"
        f.write_text("")
        assert detect(f) is None

    def test_accepts_string_path(self, tmp_path):
        f = tmp_path / "result.psf"
        f.write_text("")
        assert detect(str(f)) == Format.PSF_ASCII


class TestHeaderSniff:
    """Header sniff validates PSF-ASCII by checking first lines for PSF markers."""

    def test_psf_with_valid_header_passes(self, tmp_path):
        f = tmp_path / "result.psf"
        f.write_text('HEADER\n"PSF version" "1.1"\n')
        assert detect(f) == Format.PSF_ASCII

    def test_psf_with_invalid_header_returns_none(self, tmp_path):
        """Extension says PSF but header looks like binary/wrong format → None."""
        f = tmp_path / "result.psf"
        f.write_bytes(b"\x00\x01\x02\x03binary data")
        assert detect(f) is None

    def test_mt0_with_valid_header_passes(self, tmp_path):
        f = tmp_path / "result.mt0"
        f.write_text(".title HSPICE simulation\n$\n")
        assert detect(f) == Format.HSPICE_MT0

    def test_mt0_empty_file_still_valid(self, tmp_path):
        """Empty MT0 file — extension is enough, no header required."""
        f = tmp_path / "result.mt0"
        f.write_text("")
        assert detect(f) == Format.HSPICE_MT0

    def test_nonexistent_file_raises(self):
        with pytest.raises((FileNotFoundError, OSError)):
            detect(Path("/nonexistent/path/result.psf"))
