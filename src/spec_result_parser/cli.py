"""CLI entry point for spec-result-parser.

Commands:
  spec-parser check     -- Check a single result file against a spec
  spec-parser aggregate -- Aggregate multi-corner results
"""
import sys
from pathlib import Path

import click

from spec_result_parser.checker import SpecChecker
from spec_result_parser.evaluator import ExpressionEvaluator
from spec_result_parser.format_detector import detect
from spec_result_parser.models import ConfigError, Format, ParseError, Waveform
from spec_result_parser.parsers.hspice_mt0 import parse_hspice_mt0
from spec_result_parser.parsers.psf_ascii import parse_psf_ascii
from spec_result_parser.parsers.psf_binary import parse as parse_psf_binary
from spec_result_parser.renderer import TerminalRenderer
from spec_result_parser.spec_loader import load_spec

_PARSERS = {
    Format.PSF_ASCII: parse_psf_ascii,
    Format.HSPICE_MT0: parse_hspice_mt0,
    Format.PSF_BINARY: parse_psf_binary,
}

_EXT_FORMAT = {".csv": "csv", ".json": "json", ".html": "html"}


def _resolve_format(output_format, output_file):
    """Return (fmt, path) or raise ConfigError."""
    if output_format is None and output_file is None:
        return None, None
    if output_format is None and output_file is not None:
        ext = Path(output_file).suffix.lower()
        fmt = _EXT_FORMAT.get(ext)
        if fmt is None:
            raise ConfigError(
                f"Cannot detect format from '{ext}'. Use --format [csv|json|html]"
            )
        return fmt, output_file
    if output_format == "html" and output_file is None:
        raise ConfigError("HTML output requires --output <file.html>")
    return output_format, output_file


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
@click.option("--format", "output_format", type=click.Choice(["csv", "json", "html"]),
              default=None, help="Output format.")
@click.option("--output", "output_file", type=click.Path(), default=None,
              help="Output file path.")
@click.option("--quiet", is_flag=True, help="Suppress terminal output.")
def check(result_file: str, spec: str, margin_threshold: float, verbose: bool,
          output_format, output_file, quiet) -> None:
    """Check RESULT_FILE against spec targets and print PASS/FAIL table.

    RESULT_FILE: Path to a PSF-ASCII (.psf) or HSPICE MT0 (.mt0) result file.

    Exit codes:
      0 — all specs PASS
      1 — one or more FAIL
      2 — file parse error or config error
    """
    # Validate format/output BEFORE parsing (early exit on error)
    try:
        fmt, out_path = _resolve_format(output_format, output_file)
    except ConfigError as exc:
        click.echo(f"Error: {exc}")
        sys.exit(2)

    path = Path(result_file)

    try:
        detected_fmt = detect(path)
        if detected_fmt is None:
            raise ConfigError(f"Unsupported file format: {path.suffix!r}")

        if detected_fmt not in _PARSERS:
            raise ConfigError(f"No parser for format: {detected_fmt}")

        parse_fn = _PARSERS[detected_fmt]
        raw = parse_fn(path)
        spec_targets = load_spec(spec)

        # For binary PSF, signals may include Waveforms — evaluate expressions
        if detected_fmt == Format.PSF_BINARY:
            signals = raw  # dict[str, Measurement|Waveform]
            measurements = []
            for target in spec_targets.values():
                if target.measure is not None:
                    m = ExpressionEvaluator.evaluate(target, signals)
                    if m is not None:
                        measurements.append(m)
                elif target.name in signals:
                    sig = signals[target.name]
                    if not isinstance(sig, Waveform):
                        measurements.append(sig)
        else:
            measurements = raw  # List[Measurement] from ascii/mt0 parsers
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

    if not quiet:
        TerminalRenderer.render_single(checks)

    if fmt == "csv":
        from spec_result_parser.exporters.csv_exporter import export_single as csv_export
        csv_export(checks, out_path)
    elif fmt == "json":
        from spec_result_parser.exporters.json_exporter import export_single as json_export
        json_export(checks, out_path, spec_file=spec, result_file=result_file)
    elif fmt == "html":
        from spec_result_parser.exporters.html_exporter import export_single as html_export
        html_export(checks, out_path)

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
@click.option("--format", "output_format", type=click.Choice(["csv", "json", "html"]),
              default=None, help="Output format.")
