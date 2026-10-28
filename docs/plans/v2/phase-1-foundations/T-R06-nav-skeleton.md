# T-R06 — Nav skeleton + legacy 302 shims

- **Phase**: 1 — Foundations
- **Sequential**: yes.
- **Depends on**: T-R04.
- **References**: ADR-0051 §1, §2.

## Context

The redesign introduces canonical routes `/today`, `/plan?tab=…`, `/accounts`, `/settings?tab=…` and keeps every v1 URL alive via 302 shims for one release (Phase 7 removes the shims).

## Deliverables

- New routers:
  - `src/budget_planner/web/routers/today.py` — `GET /today` returns a stub page in Phase 1 (filled by T-R25); registers the canonical URL and the `/` legacy 302.
  - `src/budget_planner/web/routers/plan.py` — `GET /plan?tab=budget|year|forecast|analytics` returns a stub shell in Phase 1 (filled by T-R29); registers canonical URL and tab routing.
- Updated routers:
  - `routers/home.py` — `/` returns `RedirectResponse(url="/today", status_code=302)`.
  - `routers/budget.py` — `/budget` and `/budget/yearly` 302 to `/plan?tab=budget` and `/plan?tab=year`.
  - `routers/forecast.py` — `/forecast` + `/forecast/view` 302 to `/plan?tab=forecast`.
  - `routers/analytics.py` — `/analytics` 302 to `/plan?tab=analytics`.
  - `routers/categories.py` — `/categories` 302 to `/settings?tab=categories`.
  - `routers/transactions.py` — `/transactions` 302 to `/ledger?view=actual`.
  - `routers/planned.py` — `/planned` 302 to `/ledger?view=planned`.
  - `routers/recurring.py` — `/recurring` 302 to `/ledger?view=recurring`.
- Settings router: `/settings` returns the full page shell (not the v1 drawer fragment) — Phase 3 fills tab content; stub page suffices in Phase 1.
- `static/js/shortcuts.js` wires `g o/l/p/a/s` to the new URLs.
- Integration tests cover every legacy → canonical 302 Location.

## Acceptance criteria

- `curl -i -o /dev/null -w "%{http_code} %{redirect_url}\n" http://localhost:8000/budget` prints `302 /plan?tab=budget`.
- `g o` from the Today page is idempotent; `g p` from any page lands on `/plan?tab=budget` (default tab).
- The settings slide-over fragment response (`/settings?tab=categories` returning drawer HTML) is **retired** — the same URL now returns the full `/settings` page. Any integration test asserting the drawer response must be updated to assert the page response (file list captured in the task PR body).
- No Phase 1 route change breaks a v1 bookmark; every URL in the v1 README resolves (via 302 if needed).

## Validation hook

```sh
pytest tests/integration/web -k redirect && \
  curl -sI http://localhost:8000/budget | grep -i "location: /plan"
```

## Risks & gotchas

- Fragment responses that *used* `/settings` for drawer swap must change their HTMX call to the new tab-content route (introduced in Phase 3). In Phase 1 the drawer stops opening — the gear icon routes via `g s` to `/settings` instead. Document this transitional loss of fragment behaviour in the task PR body.
- `HX-Trigger` events (`budget-stale`, etc.) are **not** affected by this task — the services + repositories are untouched. Only URL shapes change.
- Keep the 302 shims small (one-liner `RedirectResponse`); T-R57 deletes them en bloc in Phase 7.

## Handoff notes

- Phase 3's first screen (T-R25 Today) lands on the stub registered here. The stub returns an empty `<main>` so visual-regression captures a known-good "shell only" baseline.
- Phase 7 removes every 302 added here. The grep audit for `RedirectResponse` in `routers/` is the acceptance signal for T-R57.
