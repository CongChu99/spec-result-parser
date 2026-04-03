"""HTML dashboard exporter — produces a single self-contained HTML file."""
from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from typing import List, Union

from spec_result_parser.models import Corner, SpecCheck, Status

_STATUS_COLOR = {
    "PASS":   "#22c55e",
    "FAIL":   "#ef4444",
    "MARGIN": "#eab308",
    "N/A":    "#6b7280",
}


def _load_chartjs() -> str:
    try:
        ref = importlib.resources.files("spec_result_parser.exporters._vendor").joinpath("chart.min.js")
        return ref.read_text(encoding="utf-8")
    except Exception:
        return "/* Chart.js not found */"


def _checks_to_rows(checks: List[SpecCheck]) -> list:
    rows = []
    for ch in checks:
        m = ch.measurement
        spec = ch.spec
        rows.append({
            "spec": m.name,
            "value": f"{m.value:.4g} {m.unit or ''}".strip(),
            "min": f"{spec.min_val}" if spec and spec.min_val is not None else "—",
            "max": f"{spec.max_val}" if spec and spec.max_val is not None else "—",
            "status": ch.status.value,
            "margin": f"{ch.margin_pct:+.1f}%" if ch.margin_pct is not None else "—",
            "color": _STATUS_COLOR.get(ch.status.value, "#ffffff"),
        })
    return rows


def _render(title: str, summary: dict, rows: list, chart_data: dict, chartjs: str) -> str:
    rows_json = json.dumps(rows)
    chart_json = json.dumps(chart_data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:2rem; }}
  h1 {{ font-size:1.5rem; margin-bottom:1.5rem; }}
  .cards {{ display:flex; gap:1rem; margin-bottom:2rem; flex-wrap:wrap; }}
  .card {{ background:#1e293b; border-radius:8px; padding:1rem 1.5rem; min-width:120px; text-align:center; }}
  .card .num {{ font-size:2rem; font-weight:700; }}
  .card .lbl {{ font-size:0.8rem; color:#94a3b8; margin-top:4px; }}
  .pass {{ color:#22c55e; }} .fail {{ color:#ef4444; }} .margin {{ color:#eab308; }}
  .chart-wrap {{ background:#1e293b; border-radius:8px; padding:1rem; margin-bottom:2rem; max-width:900px; }}
  table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; }}
  th {{ background:#334155; padding:0.6rem 1rem; text-align:left; font-size:0.85rem; color:#94a3b8; }}
  td {{ padding:0.6rem 1rem; font-size:0.9rem; border-top:1px solid #334155; }}
  .filter {{ margin-bottom:1rem; }}
  select {{ background:#1e293b; color:#e2e8f0; border:1px solid #475569; border-radius:4px; padding:4px 8px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="cards">
  <div class="card"><div class="num">{summary['total']}</div><div class="lbl">Total</div></div>
  <div class="card"><div class="num pass">{summary['pass']}</div><div class="lbl">PASS</div></div>
  <div class="card"><div class="num fail">{summary['fail']}</div><div class="lbl">FAIL</div></div>
  <div class="card"><div class="num margin">{summary['margin']}</div><div class="lbl">MARGIN</div></div>
</div>
<div class="chart-wrap"><canvas id="marginChart" height="80"></canvas></div>
<div class="filter">
  Filter: <select id="statusFilter" onchange="filterTable()">
    <option value="ALL">All</option>
    <option value="PASS">PASS</option>
    <option value="FAIL">FAIL</option>
    <option value="MARGIN">MARGIN</option>
  </select>
</div>
<table id="resultsTable">
  <thead><tr><th>Spec</th><th>Value</th><th>Min</th><th>Max</th><th>Status</th><th>Margin</th></tr></thead>
  <tbody id="tbody"></tbody>
</table>
<script>{chartjs}</script>
<script>
const rows = {rows_json};
const chartData = {chart_json};

function renderTable(data) {{
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = data.map(r => `<tr>
    <td>${{r.spec}}</td><td>${{r.value}}</td><td>${{r.min}}</td><td>${{r.max}}</td>
    <td style="color:${{r.color}};font-weight:700">${{r.status}}</td><td>${{r.margin}}</td>
  </tr>`).join('');
}}

function filterTable() {{
  const f = document.getElementById('statusFilter').value;
  renderTable(f === 'ALL' ? rows : rows.filter(r => r.status === f));
}}

renderTable(rows);

new Chart(document.getElementById('marginChart'), {{
  type: 'bar',
  data: {{
    labels: chartData.labels,
    datasets: [{{
      label: 'Margin %',
      data: chartData.values,
      backgroundColor: chartData.colors,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ y: {{ title: {{ display: true, text: 'Margin %', color:'#94a3b8' }}, ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#334155' }} }},
               x: {{ ticks: {{ color:'#94a3b8' }}, grid: {{ color:'#334155' }} }} }},
    responsive: true,
  }}
}});
</script>
</body>
</html>"""


def export_single(
    checks: List[SpecCheck],
    dest: Union[str, Path],
    title: str = "Spec Check Report",
) -> None:
    """Write single-file check result as HTML dashboard."""
    rows = _checks_to_rows(checks)
    summary = {
        "total": len(checks),
        "pass": sum(1 for c in checks if c.status == Status.PASS),
        "fail": sum(1 for c in checks if c.status == Status.FAIL),
        "margin": sum(1 for c in checks if c.status == Status.MARGIN),
    }
    chart_data = {
        "labels": [r["spec"] for r in rows],
        "values": [float(r["margin"].rstrip("%").replace("+", "")) if r["margin"] != "—" else 0 for r in rows],
        "colors": [r["color"] for r in rows],
    }
    html = _render(title, summary, rows, chart_data, _load_chartjs())
    Path(dest).write_text(html, encoding="utf-8")


def export_corners(
    corners: List[Corner],
    dest: Union[str, Path],
    title: str = "Corner Aggregation Report",
) -> None:
    """Write corner aggregation result as HTML dashboard."""
    all_checks = [ch for c in corners for ch in c.checks]
    # Embed corner name info in the title
    corner_names = ", ".join(c.name for c in corners)
    export_single(all_checks, dest, title=f"{title} — {corner_names}")
