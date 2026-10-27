# ADR-0041: Budget "Period" is Last-Anchor-Income → Next-Anchor-Income, Not Calendar Month

- **Status**: Accepted
- **Date**: 2026-10-27
- **Amends**: ADR-0025 §F4.6, ADR-0039
- **Related**: ADR-0038 (`next_due`), ADR-0014 (budget tiers)

## Context

Budget math is anchored on the user's paycheck. The user asks a single question of the Budget page: "how much do I still have to spend between now and the next income arrival?" ADR-0039 already fixed the forward half of that equation (`committed_minor` on `[today, next_income_date)`), so the "Left per day" headline is honest about scheduled commitments.

The backward half — the `spent_minor` figure — is still month-based. A user paid on the 25th sees Budget `spent` reset on the 1st; between the 1st and the 25th the "spent" line double-counts expenses that already fell on the *previous* paycheck's budget. In concrete terms: pay day was Oct 25, today is Nov 5, and `spent` currently includes Oct 1–Oct 24 expenses that belong to the previous cycle. The headline then says the user has less to spend than they really do.

The budget period should mirror the paycheck cycle on *both* sides of today.

## Decision

Shift the per-category `spent_minor` window from the calendar month `[month_start, month_end]` to the paycheck window `[last_anchor_date, today]`, where `last_anchor_date` is the operation date of the most recent **actual** (promoted) transaction in the configured income-anchor category with `operation_date <= today`.

### Resolution rules for `last_anchor_date`

1. **Promoted anchor-category transaction on-or-before `today` exists** → use the most recent such transaction's `operation_date`.
2. **No such transaction exists** → fall back to `date(year, month, 1)` (start of the displayed month). This preserves the pre-ADR-0041 behavior for first-month-of-use scenarios where the user has not yet received a paycheck.
3. **No anchor category configured** → fall back to month start (same as case 2).
4. **Zero-budget month** (`budgeted_total == 0`) → fall back to month start. Zero-budget months already short-circuit `committed_minor` to 0 (ADR-0039) and `left_daily_spend_minor` to `None`; keeping `spent_minor` on month start here is only a cosmetic choice for the per-category table.

### What stays on the calendar month

- `budgeted_minor` — one budget per paycheck cycle *is* the user's mental model, but a cycle may span two calendar months, and the budget tiers (default / recurring / one-off) are keyed on `(year, month)` by [ADR-0014](0014-budget-flat-no-rollover-three-tier.md). Prorating would introduce ambiguity on cycle-straddling months and complicate the Yearly grid (F4.8). The resolved monthly budget is treated as the budget *for the cycle anchored in that month*.
- `remaining_minor = budgeted_minor - spent_minor` — formula unchanged, numerator now uses anchor-window spent.
- `committed_in_window` — already uses `[today, next_income_date)`, unchanged.
- `next_income_date`, `days_until_next_income`, `left_daily_spend_minor` — unchanged.
- Analytics: `avg_this_year_minor`, `avg_monthly_overall_minor`, `delta_vs_prev_month_minor` — explicitly stay on their existing month-based windows. These are backward-looking historical references, not current-cycle math.

### Service shape

In `services/budget.py`:

```python
def _resolve_period_start(
    conn: sqlite3.Connection,
    today: date,
    year: int,
    month: int,
    anchor_category: Category | None,
) -> date:
    """Return [last_anchor_date, today] window-start for spent summation."""
```

The helper reads promoted actuals (not planned, not virtual recurring) via `transactions_repo.list_filtered(TransactionFilter(date_to=today, category_ids=(anchor.id,), directions=(Direction.INCOME,)))`, sorts by `operation_date` DESC, and returns the top row's `operation_date`. The lookup intentionally does **not** peek at `planned_transactions` nor `services.recurring.expand` — only money that has actually landed counts as "the last paycheck".

`month_summary` calls `_resolve_period_start` immediately after `_resolve_anchor` and passes the resulting date to `_expense_txns_in_range` **only for the current-period slice** (`this_txns`). `prev_txns`, `year_txns`, and `all_txns` keep their existing windows.

## Consequences

- Immediately after a paycheck lands (promoted into actuals), `spent_minor` snaps to 0 for the new cycle and climbs from there until the next anchor. The user sees a clean reset.
- Mid-cycle, `spent` + `committed` + `remaining` all describe the same single window: `[last_anchor_date, next_income_date)`. The three numbers are now internally consistent.
- Users who have never recorded a paycheck see unchanged behavior (month-start fallback).
- The "Last anchor paycheck" is derived from **promoted transactions only**. Planned income rows that have not yet promoted do not shift the window — the user has to confirm the paycheck landed before Budget treats the cycle as rolled.
- Yearly grid, Rules section, and Overview balance/forecast panels are untouched.
- No schema change; no new indexes required (the existing `transactions(operation_date)` + `category_id` indexes cover the lookup; v1 volumes are tiny).

## Alternatives Considered

- **Prorate `budgeted_minor` across cycle-straddling months.** Rejected — the user explicitly chose "one budget per paycheck cycle" in planning. Proration would double-book one-off overrides and make the Yearly grid semantically fuzzy.
- **Use planned-income rows as the anchor.** Rejected — planned rows are a schedule, not a commitment. Treating a planned paycheck as a "received" paycheck would reset the budget prematurely and surprise the user if the deposit lands late.
- **Expose a "cycle" picker in the UI.** Rejected — adds a navigation primitive for a question the user never asked. The current cycle is always what the Budget page is about.
- **Keep the month and add a separate "cycle spent" number.** Rejected — same objection as ADR-0039: doubling the UI real estate for the same question.

## Non-goals

- Changing analytics windows (`avg_*`, `delta_vs_prev_month`).
- Changing committed-window math.
- Changing budget tier resolution ([ADR-0014](0014-budget-flat-no-rollover-three-tier.md)).
- Changing how the Yearly grid resolves cells (F4.8).
