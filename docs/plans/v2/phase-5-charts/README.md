# Phase 5 — Charts (Plotly → server-rendered SVG)

> Replace Plotly with a tiny `charts.py` module that returns SVG geometry; render charts via Jinja; each chart carries a `<details>` data-table fallback.
>
> Bundle target: `plotly.js` deletion drops ≥ 1.5 MB from the critical path.

Entry: Phase 2 exit criteria met; Phase 4 T-R43 analytics bundle endpoint reachable in dev.

Exit: `grep -r plotly src/` returns zero hits outside historical ADR text; forecast + analytics charts render on-brand; data-table fallbacks present.

Tasks: T-R47..T-R50 + T-R68.

- T-R47 `src/budget_planner/web/charts.py`
- T-R48 Forecast chart template (line + area + annotations)
- T-R49 Analytics chart templates (grouped bars + horizontal bars)
- T-R50 Plotly removal + bundle-delta verification
- T-R68 `sparkline()` helper + Accounts trend column

ADR references: 0054, 0002 (superseded by 0054 for charts), 0015, 0042, 0043.
