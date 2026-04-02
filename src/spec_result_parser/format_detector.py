"""FormatDetector — auto-detect simulation file format from extension + optional header sniff."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from spec_result_parser.models import Format

_EXT_MAP = {
    ".psf": Format.PSF_ASCII,
    ".mt0": Format.HSPICE_MT0,
}

# PSF-ASCII files must be valid text and typically start with HEADER or a quoted string.
# If the first bytes look binary (contains null bytes), reject.
_PSF_BINARY_CHECK_BYTES = 256


def detect(filepath: Union[str, Path]) -> Optional[Format]:
    """Detect simulation file format from extension and optional header sniff.

    Args:
        filepath: Path to the simulation result file.

    Returns:
        Format enum value if recognized, None if unsupported or header mismatch.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be read.
    """
    path = Path(filepath)

    # Raises FileNotFoundError / OSError if missing
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    fmt = _EXT_MAP.get(path.suffix.lower())
    if fmt is None:
        return None

    # Header sniff for PSF-ASCII: reject binary files
    if fmt == Format.PSF_ASCII:
        raw = path.read_bytes()
        if b"\x00" in raw[:_PSF_BINARY_CHECK_BYTES]:
            return None

    return fmt
