# T-100 — Left Daily Spend in `services/budget.py`

> Phase 9 — Left Daily Spend. Status: pending.

## Purpose

Extend `MonthSummary` with the new metric so templates and routers consume one DTO instead of orchestrating three services. All math stays pure; `today` becomes an injected parameter so tests remain deterministic (no monkeypatching `date.today`).

## Inputs / prerequisites

- Upstream tasks: T-024 (budget service baseline), T-098 (anchor resolver), T-099 (next-planned-income lookup).
- Binding standards:
  - [`ADR-0014`](../../../adr/0014-budget-flat-no-rollover-three-tier.md) — flat budgets, no rollover (unchanged by this task).
  - [`ADR-0025`](../../../adr/0025-user-preferences-and-income-anchor.md) — anchor fallback rules.
  - [`ADR-0007`](../../../adr/0007-timezone-handling.md) — `today` is computed in `Europe/Warsaw` at the router boundary.
- Adjacent precedent: `services/budget.py:128` — current `month_summary` signature and `MonthTotals` wiring.

## Deliverables

Modified file: `src/budget_planner/services/budget.py`.

Extended DTO:

```python
@dataclass(frozen=True, slots=True)
class MonthSummary:
    year: int
    month: int
    lines: tuple[CategoryBudgetLine, ...]
    totals: MonthTotals
    left_daily_spend_minor: int | None   # new — None when totals.budgeted_minor == 0
    next_income_date: date | None        # new — the resolved target date (anchor hit OR fallback)
    days_until_next_income: int          # new — floored at 1
    anchor_category_name: str | None     # new — the anchor category name, or None if fallback used
```

Extended function:

```python
def month_summary(
    conn: Connection,
    year: int,
    month: int,
    *,
    today: date,
) -> MonthSummary: ...
```

- `today` is required and keyword-only; no default (ADR-0007 pushes "now" to the router boundary).
- Caller: `web/routers/budget.py` computes `today = datetime.now(zoneinfo.ZoneInfo(settings.display_timezone)).date()` and passes it through.

Algorithm (added at the tail of the existing function, after `totals = MonthTotals(...)`):

1. If `totals.budgeted_minor == 0`:
   - `left_daily_spend_minor = None`
   - `anchor_category_name = None`
   - `next_income_date = <last day of (year, month)>`
   - `days_until_next_income = max((next_income_date - today).days, 1)`
2. Else:
   - `anchor = preferences_svc.resolve_income_anchor_category(conn)`
   - If `anchor` is `None`:
     - `anchor_category_name = None`; `next_income_date = <last day of (year, month)>`
   - Else:
     - `hit = planned_svc.next_planned_for_category(conn, anchor.id, after=today)`
     - If `hit is None`: `anchor_category_name = None`; `next_income_date = <last day of (year, month)>` (fallback — anchor exists but has no future income).
     - Else: `anchor_category_name = anchor.name`; `next_income_date = hit.operation_date`.
   - `days = max((next_income_date - today).days, 1)`
   - `left_daily_spend_minor = int((Decimal(totals.remaining_minor) / Decimal(days)).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))`

New tests under `tests/unit/services/test_budget_left_daily_spend.py`:

- `test_anchor_set_income_tomorrow` — remaining = 300, today + 1d, anchor hit → `left = 300`.
- `test_anchor_set_income_in_ten_days` — remaining = 1000, today + 10d → `left = 100`.
- `test_anchor_set_no_upcoming_falls_back_to_end_of_month` — anchor set, no planned row → `anchor_category_name is None`; denominator = days-to-last-of-month.
- `test_anchor_unset_falls_back` — no preference row at all → fallback with `anchor_category_name is None`.
- `test_zero_budget_returns_none` — all budgeted = 0 → `left_daily_spend_minor is None`.
- `test_today_is_last_day_of_month_denominator_is_one` — today = last day → `days_until_next_income = 1`, `left == remaining`.
- `test_stale_anchor_falls_back` — anchor set then category soft-deleted → `resolve` returns `None` → fallback; preference row untouched.
- `test_rounding_half_even` — remaining = 1001, days = 2 → `left = 500` (501 would be round-half-up).
- `test_virtual_recurring_hit` — recurring INCOME rule generates a virtual occurrence 5 days out, no persisted row → caption shows the anchor name, denominator = 5.

## Step-by-step

1. **DTO fields.** Add the four new fields to `MonthSummary` in alphabetical adjacency to the existing fields, matching the slots-aware frozen dataclass pattern.
2. **Imports.** Add `from budget_planner.services import planned as planned_svc, preferences as preferences_svc`. Watch for a circular import — `services.planned` already imports from `repositories`; keep this at the top.
3. **Signature change.** `today` is required and keyword-only. Every existing caller currently defaults to `date.today()` at the service — this task **moves** that default to each caller. Audit the router (T-101 does the real work) and tests (`tests/unit/services/test_budget.py` and `tests/integration/web/test_budget.py`); update each with an injected date.
4. **Last-day-of-month helper.** Reuse `_month_range(year, month)` which already returns `(start, end)`.
5. **Floor at 1 and rounding.** Mirror the `_mean_minor` pattern already in the module (`Decimal` + `ROUND_HALF_EVEN` + `int(...)`).
6. **Public export.** `MonthSummary` already in `__all__`; nothing to add there, but mention the new fields in the module docstring.

## Validation / acceptance

- `pytest tests/unit/services/test_budget*.py -q` — all tests pass (existing + new).
- `pytest --cov=src/budget_planner/services/budget --cov-fail-under=95` — ≥ 95% branch coverage retained.
- `grep -nE "date\\.today\\(\\)" src/budget_planner/services/budget.py` returns no match (defensive — the service does not read the clock).
- `just test` — full suite green.
- `just lint` + `just typecheck` green.

## Risks & gotchas

- **Signature change ripple.** `today` is now required. Every existing caller breaks until updated. Pair this task's PR with T-101 or ship a shim default (`today: date | None = None`) only if you must — the preferred shape is "no shim, update every caller".
- **Timezone correctness.** The router must compute `today` in `Europe/Warsaw` (or `settings.display_timezone`). Passing UTC `date.today()` from a service test is fine for determinism; the production call site is the one that must get the TZ right.
- **Fallback caption.** `anchor_category_name is None` is the signal to the template to render `(end of month)`. Do not pass a placeholder string from the service — keeping it `None` makes the template contract explicit.
- **Rounding bias.** Banker's rounding (`ROUND_HALF_EVEN`) matches the rest of the service (`_mean_minor`). Do not switch to `ROUND_HALF_UP` for this one metric — consistency wins.
- **Zero remaining with non-zero budget.** `remaining_minor` can be negative (overspent). Division then yields a negative "left per day". That is the correct signal — show it unmodified. Templates may want to tint it red; the service does not clamp.

## Handoff notes

- Hand-off to T-101: templates consume `summary.left_daily_spend_minor` / `summary.anchor_category_name` / `summary.next_income_date` / `summary.days_until_next_income` directly. No new filters needed; `money` and `date_fmt` already exist (T-030).
- Commit shape: `feat(T-100): MonthSummary.left_daily_spend_minor (ADR-0025, F4.6)`.
