# T-R57 — Retire v1 → v2 302 redirects

- **Phase**: 7 — Cleanup
- **Sequential**: first Phase 7 task.
- **Depends on**: v2 shipped ≥ 1 release with no bookmarked-URL complaints.
- **References**: ADR-0051 §2 (one-release 302 shim window).

## Context

Phase 1 (T-R06) added 302 shims from every v1 URL to its v2 equivalent. The ADR commits to one release of overlap. This task deletes the shims and the dead router modules once that window closes.

## Deliverables

- Delete 302 shim handlers in:
  - `routers/home.py` — `/` is now the canonical Today redirect, not a 302 to `/today` (consolidate the route under `routers/today.py`).
  - `routers/budget.py` — delete the module if no non-shim handlers remain; otherwise remove the `RedirectResponse` branches.
  - `routers/forecast.py` — same shape.
  - `routers/analytics.py` — same shape.
  - `routers/categories.py` — delete the top-level page handler; keep only API-shaped endpoints migrated to `/settings`.
  - `routers/transactions.py` — delete the `/transactions` page handler; keep write endpoints.
  - `routers/planned.py` — same.
  - `routers/recurring.py` — same.
- `src/budget_planner/web/app.py` — stop including deleted routers.
- Templates:
  - Delete `templates/budget/`, `templates/forecast/`, `templates/analytics/`, `templates/categories/` and any descendants that are no longer referenced.
  - `grep -r "/budget\|/forecast/\|/analytics\|/categories\|/transactions$\|/planned$\|/recurring$" src/budget_planner/web/templates/` returns zero live hits (only within the historical `docs/` folder).
- Integration tests:
  - Delete `test_budget_page.py`, `test_forecast_page.py`, `test_analytics_page.py` (page-level tests). Keep service-level tests.
  - Replace legacy-302 tests with "legacy-URL returns 404" assertions (so a resurrected bookmark reaches a clear error page).

## Acceptance criteria

- `curl -o /dev/null -w "%{http_code}" http://localhost:8000/budget` returns `404` (not `302`).
- `grep -r "RedirectResponse.*plan\|budget\|forecast\|categories\|transactions\|planned\|recurring" src/budget_planner/web/routers/` returns zero hits.
- `just ci` green.
- Dead-link audit on the deployed app (manual Playwright crawl) finds no 404s from internal links — every v1 URL in templates has been rewritten.
- `docs/CHANGELOG.md` dated entry documents the retirement.

## Validation hook

```sh
pytest tests/integration/web/test_legacy_404.py && \
  grep -r "RedirectResponse.*/\(plan\|budget\|forecast\|categories\|transactions\|planned\|recurring\)" src/ || echo "clean"
```

## Risks & gotchas

- A deleted template may still be referenced from a Jinja `extends` or `include`. `pytest -k template` should catch; if not, `just ci` eventually fails at render time.
- Bookmarks on the user's device are the primary concern. The post-404 page gets a dated "Rising Dough has moved pages" note linking to Today — minimises confusion.
- Do not delete `test_recurring.py` / `test_planned.py` service-level tests; those endpoints still exist, only the page shells go.

## Handoff notes

- T-R58 (FAB deletion) and T-R59 (drawer-root removal) depend on this task completing cleanly.
- T-R60 dead-CSS prune runs after; stylelint has fewer surfaces to scan once legacy templates are gone.
