"""CornerAggregator — multi-corner aggregation of simulation results."""
from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Dict, List, Optional

from spec_result_parser.checker import SpecChecker
from spec_result_parser.format_detector import detect
from spec_result_parser.models import ConfigError, Corner, Measurement, ParseError, SpecTarget
from spec_result_parser.parsers.hspice_mt0 import parse_hspice_mt0
from spec_result_parser.parsers.psf_ascii import parse_psf_ascii

logger = logging.getLogger(__name__)

_PARSERS = {
    "psf_ascii": parse_psf_ascii,
    "hspice_mt0": parse_hspice_mt0,
}


class CornerAggregator:
    """Aggregate multi-corner simulation results into a list of Corner objects."""

    @classmethod
    def aggregate(
        cls,
        folder: Path,
        spec_targets: Dict[str, SpecTarget],
    ) -> List[Corner]:
        """Scan folder, parse all supported files, run SpecChecker, return corners.

        Args:
            folder: Directory containing simulation result files (.psf, .mt0).
            spec_targets: Mapping of spec name → SpecTarget (from spec loader).

        Returns:
            List of Corner objects, one per successfully parsed file.

        Raises:
            FileNotFoundError: If folder does not exist.
            ConfigError: If folder is empty or contains no supported files.
        """
        folder = Path(folder)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")

        candidates = sorted(
            f for f in folder.iterdir() if f.is_file()
        )
        if not candidates:
            raise ConfigError(f"Folder is empty: {folder}")

        corners: List[Corner] = []
        skipped = 0

        for filepath in candidates:
            fmt = detect(filepath)
            if fmt is None:
                continue  # unsupported extension — skip silently

            parse_fn = _PARSERS.get(fmt.value)
            if parse_fn is None:
                continue

            try:
                measurements: List[Measurement] = parse_fn(filepath)
            except (ParseError, Exception) as exc:
                warnings.warn(
                    f"[WARN] Skipping {filepath.name}: {exc}",
                    stacklevel=2,
                )
                skipped += 1
                continue

            checks = [
                SpecChecker.check(
                    measurement=m,
                    spec=spec_targets.get(m.name),
                )
                for m in measurements
            ]

            corners.append(Corner(name=filepath.stem, checks=checks))

        if not corners:
            raise ConfigError(
                f"No supported files found in {folder} "
                f"(skipped {skipped} file(s) due to parse errors)"
            )

        return corners
