"""
Core data models for spec-result-parser.

All dataclasses are frozen (immutable value objects). These types form the
shared contract between parsers, spec loader, checker, aggregator, and renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Format(Enum):
    """Supported simulation result file formats."""

    PSF_ASCII = "psf_ascii"
    HSPICE_MT0 = "hspice_mt0"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> "Format":
        """Auto-detect format from file extension (case-insensitive)."""
        mapping = {
            ".psf": cls.PSF_ASCII,
            ".mt0": cls.HSPICE_MT0,
        }
        return mapping.get(ext.lower(), cls.UNKNOWN)


class Status(Enum):
    """Spec check status for a single measurement."""

    PASS = "PASS"
    FAIL = "FAIL"
    MARGIN = "MARGIN"  # within margin_threshold% of a limit
    NA = "N/A"  # spec not defined for this measurement


# ---------------------------------------------------------------------------
# Core value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Measurement:
    """A single scalar value extracted from a simulation result file."""

    name: str
    value: float
    unit: Optional[str]
    fmt: Format


@dataclass(frozen=True)
class SpecTarget:
    """Min/max bounds for a single measurement from a spec file."""

    name: str
    min_val: Optional[float]
    max_val: Optional[float]
    unit: Optional[str]


@dataclass(frozen=True)
class SpecCheck:
    """Result of checking one Measurement against one SpecTarget."""

    measurement: Measurement
    spec: Optional[SpecTarget]        # None when status is NA
    status: Status
    margin_pct: Optional[float]       # % distance from nearest limit; None for NA


# ---------------------------------------------------------------------------
# Corner (multi-corner aggregation)
# ---------------------------------------------------------------------------


@dataclass
class Corner:
    """All spec checks for one PVT corner (one result file)."""

    name: str
    checks: List[SpecCheck]

    @property
    def overall_status(self) -> Status:
        """Worst status across all checks in this corner.

        Priority: FAIL > MARGIN > PASS > NA
        """
        statuses = {c.status for c in self.checks}
        if Status.FAIL in statuses:
            return Status.FAIL
        if Status.MARGIN in statuses:
            return Status.MARGIN
        if Status.PASS in statuses:
            return Status.PASS
        return Status.NA


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ParseError(Exception):
    """Raised when a result file cannot be parsed."""


class ConfigError(Exception):
    """Raised when a spec file is missing, malformed, or invalid."""
