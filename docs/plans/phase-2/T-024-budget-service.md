# T-024 — Budget Service

> Phase 2 — Services. Status: pending.

## Purpose

Resolve a monthly budget for any `(category, year, month)` via the three-tier null-coalesce (one-off → recurring → default) from ADR-0014, and produce a current-month summary (per-category budgeted / spent / remaining plus analytical values: average monthly spend overall, average this year, delta vs previous month). Flat categories, no rollover.

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-013 Repositories](../phase-1/T-013-repository-layer.md) — `repositories/budgets.py`, `repositories/categories.py`, `repositories/transactions.py`.
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `Category`, `BudgetDefault`, `BudgetRecurringOverride`, `BudgetOneOffOverride`.
- ADRs:
  - [ADR-0014 Budget flat, no rollover, three-tier](../../adr/0014-budget-flat-no-rollover-three-tier.md). *(tasks.md incorrectly cites ADR-0017 for T-024; the correct ADR is 0014. ADR-0017 is the pre-commit stack.)*
  - [ADR-0008 Transaction amount sign & direction](../../adr/0008-transaction-amount-sign-and-direction.md) — "spent" is a sum of positive expense amounts.
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
- Repository functions consumed:
  - `repositories.budgets.find_default(conn, category_id) -> BudgetDefault | None`
  - `repositories.budgets.find_recurring_override(conn, category_id, month: int) -> BudgetRecurringOverride | None`
  - `repositories.budgets.find_one_off(conn, category_id, year, month) -> BudgetOneOffOverride | None`
  - `repositories.budgets.list_defaults(conn) -> list[BudgetDefault]`
  - `repositories.budgets.list_recurring_for_month(conn, month) -> list[BudgetRecurringOverride]`
  - `repositories.budgets.list_one_offs_for_month(conn, year, month) -> list[BudgetOneOffOverride]`
  - `repositories.categories.list_active(conn, direction: Direction | None) -> list[Category]`
  - `repositories.transactions.sum_by_category_in_month(conn, year, month, direction=Direction.expense) -> dict[int, int]`
  - `repositories.transactions.sum_by_category_in_year(conn, year, direction=Direction.expense) -> dict[int, int]`
  - `repositories.transactions.sum_by_category_overall(conn, direction=Direction.expense) -> dict[int, int]` + `repositories.transactions.active_month_count(conn, direction=Direction.expense) -> dict[int, int]`

## Deliverables

- Module path: `src/budget_planner/services/budget.py`
- Test module path: `tests/unit/services/test_budget.py`
- Public function signatures:

```python
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CategoryBudgetLine:
    category_id: int
    category_name: str
    budgeted_minor: int | None       # None when neither default nor overrides exist
    spent_minor: int                  # positive magnitude of expenses this month
    remaining_minor: int | None       # budgeted - spent; None if budgeted is None
    avg_monthly_overall_minor: int    # average expense magnitude per month across all history
    avg_this_year_minor: int          # average per completed month in current year to date
    delta_vs_prev_month_minor: int    # spent_this_month - spent_prev_month


@dataclass(frozen=True, slots=True)
class MonthSummary:
    year: int
    month: int
    lines: tuple[CategoryBudgetLine, ...]
    totals: "MonthTotals"


@dataclass(frozen=True, slots=True)
class MonthTotals:
    budgeted_minor: int               # sum of non-None budgeted values
    spent_minor: int
    remaining_minor: int


def resolve_budget(
    conn: sqlite3.Connection,
    category_id: int,
    year: int,
    month: int,
) -> int | None: ...


def month_summary(
    conn: sqlite3.Connection,
    year: int,
    month: int,
) -> MonthSummary: ...
```

## Algorithm / step-by-step

### `resolve_budget`

Null-coalesce resolution order (ADR-0014):

| Tier | Lookup | Scope |
|------|--------|-------|
| 1 | `budget_one_off_overrides(category_id, year, month)` | Applied **once**. |
| 2 | `budget_recurring_overrides(category_id, month)` | Applied **every year** for that month. |
| 3 | `budget_defaults(category_id)` | Applied **all months**. |

```python
def resolve_budget(conn, category_id, year, month) -> int | None:
    one_off = repositories.budgets.find_one_off(conn, category_id, year, month)
    if one_off is not None:
        return one_off.amount
    rec = repositories.budgets.find_recurring_override(conn, category_id, month)
    if rec is not None:
        return rec.amount
    default = repositories.budgets.find_default(conn, category_id)
    if default is not None:
        return default.amount
    return None
```

**No zero-vs-null confusion.** `0` is a valid intentional "zero budget this month"; `None` means "unbudgeted". Downstream UI distinguishes them.

