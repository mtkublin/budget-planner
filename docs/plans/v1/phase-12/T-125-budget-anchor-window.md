# T-125 [S] Budget period = last-anchor-income → next-anchor-income (per-category `spent_minor`)

> Depends on: T-120, [ADR-0041](../../../adr/0041-budget-period-anchor-window.md). Blocks: nothing.

## Scope

Service-layer arithmetic only. No schema change, no template change.

### `services/budget.py`

- New helper `_resolve_period_start(conn, today, year, month, anchor_category) -> date`:
  - If `anchor_category` is `None` → return `date(year, month, 1)`.
  - Else query `transactions_repo.list_filtered(TransactionFilter(date_to=today, category_ids=(anchor_category.id,), directions=(Direction.INCOME,)))` and return the most recent `operation_date` (sort DESC in Python; v1 volumes are tiny).
  - If no such transaction exists → return `date(year, month, 1)`.
- `month_summary` wires:
  - After `_resolve_anchor`, call `_resolve_period_start` with the resolved anchor category (`None` when `_resolve_anchor` returned the fallback path).
  - Pass the resulting `period_start` into `_expense_txns_in_range` for `this_txns` **only**. `prev_txns`, `year_txns`, `all_txns` keep existing windows.
  - Zero-budget months: fall through to the month-start branch (unchanged behavior).

### Tests — `tests/unit/services/test_budget.py`

- Anchor-income transaction mid-month: per-category `spent_minor` reflects only post-anchor expenses.
- No prior anchor transaction: falls back to month start (equivalent to old behavior).
- Zero-budget month: unchanged behavior.
- No anchor category configured: unchanged behavior.
- `budgeted_minor` and `remaining_minor` formula consistency after the window shift.

## Non-goals

- Changing `committed_in_window` (T-120).
- Changing `next_income_date` / `days_until_next_income` math.
- Prorating `budgeted_minor` (ADR-0041 explicitly rejects).
- Changing analytics windows (`avg_*`, `delta_vs_prev_month`).

## Acceptance

- Fixtures without a configured anchor or without a prior anchor-income transaction keep their current per-category `spent_minor` values — no regression on Phase 9 / T-120 tests.
- `MonthTotals` dataclass unchanged.
- Coverage ≥ 90%.
- `just ci` green.
