# T-120 [S] Budget `committed_in_window` + `MonthTotals.committed_minor` + template surfaces

> Depends on: T-117, T-118, T-119, [ADR-0039](../../../adr/0039-budget-daily-spend-includes-recurring.md). Blocks: nothing (last math-side change in the phase).

## Scope

Service arithmetic + template line additions. No schema change.

### `services/budget.py`

- `MonthTotals` grows one field:
  ```python
  @dataclass(frozen=True, slots=True)
  class MonthTotals:
      budgeted_minor: int
      spent_minor: int
      committed_minor: int   # NEW
      remaining_minor: int   # = budgeted − spent − committed
  ```
- New pure helper:
  ```python
  def committed_in_window(
      conn: sqlite3.Connection,
      *,
      start: dt.date,
      end: dt.date,
  ) -> int:
      """Sum of unpromoted planned-expense + recurring-expense amounts
      with effective date in [start, end). Overrides applied; skipped
      excluded. Transit + adjustment directions excluded.
      """
  ```
  - Reuses `services.recurring.expand` to enumerate due dates per rule within `[start, end)` for the handful of upcoming cycles — forecast's existing caller.
  - Reuses `planned_repo.list_filtered(promoted=False, date_from=start, date_to=end − 1 day)` for the planned branch.
  - Category direction derived via `categories_repo.list_all` lookup table.
- `month_summary` wires:
  - `committed = committed_in_window(conn, start=today, end=next_income_date)`.
  - `remaining = budgeted − spent − committed`.
  - Zero-budget months: `committed_minor = 0` so the dim sub-line still renders a flat zero (clearer than hiding).
  - `left_daily_spend_minor = banker_round(remaining / days_until_next_income)` — rounding unchanged.

### Templates

- `templates/budget/_hero.html` (new, or inlined into `budget/index.html`): render under the "Left to spend per day" headline:
  ```html
  <p class="hero__sub tabular-nums">
    {{ summary.totals.committed_minor | money(base_currency) }} committed
    <span class="hero__sub-tag">(recurring + planned)</span>
  </p>
  ```
  - When `summary.totals.committed_minor == 0`, render the line in the muted token so the user sees "0 PLN committed" at a glance.
- `templates/home/_month_panel.html` picks up the same block (shared includes).

### Tests

- `tests/unit/services/test_budget.py`:
  - `committed_in_window` — planned-only; recurring-only (monthly cadence inside window); recurring with `end_date` cut mid-window; override on `next_due` adjusts amount; skipped override excluded.
  - `month_summary` — fixture with 1 recurring expense due inside window reduces `remaining` by its amount; `left_daily_spend_minor` adjusts accordingly; promoting the recurring (via `services.recurring.promote_recurring`) moves the amount from `committed_minor` into `spent_minor` with zero net effect on `remaining_minor` for the same `today`.
- `tests/integration/web/test_budget.py` + `tests/integration/web/test_home.py` — hero renders the "X committed" sub-line; HTMX re-render after `budget-stale` emits still carries the sub-line.

### `frontend-visual-audit` sweep

- `/`, `/budget` at 1440 / 1024 / 375. Refresh baselines for the two affected routes.

## Acceptance

- Existing fixtures that don't have recurring rules yield `committed_minor = 0` and preserve the old `remaining_minor` value — no regression on Phase 9 budget tests.
- `MonthSummary` + `MonthTotals` dataclasses add fields only; no existing field renames or deletes.
- Coverage ≥ 90%.
- `just ci` + visual sweep green.

## Non-goals

- Changing how recurring data is stored (T-117).
- Changing promotion wiring (T-118).
- Overview row rendering of individual Upcoming items (T-121).
