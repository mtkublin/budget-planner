# T-066 — Budget Consolidation

> Phase 6 — UX redesign. Status: pending.

## Purpose

Rewrite `/budget` as three stacked sections on a single page: Monthly summary (planned-vs-actual per category + remainder bar + month selector), Rules editor (lifted from today's `/budget/manage`, three-tier columns per category), and Breakdown (three Plotly figures lifted from `/analytics`: spend-by-category, cashflow-by-account, income-vs-expense trend). Make Budget the one place a user asks "am I inside my plan, and where is the money going?".

## Inputs / prerequisites

- Upstream tasks: T-061 (shell).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — Budget page composition.
- Adjacent standards: T-053 tokens; `rules/web/design-quality.md`.
- Existing services (reuse):
  - `services.budget.month_summary(month=…)` — per-category planned vs actual + totals.
  - `services.budget.rules_for_category(category_id)` — three-tier rules (default, recurring-monthly, one-off) per ADR-0019.
  - `services.analytics.spend_by_category(from_date, to_date)` — bar data.
  - `services.analytics.cashflow_by_account(from_date, to_date)` — bar data.
  - `services.analytics.income_vs_expense(from_date, to_date)` — grouped bars.

## Deliverables

Updated files:

- `src/budget_planner/web/templates/budget/index.html` — rewritten as three stacked `<section>`s.
- `src/budget_planner/web/routers/budget.py`:
  - `GET /budget?month=YYYY-MM` — full page.
  - `GET /budget/summary?month=…` — fragment (used by the month selector swap).
  - `GET /budget/breakdown?from=…&to=…` — fragment returning the three Plotly figures (JSON embedded via `plotly.js` HTML output).
- `src/budget_planner/web/templates/budget/_summary.html` — Section 1.
- `src/budget_planner/web/templates/budget/_rules.html` — Section 2 (lifted from `/budget/manage`'s current template; keep forms, add nothing).
- `src/budget_planner/web/templates/budget/_breakdown.html` — Section 3; wraps three figures each in a `<figure class="surface surface--raised">` with `<figcaption>`.

Not deliverables:

- No new rule logic. The Rules editor is a lift-and-shift of the current `/budget/manage` content.
- No new analytics figure code. Reuse the existing service functions and the T-053 chart theming.
- `/analytics` page is not deleted here; T-070 redirects it to `/budget#breakdown`.

## Step-by-step

1. **Page shell.** Three `<section>` elements with ids `summary`, `rules`, `breakdown` so the `/analytics` redirect can land users at `/budget#breakdown`. Each section has an eyebrow + `<h2>` + body.
2. **Section 1 — Monthly summary.**
   - Month selector top-right: `<form hx-get="/budget/summary" hx-target="#budget-summary-body" hx-trigger="change">` with a `<select name="month">` listing the last 24 months plus the current month (default = current month).
   - Body: table of category rows. Columns: category · planned · actual · remainder (number) · remainder bar.
   - Remainder bar: like the Overview Panel B bar, accent fill on `--color-surface-sunken` track; width = `100 * actual / planned` clamped to `[0, 100]`.
   - Totals row at the bottom (hairline-top): planned, actual, remainder in base currency.
3. **Section 2 — Rules editor.**
   - Lift the current `/budget/manage` content verbatim. If it currently uses a different route, keep both paths working during Phase 6; T-070 will redirect `/budget/manage` → `/budget#rules`.
   - Three-tier resolution per category rendered as a single table per category block with three editable columns: `Default` · `Recurring (this month)` · `One-off (this month)`.
4. **Section 3 — Breakdown.**
   - Three charts rendered as Plotly HTML divs (`figure.to_html(include_plotlyjs="cdn", full_html=False)`).
   - Apply the T-053 Plotly theme (paper_bgcolor + plot_bgcolor = `var(--color-surface-raised)`, font family Inter, hairline gridlines).
   - Date range selector at the top of the section (default: last 12 months): `<form hx-get="/budget/breakdown" hx-target="#budget-breakdown-body" hx-trigger="change">`.
5. **Required-qualities audit.** (1) hierarchy (section eyebrows + display-size month total) ✓, (2) rhythm ✓, (10) data-vis integrated (one figure component shared across all three charts) ✓, (5) semantic colour ✓.

## Validation / acceptance

- `GET /budget` returns 200 with three visible `<section>`s (`#summary`, `#rules`, `#breakdown`) in that order.
- `GET /budget?month=2026-09` renders the summary table for September 2026.
- `GET /budget/summary?month=2026-09` returns the summary fragment (no `<html>` wrapper).
- `GET /budget/breakdown?from=2025-10-01&to=2026-10-31` returns the three Plotly divs.
- Integration test `tests/integration/web/test_budget.py`:
  - `test_three_sections_present`
  - `test_month_selector_swaps_summary_via_htmx`
  - `test_breakdown_renders_three_figures`
  - `test_remainder_bar_width_matches_actual_over_planned`
- No duplicate scrollbars on the breakdown section (each `<figure>` has `overflow: hidden`; the Plotly SVG scales inside).
- `grep` guard passes (no hard-coded palette).

## Risks & gotchas

- **Plotly bundle size.** Loading `plotly.js` on every Budget request bloats the page. Options: use `include_plotlyjs="cdn"` (default here) or lazy-load Plotly only when the Breakdown section is in the viewport (IntersectionObserver). The CDN path is fine for v1 single-user local; revisit if a user complains.
- **Three charts, one request.** Pre-compute all three figures in `/budget/breakdown` to avoid three sequential service calls. If any one chart's service is slow, parallelise via `asyncio.gather`.
- **Rules editor forms** must keep `hx-post` targets stable so the existing recurring/one-off rule handlers continue to work. Lift the template, don't rename form fields.
- **Month selector list drift.** Build the list server-side from the earliest transaction date forward; don't hard-code a window.
- **Fragment caching.** HTMX swaps on `#budget-summary-body` and `#budget-breakdown-body` must preserve the surrounding section container's `aria-live` region.

## Handoff notes

- Hand-off to T-070 (redirects): `/analytics` → `/budget#breakdown`; `/budget/manage` → `/budget#rules`.
- Hand-off to T-071 (a11y): the Rules editor is dense; audit focus order and label association after the lift.
- Commit shape: `feat(T-066): /budget — summary + rules + breakdown on one page`.