### `month_summary`

Batch-friendly — one pass per data source, join in memory. Avoid N+1 by using the `list_*_for_month` and `sum_by_*` repositories.

```
1. Load:
     cats     = list_active(conn, direction=Direction.expense)
     defaults = list_defaults(conn)                        # dict[cat_id, amount]
     recs     = list_recurring_for_month(conn, month)      # dict[cat_id, amount]
     oneoffs  = list_one_offs_for_month(conn, year, month) # dict[cat_id, amount]

     spent_this  = sum_by_category_in_month(conn, year, month)
     spent_prev  = sum_by_category_in_month(conn, *prev_year_month(year, month))
     year_sums   = sum_by_category_in_year(conn, year)
     year_mos    = elapsed_months_in_year(year, month)     # 1..12
     overall_sum = sum_by_category_overall(conn)
     overall_mos = active_month_count(conn)                # dict[cat_id, int]

2. For each category c in cats:
     budgeted = oneoffs.get(c.id)
                or recs.get(c.id)
                or defaults.get(c.id)
     spent    = spent_this.get(c.id, 0)
     remaining = (budgeted - spent) if budgeted is not None else None

     avg_overall  = overall_sum.get(c.id, 0) // max(overall_mos.get(c.id, 1), 1)
     avg_this_yr  = year_sums.get(c.id, 0) // max(year_mos, 1)
     delta_prev   = spent - spent_prev.get(c.id, 0)

     emit CategoryBudgetLine(...)

3. Sort lines by (budgeted is None, category_name)  # budgeted first, then alpha.

4. Totals: sum budgeted (skipping None), sum spent, sum remaining (skip None).

5. Return MonthSummary(year, month, tuple(lines), totals).
```

Helpers (pure, in-module):

- `prev_year_month(year, month) -> tuple[int, int]`: handles January → previous December.
- `elapsed_months_in_year(year, month) -> int`: `month` (1-based). For future months in the current year, document that `avg_this_year` divides by elapsed months to date; for past years, divides by 12.

### Analytical values

- **`avg_monthly_overall`** uses the per-category "active month count" from the repository — the number of distinct `YYYY-MM` buckets with at least one expense for that category. Avoids divide-by-zero and penalises categories only started recently fairly. Falls back to `1` if the category has no history.
- **`avg_this_year`** divides year-to-date sum by elapsed months. December vs mid-year is handled naturally.
- **`delta_vs_prev_month`** is simply `spent_this - spent_prev`. Sign carries intent: positive means "spent more than last month".

All averages are integer minor units via `Decimal` → `int` conversion with `ROUND_HALF_EVEN` to avoid Python's floor-division bias for negative values.

## Interfaces / contracts

```python
def resolve_budget(conn, category_id, year, month) -> int | None:
    """
    Null-coalesce order: one-off → recurring → default. Returns None iff
    none of the three tables has a row for this (category, year, month).
    Zero (0) is a valid budget value and is returned as 0, not None.
    """


def month_summary(conn, year, month) -> MonthSummary:
    """
    One row per active expense category. Returns totals summed over rows
    with a non-None budgeted value. Pure w.r.t. the given DB snapshot.
    """
```

Invariants:

- `resolve_budget(..., y, m) == None` iff the three-tier null-coalesce is empty.
- `month_summary(...).lines` contains exactly `len(list_active_expense_categories)` rows.
- `line.remaining_minor is None` iff `line.budgeted_minor is None`.

## Test strategy

Fixtures:

```
categories (direction=expense):
  10 Groceries
  11 Rent
  12 Utilities
  13 Gym      <- no budget rows set anywhere

budget_defaults:
  10 -> 120_000  (1 200,00 PLN)
  11 -> 300_000
  12 ->  40_000

budget_recurring_overrides:
  (11, month=1) -> 310_000     # Rent goes up every January

budget_one_off_overrides:
  (12, 2026, 2) -> 60_000      # February 2026 heating spike

transactions (expense only, PLN, Checking account):
  2026-01-05  Groceries   30_000
  2026-01-20  Groceries   40_000
  2026-01-25  Rent       310_000
  2026-02-02  Utilities   55_000
  2026-02-10  Groceries   45_000
  2025-11-15  Groceries   35_000     # last-year baseline for averages
```

Cases:

### `resolve_budget`

