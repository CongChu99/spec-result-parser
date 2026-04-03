"""FormatDetector — auto-detect simulation file format from extension + optional header sniff."""
from __future__ import annotations

import struct
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
_PSF_BINARY_MAGIC = struct.pack(">I", 1)   # 0x00 0x00 0x00 0x01


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

    # Header sniff for PSF-ASCII: check magic bytes FIRST, then reject other binary files
    if fmt == Format.PSF_ASCII:
        raw = path.read_bytes()
        header = raw[:_PSF_BINARY_CHECK_BYTES]
        # Check magic bytes FIRST — binary PSF starts with 0x00000001
        if header[:4] == _PSF_BINARY_MAGIC:
            return Format.PSF_BINARY
        # Reject other binary files
        if b"\x00" in header:
            return None

    return fmt