@click.option("--output", "output_file", type=click.Path(), default=None,
              help="Output file path.")
@click.option("--quiet", is_flag=True, help="Suppress terminal output.")
def aggregate(folder: str, spec: str, corners: str, margin_threshold: float,
              verbose: bool, output_format, output_file, quiet) -> None:
    """Aggregate multi-corner results from FOLDER and print corner matrix.

    FOLDER: Directory containing PSF-ASCII (.psf) or HSPICE MT0 (.mt0) files.
    Each file represents one PVT corner.

    Exit codes:
      0 — all corners PASS all specs
      1 — one or more corners FAIL
      2 — error reading files or spec
    """
    from spec_result_parser.corner_aggregator import CornerAggregator
    from spec_result_parser.models import Status

    # Validate format/output BEFORE parsing (early exit on error)
    try:
        fmt, out_path = _resolve_format(output_format, output_file)
    except ConfigError as exc:
        click.echo(f"Error: {exc}")
        sys.exit(2)

    try:
        spec_targets = load_spec(spec)
        corner_list = CornerAggregator.aggregate(Path(folder), spec_targets)
    except (ConfigError, ParseError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    if not quiet:
        TerminalRenderer.render_corners(corner_list)

    if fmt == "csv":
        from spec_result_parser.exporters.csv_exporter import export_corners as csv_export
        csv_export(corner_list, out_path)
    elif fmt == "json":
        from spec_result_parser.exporters.json_exporter import export_corners as json_export
        json_export(corner_list, out_path, spec_file=spec, result_folder=folder)
    elif fmt == "html":
        from spec_result_parser.exporters.html_exporter import export_corners as html_export
        html_export(corner_list, out_path)

    has_fail = any(c.overall_status == Status.FAIL for c in corner_list)
    sys.exit(1 if has_fail else 0)



@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--spec", "-s", required=True, type=click.Path(exists=True),
              help="YAML or CSV spec file with min/max targets.")
@click.option("--n-sigma", default=3.0, show_default=True,
              help="Sigma multiplier for status band (3 = 99.73%).")
@click.option("--margin-threshold", default=10.0, show_default=True,
              help="Percentage within a limit to flag as MARGIN.")
@click.option("--format", "output_format", type=click.Choice(["csv", "json", "html"]),
              default=None, help="Output format.")
@click.option("--output", "output_file", type=click.Path(), default=None,
              help="Output file path.")
@click.option("--quiet", is_flag=True, help="Suppress terminal output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug output.")
def montecarlo(folder: str, spec: str, n_sigma: float, margin_threshold: float,
               output_format, output_file, quiet, verbose) -> None:
    """Run Monte Carlo statistical analysis on FOLDER of simulation result files.

    Each file in FOLDER is treated as one MC sample.  Computes mean, σ, Cpk,
    and estimated yield % for every spec, then shows a PASS/FAIL/MARGIN summary.

    Exit codes:
      0 — all specs PASS (mean±N·σ within bounds and Cpk ≥ 1.33)
      1 — one or more specs FAIL
      2 — error reading files or spec
    """
    from spec_result_parser.monte_carlo import MonteCarloAggregator
    from spec_result_parser.models import Status, ConfigError

    try:
        fmt, out_path = _resolve_format(output_format, output_file)
    except ConfigError as exc:
        click.echo(f"Error: {exc}")
        sys.exit(2)

    try:
        spec_targets = load_spec(spec)
        stats = MonteCarloAggregator.aggregate(
            Path(folder),
            spec_targets,
            margin_threshold=margin_threshold,
            n_sigma=n_sigma,
        )
    except (ConfigError, ParseError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    if not quiet:
        TerminalRenderer.render_montecarlo(stats)

    if fmt == "csv":
        from spec_result_parser.exporters.csv_exporter import export_montecarlo as csv_mc
        csv_mc(stats, out_path)
    elif fmt == "json":
        from spec_result_parser.exporters.json_exporter import export_montecarlo as json_mc
        json_mc(stats, out_path, spec_file=spec, mc_folder=folder)
    elif fmt == "html":
        from spec_result_parser.exporters.html_exporter import export_montecarlo as html_mc
        html_mc(stats, out_path)

    has_fail = any(s.status == Status.FAIL for s in stats)
    sys.exit(1 if has_fail else 0)


if __name__ == "__main__":
    main()
