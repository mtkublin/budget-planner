# T-R25 — Today

- **Phase**: 3 — Screens
- **Sequential**: first screen rebuild; sets the pattern for the rest.
- **Depends on**: Phase 2 primitives, T-R40 (`/today/afford`).
- **References**: ADR-0051 §3, ADR-0056 §3, handoff `docs/application_redesign_handoff/docs/03-screen-specs.md` §Today.

## Context

Today replaces v1's Overview. Three regions: hero (left-per-day), can-I-afford input, net worth card, and Upcoming panel. The hero reuses `MonthSummary.left_daily_spend_minor` and `days_until_next_income` from existing services; the only new backend piece is `/today/afford` live preview.

## Deliverables

- `src/budget_planner/web/routers/today.py` — fully replaces the Phase 1 stub.
- `templates/today/index.html` extending `base.html`:
  - `_hero.html` with left-per-day via `amount` macro, pace tag via `pace_tag`, segmented bar via `progress_bar`, period one-liner via `period_header`.
  - `_can_i_afford.html` with input + HTMX trigger `keyup changed delay:200ms` → `GET /today/afford?amount=`; renders delta line via `amount`.
  - `_net_worth.html` with total + assets + liabilities + six largest balances + links to Accounts and Plan · Forecast.
  - `_upcoming.html` with segmented 7/30/All + grouped rows via `table_row`; promote-in-place HTMX expansion (ADR-0056 §1).
- Service wiring:
  - Hero + period reuse `services.budget.month_summary(conn, today)` directly.
  - Upcoming reuses `services.upcoming.list_upcoming(conn, window)` (ADR-0038).
- Promote-in-place: `GET /recurring/{id}/promote-form` + `GET /planned/{id}/promote-form` return the expanded row fragment (service helpers added in Phase 4 if not already present).
- Integration tests under `tests/integration/web/test_today.py` cover hero rendering, afford endpoint delta, Upcoming overdue muting, promote-in-place expansion, keyboard `g o` landing.

## Acceptance criteria

- `/today` renders without template errors; `curl -o /dev/null -w "%{http_code}\n" http://localhost:8000/today` prints `200`.
- Visual-regression baselines at D/T/M match the handoff mockups `desktop-1d-today.png` and `mobile-1o-today.png` within tolerance.
- `frontend-visual-audit` on `/today` at 1440 / 1024 / 375 returns zero `horizontalScroll`, `overflowingElements`, `duplicateIds`, `consoleErrors`, `requestFailures`.
- Can-I-afford input debounces to one request per 200 ms; server minor-unit arithmetic matches `month_summary` (same tie-breaking rules).
- Upcoming promote-in-place: focus a row, press `↵`, confirm with `↵`, hero updates via `HX-Trigger: budget-stale`.
- `g o` from any page lands on `/today`.

## Validation hook

```sh
pytest tests/integration/web/test_today.py && \
  just test-visual --filter today && \
  invoke frontend-visual-audit at 1440 1024 375 against /today
```

## Risks & gotchas

- The segmented progress bar (spent | committed | left) must use diagonal hatch for the committed segment (ADR-0053 §Progress bar). Confirm the hatch pattern renders in Firefox + Safari.
- Overdue rows use `.row--overdue` plus the `overdue_chip` macro; both signals must be present (no colour-only state per ADR-0050 §6).
- Can-I-afford: when the input is empty or non-numeric, the endpoint returns the baseline per-day figure without delta — do not throw.
- The pace tag colour maps to tokens (`--income` on-track, `--adjust` tight, `--expense` overdue); do not hard-code hex.

## Handoff notes

- Subsequent screen tasks (T-R26..T-R39) copy this task's structure: router stub → template extending base → partials per region → integration tests → visual-regression baselines → `frontend-visual-audit`.
- Promote-in-place pattern is reused by Ledger · Planned (T-R27) and Ledger · Recurring (T-R28); the row fragment route lives in those routers.
