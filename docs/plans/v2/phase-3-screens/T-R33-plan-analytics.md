# T-R33 — Plan · Analytics

- **Phase**: 3 — Screens
- **Sequential**: after T-R29, T-R43, Phase 5 charts.
- **Depends on**: T-R43 (`services.analytics.bundle`), T-R49 (analytics chart templates).
- **References**: handoff §Plan · Analytics, ADR-0054, ADR-0056 §6.

## Context

Analytics replaces the Plotly-backed `/analytics` with a server-rendered SVG + table layout. Three regions: spend-by-category (horizontal bars with delta vs 12-month avg), income-vs-expense bars by month, largest single items list. Period selector: month / 3 months / YTD / 12 months.

## Deliverables

- `templates/plan/_analytics.html` composing:
  - Period `segmented` control with `hx-get="/plan/analytics?period=…"` fragment swap.
  - `_spend_by_category.html` — horizontal bars via `charts.horizontal_bars`; row = pill + bar + amount + delta chip (red when above average, green when below). Links to `/ledger?view=actual&category_id=…&date_from=…` for drill-down.
  - `_income_vs_expense.html` — grouped bars via `charts.grouped_bars`; income + expense per month in the period.
  - `_largest_items.html` — plain list of top 10 single transactions by signed amount within the period.
- All three regions have `<details>` data-table fallbacks (ADR-0054 §3).
- Analytics endpoint returns the shape:
  ```python
  @dataclass(frozen=True)
  class AnalyticsBundle:
      period_label: str
      spend_by_category: tuple[CategorySpend, ...]
      income_vs_expense: tuple[MonthlyIE, ...]
      largest_items: tuple[LargeItem, ...]
  ```
- Integration tests cover: period switch via HTMX; delta chip colours (above/below avg); drill-down link URL shape; empty-state render.

## Acceptance criteria

- Visual-regression at D/T/M matches handoff `desktop-2b-plan-analytics.png`.
- Spend-by-category rows carry an `aria-label` describing the delta ("ZAKUPY 3,200 PLN, 18 % above 12-month average") — no colour-only state.
- Drill-down link resolves to a Ledger view with the correct filter chips active.
- Period swap preserves scroll position within the Plan shell (HTMX `hx-swap-oob` on the segmented control + content region).

## Validation hook

```sh
pytest tests/integration/web/test_plan_analytics.py && \
  just test-visual --filter analytics && \
  invoke frontend-visual-audit at 1440 1024 375 against "/plan?tab=analytics"
```

## Risks & gotchas

- Largest items list excludes transits (same rule as v1 analytics; transits distort the ranking).
- Delta vs 12-month average must handle categories with fewer than 12 months of history — show "insufficient history" chip instead of an inflated %.
- Period "YTD" at Jan 1 means one data point; render gracefully.

## Handoff notes

- T-R68 (Accounts sparkline) uses the same `charts.sparkline` helper; T-R33 does not need it, but keep consistent chart styling tokens.
- Phase 5 T-R49 shipped the chart templates; this task composes them into the page shell.
