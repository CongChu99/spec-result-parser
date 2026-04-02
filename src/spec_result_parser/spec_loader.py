"""Spec config loader — reads YAML and CSV spec files into SpecTarget objects.

Supported formats:
  YAML (.yaml, .yml):
    specs:
      gain_dc:  { min: 60, max: null, unit: dB }
      ugbw:     { min: 10.0e6, max: null, unit: Hz }

  CSV (.csv):
    measurement,min,max,unit
    gain_dc,60,,dB
    ugbw,10.0e6,,Hz

Auto-detect format from file extension.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional, Union

import yaml

from spec_result_parser.models import ConfigError, SpecTarget


def load_spec(path: Union[str, Path]) -> Dict[str, SpecTarget]:
    """Load spec targets from a YAML or CSV spec file.

    Args:
        path: Path to the spec file (.yaml, .yml, or .csv).

    Returns:
        Dict mapping measurement name → SpecTarget.

    Raises:
        ConfigError: If file is missing, malformed, wrong format, or missing columns.
    """
    path = Path(path)

    if not path.exists():
        raise ConfigError(f"Cannot load spec file: {path.name}")

    ext = path.suffix.lower()
    if ext in (".yaml", ".yml"):
        return _load_yaml(path)
    elif ext == ".csv":
        return _load_csv(path)
    else:
        raise ConfigError(
            f"Unsupported spec file format: '{ext}'. Use .yaml or .csv"
        )


def _parse_float_or_none(value: Optional[object]) -> Optional[float]:
    """Parse a value to float, returning None if null/empty."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _load_yaml(path: Path) -> Dict[str, SpecTarget]:
    """Load spec from YAML file."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Cannot load spec file: {path.name} — {e}") from e

    if not isinstance(raw, dict) or "specs" not in raw:
        raise ConfigError(
            f"Cannot load spec file: {path.name} — missing 'specs' key. "
            "Expected: 'specs: {{ name: {{ min: ..., max: ..., unit: ... }} }}'"
        )

    specs_raw = raw["specs"]
    if not isinstance(specs_raw, dict):
        raise ConfigError(f"Cannot load spec file: {path.name} — 'specs' must be a mapping")

    targets: Dict[str, SpecTarget] = {}
    for name, entry in specs_raw.items():
        if not isinstance(entry, dict):
            raise ConfigError(
                f"Cannot load spec file: {path.name} — entry '{name}' must be a mapping"
            )
        targets[name] = SpecTarget(
            name=name,
            min_val=_parse_float_or_none(entry.get("min")),
            max_val=_parse_float_or_none(entry.get("max")),
            unit=entry.get("unit"),
        )

    return targets


def _load_csv(path: Path) -> Dict[str, SpecTarget]:
    """Load spec from CSV file with columns: measurement, min, max, unit."""
    required_cols = {"measurement", "min", "max", "unit"}

    try:
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])

            if not required_cols.issubset(headers):
                missing = required_cols - headers
                raise ConfigError(
                    f"Cannot load spec file: {path.name} — "
                    f"missing required columns: {sorted(missing)}"
                )

            targets: Dict[str, SpecTarget] = {}
            for row in reader:
                name = row["measurement"].strip()
                targets[name] = SpecTarget(
                    name=name,
                    min_val=_parse_float_or_none(row.get("min")),
                    max_val=_parse_float_or_none(row.get("max")),
                    unit=row.get("unit", "").strip() or None,
                )
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f"Cannot load spec file: {path.name} — {e}") from e

    return targets
