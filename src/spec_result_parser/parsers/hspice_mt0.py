"""Parser for HSPICE MT0 / printfile simulation results.

Format: Plain ASCII with name=value pairs, one per line.
Comment lines start with '$' or '*' or '.option'.

Example:
    $ HSPICE Opamp TT corner
    gain_dc=6.85000e+01
    ugbw=1.25000e+07
    pm=6.72300e+01

No external dependencies — pure Python stdlib only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Union

from spec_result_parser.models import Format, Measurement, ParseError

# Matches: name=value (scientific notation, signed floats)
_MEASURE_RE = re.compile(
    r"^(\w+)\s*=\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*$"
)

# Lines to skip: comments, directives, blank
_SKIP_RE = re.compile(r"^\s*($|\$|\*|\.)")


def parse_hspice_mt0(path: Union[str, Path]) -> List[Measurement]:
    """Parse a HSPICE MT0 / printfile and return scalar Measurement objects.

    Args:
        path: Path to the HSPICE MT0 result file.

    Returns:
        List of Measurement objects (unit is always None — MT0 has no unit info).

    Raises:
        ParseError: If the file contains no valid measurement lines.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise

    lines = text.splitlines()
    measurements: List[Measurement] = []

    for raw_line in lines:
        line = raw_line.strip()

        # Skip comment / blank / directive lines
        if _SKIP_RE.match(line):
            continue

        m = _MEASURE_RE.match(line)
        if m:
            name = m.group(1)
            value = float(m.group(2))
            measurements.append(
                Measurement(name=name, value=value, unit=None, fmt=Format.HSPICE_MT0)
            )

    if not measurements:
        # Check if file had ANY parseable content at all
        non_blank = [l.strip() for l in lines if l.strip() and not _SKIP_RE.match(l.strip())]
        if non_blank:
            raise ParseError(
                f"Cannot parse {path.name} as HSPICE MT0. Check file format."
            )
        raise ParseError(
            f"No measurements found in {path.name}."
        )

    return measurements
