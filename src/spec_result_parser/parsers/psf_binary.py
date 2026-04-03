"""Binary PSF parser using libpsf.

Requires: pip install spec-result-parser[binary]
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Union

import numpy as np

from spec_result_parser.models import Format, Measurement, ParseError, Waveform


def _load_libpsf(path: Path):
    """Load a PSF dataset via libpsf. Separated for test mocking."""
    try:
        import libpsf  # type: ignore[import]
    except ImportError:
        raise ParseError(
            "Binary PSF requires the 'binary' extra: "
            "pip install spec-result-parser[binary]"
        )
    try:
        return libpsf.PSFDataSet(str(path))
    except Exception as exc:
        raise ParseError(f"Cannot parse binary PSF file: {path.name} — {exc}") from exc


def parse(path: Union[str, Path]) -> Dict[str, Union[Measurement, Waveform]]:
    """Parse a Cadence Spectre binary PSF file.

    Returns:
        Dict mapping signal name → Measurement (scalar) or Waveform (swept).

    Raises:
        ParseError: If libpsf is not installed or file cannot be parsed.
        FileNotFoundError: If file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    dataset = _load_libpsf(path)

    result: Dict[str, Union[Measurement, Waveform]] = {}
    for name in dataset.get_signal_names():
        sig = dataset.get_signal(name)
        if sig.is_swept:
            result[name] = Waveform(
                sweep_var=sig.sweep_param,
                x=np.asarray(sig.abscissa, dtype=float),
                y=np.asarray(sig.ordinate, dtype=float),
                unit=sig.units or None,
                fmt=Format.PSF_BINARY,
            )
        else:
            result[name] = Measurement(
                name=name,
                value=float(sig.value),
                unit=sig.units or None,
                fmt=Format.PSF_BINARY,
            )

    return result
