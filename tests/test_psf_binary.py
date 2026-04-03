"""Tests for binary PSF parser."""
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from spec_result_parser.models import Format, Measurement, ParseError, Waveform


def test_libpsf_absent_raises_parse_error(tmp_path):
    """When libpsf is not installed, raise ParseError with install hint."""
    f = tmp_path / "result.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\x00" * 10)

    import sys
    sys.modules.pop("spec_result_parser.parsers.psf_binary", None)

    with patch.dict("sys.modules", {"libpsf": None}):
        from spec_result_parser.parsers.psf_binary import parse
        with pytest.raises(ParseError, match=r"pip install spec-result-parser\[binary\]"):
            parse(f)


def test_parse_scalar_returns_measurement(tmp_path):
    """Scalar-only PSF file returns dict of Measurement objects."""
    f = tmp_path / "result.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\x00" * 10)

    mock_psf = MagicMock()
    mock_psf.get_signal_names.return_value = ["gain_dc"]
    mock_psf.get_signal.return_value = MagicMock(
        is_swept=False, value=68.5, units="dB"
    )

    import sys
    sys.modules.pop("spec_result_parser.parsers.psf_binary", None)

    with patch("spec_result_parser.parsers.psf_binary._load_libpsf", return_value=mock_psf):
        from spec_result_parser.parsers.psf_binary import parse
        result = parse(f)

    assert "gain_dc" in result
    assert isinstance(result["gain_dc"], Measurement)
    assert result["gain_dc"].value == 68.5
    assert result["gain_dc"].unit == "dB"
    assert result["gain_dc"].fmt == Format.PSF_BINARY


def test_parse_waveform_returns_waveform(tmp_path):
    """Swept signal returns Waveform object."""
    f = tmp_path / "result.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\x00" * 10)

    mock_signal = MagicMock()
    mock_signal.is_swept = True
    mock_signal.sweep_param = "freq"
    mock_signal.abscissa = np.array([1e6, 2e6, 3e6])
    mock_signal.ordinate = np.array([0.5, 0.3, 0.1])
    mock_signal.units = "V"

    mock_psf = MagicMock()
    mock_psf.get_signal_names.return_value = ["vout"]
    mock_psf.get_signal.return_value = mock_signal

    import sys
    sys.modules.pop("spec_result_parser.parsers.psf_binary", None)

    with patch("spec_result_parser.parsers.psf_binary._load_libpsf", return_value=mock_psf):
        from spec_result_parser.parsers.psf_binary import parse
        result = parse(f)

    assert "vout" in result
    w = result["vout"]
    assert isinstance(w, Waveform)
    assert w.sweep_var == "freq"
    np.testing.assert_array_equal(w.x, [1e6, 2e6, 3e6])
    assert w.unit == "V"


def test_parse_missing_file_raises():
    import sys
    sys.modules.pop("spec_result_parser.parsers.psf_binary", None)
    with pytest.raises((FileNotFoundError, ParseError)):
        from spec_result_parser.parsers.psf_binary import parse
        parse("/nonexistent/path.psf")


def test_parse_corrupt_file_raises(tmp_path):
    f = tmp_path / "bad.psf"
    f.write_bytes(struct.pack(">I", 1) + b"\xff\xfe\xfd")

    mock_psf_module = MagicMock()
    mock_psf_module.PSFDataSet.side_effect = Exception("corrupt data")

    import sys
    sys.modules.pop("spec_result_parser.parsers.psf_binary", None)

    with patch.dict("sys.modules", {"libpsf": mock_psf_module}):
        from spec_result_parser.parsers.psf_binary import parse
        with pytest.raises(ParseError, match="Cannot parse binary PSF"):
            parse(f)
