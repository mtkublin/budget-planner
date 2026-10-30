# T-R50 — Plotly removal

- **Phase**: 5 — Charts
- **Sequential**: last task of Phase 5.
- **Depends on**: T-R47, T-R48, T-R49.
- **References**: ADR-0054.

## Context

Final removal gate. After T-R48 and T-R49 have Forecast and Analytics rendering via SVG, Plotly's JS and the server-side `to_plotly_figure` helpers are dead code. This task deletes them and verifies the bundle-size target.

## Deliverables

- Delete `src/budget_planner/web/static/vendor/plotly*.js` (if committed).
- Delete `src/budget_planner/web/plot.py` or any module whose only purpose was Plotly JSON conversion.
- Remove `plotly` from `pyproject.toml` dependencies (if present as a runtime dep).
- Remove any `script src="/static/vendor/plotly..."` tags from `base.html` / forecast / analytics templates.
- Audit: `grep -r "plotly\|Plotly" src/ pyproject.toml` returns zero matches outside historical ADR text under `docs/adr/`.
- Measure bundle delta: compare the gzipped size of the critical-path JS before/after; record in the task PR body.

## Acceptance criteria

- `grep -r "plotly\|Plotly" src/budget_planner/` is empty.
- `uv run pytest` green; `just ci` green.
- Bundle delta ≥ 1.5 MB uncompressed (handoff target).
- Forecast + Analytics continue to render correctly against the Phase 3 visual-regression baselines (zero drift).

## Validation hook

```sh
grep -rE "plotly|Plotly" src/budget_planner/ && exit 1 || echo "clean"
du -sb src/budget_planner/web/static/vendor/ | awk '{print $1}'
just ci
```

## Risks & gotchas

- If any residual tests still mock `plotly`, they break after import removal. Delete those tests or rewrite against the SVG renderer.
- Pre-commit `pip-audit` entry for `plotly` is also stale; drop it.
- `pyproject.toml` cleanup regenerates `uv.lock` — commit the lock update in the same PR.

## Handoff notes

- Follow-up: a later task may add `sparkline()` to `charts.py` for the Accounts trend column; this gate stays unchanged for that work.
- The ADR history (`docs/adr/0002-web-stack-fastapi-htmx-jinja.md` names Plotly) stays untouched — ADRs are append-only; ADR-0054 supersedes it.
