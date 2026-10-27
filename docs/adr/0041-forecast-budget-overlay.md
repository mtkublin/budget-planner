# ADR-0041: Forecast — Budget Overlay for Unaccounted Expected Spend

- **Status**: Accepted
- **Date**: 2026-10-27
- **Supersedes (partial)**: [ADR-0015 §Alternatives Considered](0015-forecast-deterministic-live-htmx.md) — the "hybrid (deterministic + trend overlay for unplanned categories)" option, previously deferred to v2, is partially promoted into v1 as a *budget-driven* overlay (not a trend-driven overlay).

## Context

ADR-0015 defined the forecast as:

```
projected_balance(account, date) =
    current_balance(account, today)
  + Σ planned_transactions in (today, date]
  + Σ virtual_recurring_occurrences in (today, date]
```

This under-reports expected future spend whenever the user has a **budget** for a category but has not yet entered planned transactions or recurring rules that fully consume that budget. In practice, discretionary categories (Groceries, Dining, Transport) are routinely budgeted but almost never fully pre-populated as planned rows — so the forecast line trends optimistic.

The Budget page already surfaces the "unaccounted" gap on the current month via `MonthTotals.remaining_minor = budgeted − spent − committed` ([ADR-0039](0039-budget-daily-spend-includes-recurring.md)). The forecast should express the same economic view.

## Decision

The forecast adds a **budget overlay**: synthetic expense cash events representing the per-category per-month residual budget that is not already covered by planned transactions or recurring occurrences.

### Formula

For every ``(category c, month m)`` such that ``month_start(m) ≤ horizon_end`` and the three-tier `resolve_budget(c, m)` returns a non-null amount:

```
spent_so_far(c, m)       = Σ actual expense transactions in [max(month_start, series_start), today] on c
committed_future(c, m)   = Σ (planned expense rows + recurring expense occurrences) in (today, month_end] on c
unaccounted(c, m)        = max(resolved_budget(c, m) − spent_so_far(c, m) − committed_future(c, m), 0)
```

- ``spent_so_far`` is included only for the month that contains ``today`` (future months have no "so far" slice).
- ``committed_future`` uses the same expense-direction filter as [ADR-0039](0039-budget-daily-spend-includes-recurring.md) and reuses the planned/recurring event collection the forecast already builds — no new SQL.
- ``unaccounted`` is clamped at zero per category — a category whose planned + recurring exceed its budget does **not** become income.

### Distribution

``unaccounted(c, m)`` is distributed as expense cash events across:

```
distribution_window(m) = [max(today + 1 day, month_start(m)),  min(month_end(m), horizon_end)]
```

- Daily share = ``ROUND_HALF_EVEN(unaccounted / len(distribution_window))``.
- Any rounding residual is absorbed by the final day of the window so the sum equals ``unaccounted`` exactly.
- Zero-length windows (e.g. month already fully past ``today`` on day-0) are skipped.

Even distribution matches how the Budget page expresses "Left per day" and keeps the forecast chart smooth rather than step-shaped.

### Account allocation

Budgets are account-agnostic. The overlay allocates every synthetic event to the **first active account by id** (``min(account_ids)`` among ``accounts_repo.list_all(include_deleted=False)``). Rationale:

1. The dominant consumer of the forecast is the base-currency aggregate line — account attribution matters only for the per-account breakout.
2. Introducing a "primary spending account" preference is out of scope here and can be added later via [ADR-0025](0025-user-preferences-and-income-anchor.md).
3. Deterministic by account id → tests remain stable and reproducible.

### Public API

``services.forecast.forecast(...)`` grows one keyword-only argument:

```python
def forecast(
    conn: sqlite3.Connection,
    http: httpx.Client,
    today: dt.date,
    horizon_days: int,
    base_currency: str,
    *,
    include_budget_overlay: bool = True,
) -> ForecastSeries: ...
```

Default is on. Callers that want the pre-ADR-0041 behaviour pass ``include_budget_overlay=False`` (unit tests exercising the pure planned+recurring projection do this).

The output shape (``ForecastSeries`` → ``DayPoint`` → ``AccountBalancePoint``) is unchanged. Budget-driven events flow through the same ``_CashEvent`` pipeline as planned/recurring and inherit identical FX conversion + rounding behaviour.

## Consequences

- Forecast line reflects the user's *stated intent* (budget), not just their *entered future events*. Matches the Budget-page "left per day" economic view.
- No new persistence; purely derived.
- Per-account series for the "primary" account dips more aggressively than its tracked planned/recurring would suggest. This is correct for the aggregate and acceptable for v1; a future preference can relocate the overlay.
- The deterministic contract from ADR-0015 is preserved: same DB snapshot + same ``today`` → same series.

## Alternatives Considered

- **Apply only to totals, bypass per-account**: breaks the ``totals_base_minor == sum(by_account.base_minor)`` invariant and complicates charting. Rejected.
- **Allocate overlay proportionally across accounts by historical spend share**: more realistic per-account view, but requires an extra 90-day rolling query, introduces non-determinism when txn history is sparse, and still doesn't fix the attribution for brand-new accounts. Defer.
- **Single end-of-month event instead of daily distribution**: produces a sawtooth forecast chart. The current per-day distribution matches the Budget page's "per-day" headline.
- **Opt-in via query param (default off)**: discoverability is poor; the budget page already treats "committed" as first-class — the forecast should match that stance by default.

## Links

- [ADR-0015 Forecast deterministic, live via HTMX](0015-forecast-deterministic-live-htmx.md)
- [ADR-0039 Budget daily spend includes recurring](0039-budget-daily-spend-includes-recurring.md)
- [ADR-0014 Budget flat, no rollover, three-tier](0014-budget-flat-no-rollover-three-tier.md)
- [ADR-0006 Multi-currency model](0006-multi-currency-model.md)
