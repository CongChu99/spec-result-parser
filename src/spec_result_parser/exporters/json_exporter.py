"""JSON exporter for spec check results."""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from typing import List, Optional, Union
from pathlib import Path

from spec_result_parser.models import Corner, SpecCheck, Status

try:
    from importlib.metadata import version as _pkg_version
    _VERSION = _pkg_version("spec-result-parser")
except Exception:
    _VERSION = "unknown"


def _build_single_payload(
    checks: List[SpecCheck],
    spec_file: str = "",
    result_file: str = "",
    version: str = _VERSION,
) -> dict:
    total = len(checks)
    pass_n = sum(1 for c in checks if c.status == Status.PASS)
    fail_n = sum(1 for c in checks if c.status == Status.FAIL)
    margin_n = sum(1 for c in checks if c.status == Status.MARGIN)
    overall = "FAIL" if fail_n else ("MARGIN" if margin_n else "PASS")

    return {
        "meta": {
            "tool": "spec-result-parser",
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spec_file": spec_file,
            "result_file": result_file,
        },
        "summary": {
            "total": total,
            "pass": pass_n,
            "fail": fail_n,
            "margin": margin_n,
            "overall": overall,
        },
        "results": [_check_to_dict(c) for c in checks],
    }


def _check_to_dict(c: SpecCheck) -> dict:
    m = c.measurement
    spec = c.spec
    return {
        "spec": m.name,
        "value": m.value,
        "unit": m.unit,
        "min": spec.min_val if spec else None,
        "max": spec.max_val if spec else None,
        "status": c.status.value,
        "margin_pct": c.margin_pct,
    }


def export_single(
    checks: List[SpecCheck],
    dest=None,
    spec_file: str = "",
    result_file: str = "",
    version: str = _VERSION,
) -> None:
    payload = _build_single_payload(checks, spec_file, result_file, version)
    _write_json(payload, dest)


def export_corners(
    corners: List[Corner],
    dest=None,
    spec_file: str = "",
    result_folder: str = "",
    version: str = _VERSION,
) -> None:
    all_checks = [ch for c in corners for ch in c.checks]
    payload = _build_single_payload(all_checks, spec_file=spec_file, result_file=result_folder, version=version)
    payload["corners"] = [
        {
            "name": c.name,
            "overall": c.overall_status.value,
            "results": [_check_to_dict(ch) for ch in c.checks],
        }
        for c in corners
    ]
    _write_json(payload, dest)


def _write_json(payload: dict, dest) -> None:
    text = json.dumps(payload, indent=2, default=str)
    if dest is None:
        print(text)
    elif hasattr(dest, "write"):
        dest.write(text)
    else:
        Path(dest).write_text(text, encoding="utf-8")
