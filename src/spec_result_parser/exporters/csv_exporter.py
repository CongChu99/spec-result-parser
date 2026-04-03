"""CSV exporter for spec check results."""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from typing import List, Union

from spec_result_parser.models import Corner, SpecCheck


_SINGLE_FIELDS = ["spec", "value", "unit", "min", "max", "status", "margin_pct"]


def export_single(
    checks: List[SpecCheck],
    dest: Union[str, Path, io.IOBase, None] = None,
) -> None:
    """Write single-file check results to CSV.

    Args:
        checks: List of SpecCheck results.
        dest: File path, open file object, or None for stdout.
    """
    _write_single(checks, dest)


def export_corners(
    corners: List[Corner],
    dest: Union[str, Path, io.IOBase, None] = None,
) -> None:
    """Write corner aggregation results to CSV.

    Args:
        corners: List of Corner objects.
        dest: File path, open file object, or None for stdout.
    """
    _write_corners(corners, dest)


def _write_single(checks: List[SpecCheck], dest) -> None:
    def _rows():
        for ch in checks:
            m = ch.measurement
            spec = ch.spec
            yield {
                "spec": m.name,
                "value": m.value,
                "unit": m.unit or "",
                "min": spec.min_val if spec else "",
                "max": spec.max_val if spec else "",
                "status": ch.status.value,
                "margin_pct": f"{ch.margin_pct:.1f}" if ch.margin_pct is not None else "",
            }

    _write_csv(_SINGLE_FIELDS, list(_rows()), dest)


def _write_corners(corners: List[Corner], dest) -> None:
    if not corners:
        return
    spec_names = [ch.measurement.name for ch in corners[0].checks]
    fields = ["corner", "overall"] + spec_names

    rows = []
    for corner in corners:
        checks_by_name = {ch.measurement.name: ch for ch in corner.checks}
        row = {"corner": corner.name, "overall": corner.overall_status.value}
        for name in spec_names:
            ch = checks_by_name.get(name)
            row[name] = ch.status.value if ch else "N/A"
        rows.append(row)

    _write_csv(fields, rows, dest)


def _write_csv(fields: List[str], rows: List[dict], dest) -> None:
    if dest is None or dest is sys.stdout:
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    elif hasattr(dest, "write"):
        writer = csv.DictWriter(dest, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    else:
        with open(dest, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
