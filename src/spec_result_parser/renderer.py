"""TerminalRenderer — rich color table output for spec check results."""
from __future__ import annotations

from typing import List, Optional

from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich import box

from spec_result_parser.models import Corner, McSpecStat, SpecCheck, Status

_STATUS_STYLE = {
    Status.PASS: Style(color="green", bold=True),
    Status.FAIL: Style(color="red", bold=True),
    Status.MARGIN: Style(color="yellow", bold=True),
    Status.NA: Style(color="white", dim=True),
}
_FAIL_ROW_STYLE = Style(bgcolor="#4D1C1C")
_WORST_ROW_STYLE = Style(bgcolor="#1A1000")

_DEFAULT_CONSOLE = Console()


def _fmt_value(value: float, unit: str) -> str:
    if abs(value) >= 1e6:
        return f"{value/1e6:.3g}M{unit}"
    if abs(value) >= 1e3:
        return f"{value/1e3:.3g}k{unit}"
    return f"{value:.4g} {unit}"


def _fmt_margin(margin_pct: Optional[float]) -> str:
    if margin_pct is None:
        return "—"
    return f"{margin_pct:+.1f}%"


def _fmt_bound(val: Optional[float], unit: str) -> str:
    if val is None:
        return "—"
    return _fmt_value(val, unit)


