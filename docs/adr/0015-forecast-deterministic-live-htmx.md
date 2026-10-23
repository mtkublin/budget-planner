# ADR-0015: Forecasting — Deterministic Projection, Live via HTMX

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

### Method: deterministic projection

For each day in the horizon, project per-account balance by applying:

```
projected_balance(account, date) =
    current_balance(account, today)
  + Σ planned_transactions affecting account where operation_date ∈ (today, date]
  + Σ virtual_recurring_occurrences affecting account in the same range
```

Fortune total = sum over accounts, each converted into base currency using the **latest cached FX rate** (not historical — this is a forward-looking view).

### Liveness

On-request recompute. The forecast page calls the pure forecast function on each load. Any mutation to planned/recurring/account state returns an `HX-Trigger: forecast-stale` response header; the forecast fragment, if visible, swaps itself.

No background worker, no WebSocket, no client-side recompute.

## Consequences

- Truthful: the forecast reflects user-entered plans, not inferred habits.
- Pure, cheap, easy to test with fixtures of known expected output.
- Horizon can be arbitrary (6 months, 5 years) — same code path.

## Alternatives Considered

- **ML / trend-based (ARIMA, Prophet)**: wrong signal — predicts past habits, not planned events; needs years of data.
- **Hybrid (deterministic + trend overlay for unplanned categories)**: interesting v2; adds complexity.
- **WebSocket push**: overbuilt for single-user local app.
- **Client-side JS recompute**: duplicates logic in Python and JS; DRY violation.
