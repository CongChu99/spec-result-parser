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


def _render_montecarlo(title: str, summary: dict, rows: list, histograms: list, chartjs: str) -> str:
    rows_json = json.dumps(rows)
    histograms_json = json.dumps(histograms)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:2rem; }}
  h1 {{ font-size:1.5rem; margin-bottom:0.25rem; }}
  .subtitle {{ color:#94a3b8; font-size:0.9rem; margin-bottom:1.5rem; }}
  .cards {{ display:flex; gap:1rem; margin-bottom:2rem; flex-wrap:wrap; }}
  .card {{ background:#1e293b; border-radius:8px; padding:1rem 1.5rem; min-width:120px; text-align:center; }}
  .card .num {{ font-size:2rem; font-weight:700; }}
  .card .lbl {{ font-size:0.8rem; color:#94a3b8; margin-top:4px; }}
  .pass {{ color:#22c55e; }} .fail {{ color:#ef4444; }} .margin {{ color:#eab308; }}
  table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; margin-bottom:2rem; }}
  th {{ background:#334155; padding:0.6rem 1rem; text-align:left; font-size:0.85rem; color:#94a3b8; }}
  td {{ padding:0.6rem 1rem; font-size:0.9rem; border-top:1px solid #334155; }}
  h2 {{ font-size:1.1rem; margin:2rem 0 0.8rem; color:#94a3b8; letter-spacing:0.05em; text-transform:uppercase; font-size:0.75rem; }}
  .hist-grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(340px,1fr)); gap:1rem; margin-bottom:2rem; }}
  .hist-card {{ background:#1e293b; border-radius:8px; padding:1rem; }}
  .hist-title {{ font-size:0.85rem; font-weight:600; margin-bottom:0.5rem; }}
  .spec-limits {{ font-size:0.75rem; color:#94a3b8; margin-bottom:0.5rem; }}
  .filter {{ margin-bottom:1rem; }}
  select {{ background:#1e293b; color:#e2e8f0; border:1px solid #475569; border-radius:4px; padding:4px 8px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; }}
  .badge-PASS {{ background:#14532d; color:#22c55e; }}
  .badge-FAIL {{ background:#7f1d1d; color:#ef4444; }}
  .badge-MARGIN {{ background:#713f12; color:#eab308; }}
  .badge-NA {{ background:#1e293b; color:#6b7280; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="subtitle">Monte Carlo Statistical Analysis — {summary['n_samples']} samples per spec</p>
<div class="cards">
  <div class="card"><div class="num">{summary['total']}</div><div class="lbl">Specs</div></div>
  <div class="card"><div class="num pass">{summary['pass']}</div><div class="lbl">PASS</div></div>
  <div class="card"><div class="num fail">{summary['fail']}</div><div class="lbl">FAIL</div></div>
  <div class="card"><div class="num margin">{summary['margin']}</div><div class="lbl">MARGIN</div></div>
</div>

<h2>Statistics Summary</h2>
<div class="filter">Filter: <select id="statusFilter" onchange="filterTable()">
  <option value="ALL">All</option><option value="PASS">PASS</option>
  <option value="FAIL">FAIL</option><option value="MARGIN">MARGIN</option>
</select></div>
<table id="statsTable">
  <thead><tr>
    <th>Spec</th><th>N</th><th>Mean</th><th>σ</th><th>Min</th><th>Max</th>
    <th>Spec Min</th><th>Spec Max</th><th>Cpk</th><th>Yield %</th><th>Status</th>
  </tr></thead>
  <tbody id="tbody"></tbody>
</table>

<h2>Distribution Histograms</h2>
<div class="hist-grid" id="histGrid"></div>

<script>{chartjs}</script>
<script>
const rows = {rows_json};
const histograms = {histograms_json};
const STATUS_COLOR = {{PASS:"#22c55e",FAIL:"#ef4444",MARGIN:"#eab308","N/A":"#6b7280"}};

function badge(status) {{
  return `<span class="badge badge-${{status}}">${{status}}</span>`;
}}

function renderTable(data) {{
  document.getElementById('tbody').innerHTML = data.map(r => `<tr>
    <td><strong>${{r.spec}}</strong></td><td>${{r.n}}</td>
    <td>${{r.mean}}</td><td>${{r.std}}</td><td>${{r.min}}</td><td>${{r.max}}</td>
    <td>${{r.spec_min}}</td><td>${{r.spec_max}}</td>
    <td>${{r.cpk}}</td><td>${{r.yield_pct}}</td>
    <td>${{badge(r.status)}}</td>
  </tr>`).join('');
}}

function filterTable() {{
  const f = document.getElementById('statusFilter').value;
  renderTable(f === 'ALL' ? rows : rows.filter(r => r.status === f));
}}

renderTable(rows);

// Build histograms
histograms.forEach((h, i) => {{
  const card = document.createElement('div');
  card.className = 'hist-card';
  const limitsText = [
    h.spec_min !== null ? `Min: ${{h.spec_min}}` : null,
    h.spec_max !== null ? `Max: ${{h.spec_max}}` : null,
  ].filter(Boolean).join(' | ') || 'No bounds defined';
  card.innerHTML = `
    <div class="hist-title">${{h.spec}} <span style="color:${{STATUS_COLOR[h.status] || '#fff'}}">(${{h.status}})</span></div>
    <div class="spec-limits">${{limitsText}} | Cpk: ${{h.cpk}} | Yield: ${{h.yield_pct}}</div>
    <canvas id="hist-${{i}}" height="140"></canvas>`;
  document.getElementById('histGrid').appendChild(card);

  // Bin the data
  const vals = h.values;
  const nBins = Math.min(10, vals.length);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const binW = (hi - lo) / nBins || 1;
  const binCounts = new Array(nBins).fill(0);
  const binLabels = [];
  for (let b = 0; b < nBins; b++) {{
    const lo2 = lo + b * binW;
    binLabels.push(lo2.toPrecision(3));
  }}
  vals.forEach(v => {{
    let b = Math.floor((v - lo) / binW);
    if (b >= nBins) b = nBins - 1;
    binCounts[b]++;
  }});

  const color = STATUS_COLOR[h.status] || '#60a5fa';
  new Chart(document.getElementById(`hist-${{i}}`), {{
    type: 'bar',
    data: {{
      labels: binLabels,
      datasets: [{{ label: 'Count', data: binCounts, backgroundColor: color + '99',
                    borderColor: color, borderWidth: 1 }}]
    }},
    options: {{
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ title: {{ display: true, text: 'Count', color:'#94a3b8' }},
              ticks: {{ color:'#94a3b8', precision:0 }}, grid: {{ color:'#334155' }} }},
        x: {{ title: {{ display: true, text: h.unit || 'Value', color:'#94a3b8' }},
              ticks: {{ color:'#94a3b8', maxRotation: 45 }}, grid: {{ color:'#334155' }} }}
      }},
      animation: false,
    }}
  }});
}});
</script>
</body>
</html>"""


def export_montecarlo(
    stats,
    dest: Union[str, Path],
    title: str = "Monte Carlo Analysis Report",
) -> None:
    """Write Monte Carlo statistical results as a dark-theme HTML dashboard with histograms."""
    from spec_result_parser.models import Status

    rows = []
    histograms = []
    n_samples = max((s.n for s in stats), default=0)

    for s in stats:
        unit = s.unit or ""
        rows.append({
            "spec": s.name,
            "n": s.n,
            "mean": f"{s.mean:.4g} {unit}".strip(),
            "std": f"{s.std:.4g} {unit}".strip(),
            "min": f"{s.min_val:.4g} {unit}".strip(),
            "max": f"{s.max_val:.4g} {unit}".strip(),
            "spec_min": "—",
            "spec_max": "—",
            "cpk": f"{s.cpk:.3f}" if s.cpk is not None else "—",
            "yield_pct": f"{s.yield_pct:.2f}%" if s.yield_pct is not None else "—",
            "status": s.status.value if s.status != Status.NA else "N/A",
            "color": _STATUS_COLOR.get(s.status.value, "#ffffff"),
        })
        histograms.append({
            "spec": s.name,
            "values": s.values,
            "unit": unit,
            "spec_min": None,
            "spec_max": None,
            "status": s.status.value if s.status != Status.NA else "N/A",
            "cpk": f"{s.cpk:.3f}" if s.cpk is not None else "—",
            "yield_pct": f"{s.yield_pct:.2f}%" if s.yield_pct is not None else "—",
        })

    summary = {
        "total": len(stats),
        "pass": sum(1 for s in stats if s.status == Status.PASS),
        "fail": sum(1 for s in stats if s.status == Status.FAIL),
        "margin": sum(1 for s in stats if s.status == Status.MARGIN),
        "n_samples": n_samples,
    }

    html = _render_montecarlo(title, summary, rows, histograms, _load_chartjs())
    Path(dest).write_text(html, encoding="utf-8")