1. **Default only**: `resolve_budget(10, 2026, 3) == 120_000`.
2. **Recurring override picks over default**: `resolve_budget(11, 2026, 1) == 310_000`.
3. **Recurring override does not apply to other months**: `resolve_budget(11, 2026, 7) == 300_000` (default).
4. **One-off beats recurring and default**: `resolve_budget(12, 2026, 2) == 60_000`.
5. **One-off does not persist across years**: `resolve_budget(12, 2027, 2) == 40_000` (default, no recurring for Feb).
6. **No rows anywhere**: `resolve_budget(13, 2026, 3) == None`.
7. **Zero is valid**: insert `budget_defaults(10, 0)`, expect `0` returned, not `None`.

### `month_summary`

8. **January 2026**: Rent uses the recurring override (310_000); spent==310_000; remaining=0. Groceries budgeted==120_000; spent==70_000; remaining==50_000. Utilities budgeted==40_000; spent==0. Gym budgeted is `None`; spent==0; remaining `None`.
9. **February 2026**: Utilities budgeted==60_000 (one-off); spent==55_000; remaining==5_000. Delta vs January for Groceries = 45_000 − 70_000 = −25_000.
10. **Totals exclude unbudgeted lines**: Gym does not contribute to any total.
11. **Previous-month roll-over Jan→Dec**: `month_summary(2026, 1)` sets Groceries `delta_vs_prev_month = 70_000 − 0` (no Dec 2025 Groceries in fixture → spent_prev = 0).
12. **`avg_monthly_overall` uses active-month count**: Groceries history = Nov 2025 (1 txn), Jan 2026 (2 txns), Feb 2026 (1 txn) → 3 distinct months → avg = (35_000+70_000+45_000)/3 = 50_000.
13. **`avg_this_year`**: Groceries 2026 YTD through February → (70_000 + 45_000) / 2 = 57_500.
14. **Deleted txn excluded**: soft-delete a January Groceries row and verify `spent_minor` and averages shift.
15. **Transit excluded from spent**: insert a transit row referencing a Groceries-direction category? Not valid — but insert an income row and confirm it does not affect expense totals (direction filter in repo).
16. **Adjustment excluded**: insert a reconciliation adjustment on Checking; `spent_minor` unaffected.
17. **Sort order**: lines with budgeted set appear before `None` budget lines; alphabetical within group.
18. **Rounding**: force a scenario where averaging produces `.5` minor unit and verify `ROUND_HALF_EVEN` behaviour (choose amounts so banker's rounding is unambiguous — e.g. 50_000 / 3 is a repeating decimal; assert the deterministic int).

Mocking boundaries: none. Live DB + schema.

## Risks & gotchas

- **Zero vs null**: `0` is a valid budget, not "unbudgeted". The chained `or` idiom in Python collapses `0`-ish values; use explicit `is not None` checks in `resolve_budget`.
- **One-off scope**: do not apply a one-off to the same month of a different year. The year is part of the key by design.
- **Previous-month computation across year boundaries**: Jan → previous Dec. The `prev_year_month` helper must subtract from `year` as well. Covered by test 11.
- **Division by zero in averages**: new categories have zero history. The repository returns `0` for the sum and `0` for the "active month count"; `max(count, 1)` in the service guards against ZeroDivisionError.
- **Direction filter**: all expense sums are strictly `direction=expense`. Including `transit` or `adjustment` would double-count or hide. Enforce at the repository and verify in tests (16).
- **Soft-deleted transactions excluded**: standard repository filter. Verify in test 14.
- **Running the month-summary in the UI**: this view is read every page load for the home dashboard and budget views. Measure wall-clock on 10 years of seeded data in Phase 4; if slow, add an in-memory per-request cache keyed on `max(audit_log.id)` (don't speculate here).
- **Timezone**: `operation_date` is naive `DATE`. "Current month" is driven by the display timezone (`Europe/Warsaw`, ADR-0007). This service receives `(year, month)` already resolved by the caller.
- **Integer floor-division trap**: `-25_000 // 2 == -12_500` in Python but `-25_001 // 2 == -12_501` (floors away from zero for negatives). Use `Decimal` + `ROUND_HALF_EVEN` for averages, not `//`.

## Handoff notes

Phase 3 consumers:

- **Budget router (T-036)**:
  - `GET /budget` → `month_summary(conn, now.year, now.month)`.
  - `GET /budget/manage` → `list_defaults` / `list_recurring_for_month` / `list_one_offs_for_month` directly, plus `resolve_budget` for a preview.
  - Mutations go through `repositories.budgets.*` (audit written there).
- **Home dashboard (T-039)** calls `month_summary` for the "this month" tile.
- **Analytics router (T-038)** reuses `sum_by_category_in_month` and the overall / yearly sums directly from the repository, not via this service — the budget service is scoped to budget resolution, not generic analytics.