class TerminalRenderer:
    """Render SpecCheck results as colored rich tables."""

    @classmethod
    def render_single(
        cls,
        checks: List[SpecCheck],
        console: Optional[Console] = None,
    ) -> None:
        """Render a single-file check result table.

        Args:
            checks: List of SpecCheck results from SpecChecker.
            console: Rich Console to render to (default: stdout).
        """
        con = console or _DEFAULT_CONSOLE

        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold white",
        )
        table.add_column("Spec", style="bold")
        table.add_column("Value", justify="right")
        table.add_column("Min", justify="right")
        table.add_column("Max", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Margin", justify="right")

        for check in checks:
            m = check.measurement
            unit = m.unit or ""
            spec = check.spec
            status_label = check.status.value.upper()
            if check.status == Status.NA:
                status_label = "N/A"

            row_style = _FAIL_ROW_STYLE if check.status == Status.FAIL else None

            table.add_row(
                m.name,
                _fmt_value(m.value, unit),
                _fmt_bound(spec.min_val if spec else None, unit),
                _fmt_bound(spec.max_val if spec else None, unit),
                f"[{_STATUS_STYLE[check.status]}]{status_label}[/]",
                _fmt_margin(check.margin_pct),
                style=row_style,
            )

        con.print(table)
        cls._print_single_summary(checks, con)

    @classmethod
    def render_corners(
        cls,
        corners: List[Corner],
        console: Optional[Console] = None,
    ) -> None:
        """Render a corner×spec matrix table with worst-case row.

        Args:
            corners: List of Corner objects from CornerAggregator.
            console: Rich Console to render to (default: stdout).
        """
        con = console or _DEFAULT_CONSOLE

        if not corners:
            con.print("[yellow]No corners to display.[/yellow]")
            return

        # Collect spec names from first corner
        spec_names = [ch.measurement.name for ch in corners[0].checks]

        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold white")
        table.add_column("Corner", style="bold")
        for name in spec_names:
            table.add_column(name, justify="center")
        table.add_column("Overall", justify="center")

        all_fail_count = 0

        for corner in corners:
            checks_by_name = {ch.measurement.name: ch for ch in corner.checks}
            row = [corner.name]
            has_fail = corner.overall_status == Status.FAIL
            if has_fail:
                all_fail_count += 1

            for name in spec_names:
                ch = checks_by_name.get(name)
                if ch is None:
                    row.append("—")
                else:
                    label = ch.status.value.upper()
                    if ch.status == Status.NA:
                        label = "N/A"
                    margin = f"\n{_fmt_margin(ch.margin_pct)}" if ch.margin_pct is not None else ""
                    row.append(f"[{_STATUS_STYLE[ch.status]}]{label}[/]{margin}")

            overall_label = corner.overall_status.value.upper()
            row.append(f"[{_STATUS_STYLE[corner.overall_status]}]{overall_label}[/]")

            row_style = _FAIL_ROW_STYLE if has_fail else None
            table.add_row(*row, style=row_style)

        # Worst-case row: worst status per spec across all corners
        worst_row = ["[bold]Worst Case[/bold]"]
        for name in spec_names:
            col_checks = [
                ch for corner in corners
                for ch in corner.checks if ch.measurement.name == name
            ]
            if not col_checks:
                worst_row.append("—")
                continue
            worst = min(col_checks, key=lambda c: c.margin_pct if c.margin_pct is not None else float("inf"))
            label = worst.status.value.upper()
            if worst.status == Status.NA:
                label = "N/A"
            worst_row.append(f"[{_STATUS_STYLE[worst.status]}]{label}[/]")

        worst_overall = max(
            (c.overall_status for c in corners),
            key=lambda s: [Status.FAIL, Status.MARGIN, Status.PASS, Status.NA].index(s)
            if s in [Status.FAIL, Status.MARGIN, Status.PASS, Status.NA] else 99,
        )
        worst_row.append(f"[{_STATUS_STYLE[worst_overall]}]{worst_overall.value.upper()}[/]")
        table.add_row(*worst_row, style=_WORST_ROW_STYLE)

        con.print(table)
        cls._print_corners_summary(corners, all_fail_count, con)

    @staticmethod
    def _print_single_summary(checks: List[SpecCheck], con: Console) -> None:
        total = len(checks)
        fail_count = sum(1 for c in checks if c.status == Status.FAIL)
        pass_count = sum(1 for c in checks if c.status == Status.PASS)

        if fail_count == 0:
            con.print(f"[bold green]✓ All {total} specs: PASS[/bold green]")
        else:
            con.print(f"[bold red]✗ {fail_count} of {total} specs: FAIL[/bold red]")

    @staticmethod
    def _print_corners_summary(corners: List[Corner], fail_count: int, con: Console) -> None:
        total = len(corners)
        if fail_count == 0:
            con.print(f"[bold green]✓ All {total} corners: PASS[/bold green]")
        else:
            con.print(f"[bold red]✗ {fail_count} of {total} corners have FAIL[/bold red]")

    @classmethod
    def render_montecarlo(
        cls,
        stats: List[McSpecStat],
        console: Optional[Console] = None,
    ) -> None:
        """Render Monte Carlo statistical summary table.

        Columns: Spec | N | Mean | Std (σ) | Min | Max | Cpk | Yield % | Status
        """
        con = console or _DEFAULT_CONSOLE

        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold white")
        table.add_column("Spec", style="bold")
        table.add_column("N", justify="right")
        table.add_column("Mean", justify="right")
        table.add_column("σ", justify="right")
        table.add_column("Min", justify="right")
        table.add_column("Max", justify="right")
        table.add_column("Cpk", justify="right")
        table.add_column("Yield %", justify="right")
        table.add_column("Status", justify="center")

        fail_count = 0
        for stat in stats:
            unit = stat.unit or ""
            style = _FAIL_ROW_STYLE if stat.status == Status.FAIL else None

            cpk_str = f"{stat.cpk:.2f}" if stat.cpk is not None else "—"
            yield_str = f"{stat.yield_pct:.2f}%" if stat.yield_pct is not None else "—"
            status_label = stat.status.value.upper()
            if stat.status == Status.NA:
                status_label = "N/A"
            if stat.status == Status.FAIL:
                fail_count += 1

            table.add_row(
                stat.name,
                str(stat.n),
                _fmt_value(stat.mean, unit),
                _fmt_value(stat.std, unit),
                _fmt_value(stat.min_val, unit),
                _fmt_value(stat.max_val, unit),
                cpk_str,
                yield_str,
                f"[{_STATUS_STYLE[stat.status]}]{status_label}[/]",
                style=style,
            )

        con.print(table)

        total = len(stats)
        if fail_count == 0:
            con.print(f"[bold green]✓ Monte Carlo: {total} specs checked, all PASS[/bold green]")
        else:
            con.print(f"[bold red]✗ Monte Carlo: {fail_count} of {total} specs FAIL[/bold red]")
