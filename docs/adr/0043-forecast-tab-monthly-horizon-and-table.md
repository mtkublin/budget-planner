# ADR-0043: Forecast Surface — Monthly Horizon + Breakdown Table

- **Status**: Accepted
- **Date**: 2026-10-27
- **Amends**: [ADR-0015](0015-forecast-deterministic-live-htmx.md) (Forecasting — Deterministic Projection)

## Context

ADR-0015 defined a daily deterministic projection with a user-selectable horizon. In practice:

1. Users think about forecast runway in **months / years**, not days.
2. The 365-day cap excluded multi-year planning scenarios (loan payoff windows, savings goals).
3. The chart alone omits the detail users actually need to act on — the per-month income / planned-expense / net breakdown that drives the EOM balance curve.

## Decision

### 1. Horizon unit becomes **months**

- Primary input renamed `horizon_months` (default **12**, min **1**, max **60**).
- Service still projects daily under the hood (ADR-0015 invariant preserved); the router expands months → days (`horizon_days = end_of_month_offset_from_today`).
- Legacy `horizon_days` query param is removed; this is a v1 UI change, no persisted state depends on it.

### 2. New monthly aggregation API

`services.forecast.forecast_monthly(conn, http, today, horizon_months, base_currency) -> MonthlySeries`

Per month in `[today.month, today.month + horizon_months - 1]` returns:

- `month` (first-of-month `date`)
- `income_base_minor` — sum of signed income events landing in the month (base currency)
- `expense_base_minor` — sum of (absolute) expense events in the month (base currency)
- `net_base_minor` — `income - expense`
- `end_balance_base_minor` — projected total fortune at end of month

Transits net to zero across accounts and are excluded from income / expense totals. Adjustments are not emitted by the forecast engine (planned adjustments unsupported, ADR-0011).

The daily `forecast()` function remains the primary driver; `forecast_monthly()` composes over its daily output + raw event stream — one DB pass per request.

### 3. Forecast tab is promoted into the rail nav

Previously the `/forecast` route was reachable only by URL. It becomes a first-class nav entry (`g f` shortcut), placed after Budget.

### 4. Page composition

```
Forecast
  ├─ Horizon control (number input, unit = months)
  ├─ Chart (daily series, same as today, extends over the chosen window)
  └─ Monthly table
       Month · Income · Expenses · Net · Projected balance (EOM)
```

Table reuses `partials/forecast/_table.html`; both chart + table share the `#forecast-view` wrap so one HTMX swap updates both.

## Consequences

- Horizon math moves to the router boundary; service stays pure in days.
- Multi-year planning now fits — 60 months × ~31 days = ~1860 points per chart; still cheap (one pass through planned rows + rule expansion).
- Monthly table exposes the "why" behind the curve — users can see which month a dip comes from without hovering the chart.
- The `HX-Trigger: forecast-stale` contract (ADR-0015) still fires both chart + table since they share one swap target.

## Alternatives Considered

- **Keep days as the input, add a separate "months" preset dropdown**: double-input UX, no gain.
- **Push monthly aggregation into the template via Jinja grouping**: scattering domain math across layers, violates "fat services" (CLAUDE.md).
- **Compute monthly series client-side from the Plotly payload**: duplicates signed-leg logic in JS, DRY violation (same reasoning that killed client-side recompute in ADR-0015).
