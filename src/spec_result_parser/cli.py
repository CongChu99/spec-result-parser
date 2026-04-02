"""CLI entry point for spec-result-parser.

Commands:
  spec-parser check     -- Check a single result file against a spec
  spec-parser aggregate -- Aggregate multi-corner results
"""
import sys
import click

from spec_result_parser.checker import SpecChecker
from spec_result_parser.format_detector import detect
from spec_result_parser.models import ConfigError, Format, ParseError
from spec_result_parser.parsers.hspice_mt0 import parse_hspice_mt0
from spec_result_parser.parsers.psf_ascii import parse_psf_ascii
from spec_result_parser.renderer import TerminalRenderer
from spec_result_parser.spec_loader import load_spec

_PARSERS = {
    Format.PSF_ASCII: parse_psf_ascii,
    Format.HSPICE_MT0: parse_hspice_mt0,
}


@click.group()
@click.version_option()
def main() -> None:
    """spec-parser — Analog IC spec checker CLI.

    Check Spectre PSF-ASCII and HSPICE MT0 simulation results against
    engineer-defined PASS/FAIL targets.
    """


@main.command()
@click.argument("result_file", type=click.Path(exists=True))
@click.option("--spec", "-s", required=True, type=click.Path(exists=True),
              help="YAML or CSV spec file with min/max targets.")
@click.option("--margin-threshold", default=10.0, show_default=True,
              help="Percentage within a limit to flag as MARGIN.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug output.")
def check(result_file: str, spec: str, margin_threshold: float, verbose: bool) -> None:
    """Check RESULT_FILE against spec targets and print PASS/FAIL table.

    RESULT_FILE: Path to a PSF-ASCII (.psf) or HSPICE MT0 (.mt0) result file.

    Exit codes:
      0 — all specs PASS
      1 — one or more FAIL
      2 — file parse error or config error
    """
    from pathlib import Path
    path = Path(result_file)

    try:
        fmt = detect(path)
        if fmt is None:
            raise ConfigError(f"Unsupported file format: {path.suffix!r}")

        parse_fn = _PARSERS[fmt]
        measurements = parse_fn(path)
        spec_targets = load_spec(spec)
    except (ConfigError, ParseError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    checks = [
        SpecChecker.check(m, spec_targets.get(m.name), margin_threshold=margin_threshold)
        for m in measurements
    ]

    TerminalRenderer.render_single(checks)

    from spec_result_parser.models import Status
    has_fail = any(ch.status == Status.FAIL for ch in checks)
    sys.exit(1 if has_fail else 0)


@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--spec", "-s", required=True, type=click.Path(exists=True),
              help="YAML or CSV spec file with min/max targets.")
@click.option("--corners", type=click.Path(exists=True),
              help="Optional YAML file mapping filename stems to corner names.")
@click.option("--margin-threshold", default=10.0, show_default=True,
              help="Percentage within a limit to flag as MARGIN.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug output.")
def aggregate(folder: str, spec: str, corners: str, margin_threshold: float,
              verbose: bool) -> None:
    """Aggregate multi-corner results from FOLDER and print corner matrix.

    FOLDER: Directory containing PSF-ASCII (.psf) or HSPICE MT0 (.mt0) files.
    Each file represents one PVT corner.

    Exit codes:
      0 — all corners PASS all specs
      1 — one or more corners FAIL
      2 — error reading files or spec
    """
    from pathlib import Path
    from spec_result_parser.corner_aggregator import CornerAggregator
    from spec_result_parser.models import Status

    try:
        spec_targets = load_spec(spec)
        corner_list = CornerAggregator.aggregate(Path(folder), spec_targets)
    except (ConfigError, ParseError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    TerminalRenderer.render_corners(corner_list)

    has_fail = any(c.overall_status == Status.FAIL for c in corner_list)
    sys.exit(1 if has_fail else 0)


if __name__ == "__main__":
    main()
