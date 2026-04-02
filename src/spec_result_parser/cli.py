"""CLI entry point for spec-result-parser.

Commands:
  spec-parser check     -- Check a single result file against a spec
  spec-parser aggregate -- Aggregate multi-corner results
"""
import sys
import click


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
    click.echo("TODO: check not yet implemented")
    sys.exit(0)


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
    click.echo("TODO: aggregate not yet implemented")
    sys.exit(0)


if __name__ == "__main__":
    main()
