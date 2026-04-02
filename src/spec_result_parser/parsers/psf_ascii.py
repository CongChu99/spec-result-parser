"""Parser for Cadence Spectre PSF-ASCII result files.

Format reference:
  PSF-ASCII files contain sections: HEADER, TYPE, SWEEP (optional), VALUE.
  This parser focuses on the VALUE section to extract scalar measurements.

  VALUE section line format:
    "<name>" FLOAT DOUBLE <value> [<unit>]

  Example:
    "gain_dc" FLOAT DOUBLE 6.85000e+01 dB

No external dependencies — pure Python stdlib only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Union

from spec_result_parser.models import Format, Measurement, ParseError

# Matches VALUE section scalar lines:
# "gain_dc" FLOAT DOUBLE 6.85000e+01 dB
_VALUE_LINE_RE = re.compile(
    r'^"(\w+)"\s+FLOAT\s+DOUBLE\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*(\w+)?'
)

_SECTION_START_RE = re.compile(r"^(HEADER|TYPE|SWEEP|VALUE)\s*$")
_SECTION_END_RE = re.compile(r"^END\s+(HEADER|TYPE|SWEEP|VALUE)\s*$")


def parse_psf_ascii(path: Union[str, Path]) -> List[Measurement]:
    """Parse a Spectre PSF-ASCII file and return scalar Measurement objects.

    Args:
        path: Path to the PSF-ASCII result file.

    Returns:
        List of Measurement objects from the VALUE section.

    Raises:
        ParseError: If the file is not valid PSF-ASCII format or has no scalar
                    measurements in the VALUE section.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise

    lines = text.splitlines()

    # Validate it looks like PSF-ASCII — must have HEADER or VALUE section
    upper_lines = [l.strip().upper() for l in lines]
    if "HEADER" not in upper_lines and "VALUE" not in upper_lines:
        raise ParseError(
            f"Cannot parse {path.name} as PSF-ASCII. Check file format."
        )

    measurements: List[Measurement] = []
    in_value_section = False
    in_sweep_section = False

    for raw_line in lines:
        line = raw_line.strip()

        # Track section transitions
        if _SECTION_END_RE.match(line):
            section = _SECTION_END_RE.match(line).group(1)
            if section == "VALUE":
                in_value_section = False
            elif section == "SWEEP":
                in_sweep_section = False
            continue

        if _SECTION_START_RE.match(line):
            section = _SECTION_START_RE.match(line).group(1)
            if section == "VALUE":
                in_value_section = True
                in_sweep_section = False
            elif section == "SWEEP":
                in_sweep_section = True
                in_value_section = False
            continue

        # Only parse lines inside VALUE section (skip SWEEP)
        if not in_value_section or in_sweep_section:
            continue

        m = _VALUE_LINE_RE.match(line)
        if m:
            name = m.group(1)
            value = float(m.group(2))
            unit: str | None = m.group(3) if m.group(3) else None
            measurements.append(
                Measurement(name=name, value=value, unit=unit, fmt=Format.PSF_ASCII)
            )

    if not measurements:
        raise ParseError(
            f"No scalar measurements found in {path.name}. "
            "Only scalar PSF sections are supported."
        )

    return measurements
