# T-038 — Analytics Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

Interactive analytics over the **persistent** transaction log (not planned/virtual). Multi-chart dashboard: spend by category over time, income vs expense trend, cash-flow by account, top categories per month. All charts Plotly, all converted into base currency with **historical FX rates** (not latest — this is a retrospective view, ADR-0006). Groupby selector lets the user pivot across category / account / direction / month-quarter-year.

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md).
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — `transactions.list_filtered`, aggregated reads.
  - [`../phase-2/T-020-fx-service.md`](../phase-2/T-020-fx-service.md) — `fx.convert(conn, amount, date, from_ccy, to_ccy)` historical.
  - [`../phase-2/T-027-export-service.md`](../phase-2/T-027-export-service.md).
- ADRs:
  - [`../../adr/0006-multi-currency-model.md`](../../adr/0006-multi-currency-model.md) — historical FX for retrospective aggregates.
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — direction derived from category; transits + adjustments excluded from income/expense charts.
  - [`../../adr/0020-import-deferred-export-v1.md`](../../adr/0020-import-deferred-export-v1.md) — export in v1 operates on the filtered record set.
  - [`../../adr/0021-functional-style-no-oop.md`](../../adr/0021-functional-style-no-oop.md).
- Service calls (new, under `services.analytics` — add in this task if not already present, as a Phase 2-shaped helper even though it lands in Phase 3; alternatively put aggregation inside the router using repo read helpers only. Prefer the service to keep the router thin):
  - `services.analytics.spend_by_category_over_time(conn, filter, group=month) -> AnalyticsSeries`.
  - `services.analytics.income_vs_expense_trend(conn, filter, group=month) -> AnalyticsSeries`.
  - `services.analytics.cash_flow_by_account(conn, filter, group=month) -> AnalyticsSeries`.
  - `services.analytics.top_categories_per_month(conn, filter, top_n=5) -> AnalyticsSeries`.
  - Shared base-currency conversion inside each service call via historical `fx.convert`.
- Reuse: `parse_filter(request)` from T-031 (shared transaction filter DTO parser).

## Deliverables

- Router module path: `src/budget_planner/web/routers/analytics.py`.
- Jinja templates:
  - `templates/analytics/index.html` — full page: filter sidebar + groupby selector + chart grid + export links.
  - `templates/partials/analytics/_charts.html` — the chart grid (`<section id="charts" ...>`), swapped on filter / groupby change.
  - `templates/partials/analytics/_chart.html` — a single Plotly figure wrapped in `<figure>` + `<figcaption>` + `<script type="application/json">` fig blob.
  - `templates/partials/analytics/_filter_form.html` — reuse of T-031 filter inputs + groupby `<select>` + top-N `<select>`.
- Tests: `tests/integration/web/test_analytics.py`.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/analytics` | filter query + `group=month\|quarter\|year`, `by=category\|account\|direction`, `top_n` | full page `index.html` | all four `services.analytics.*` with filter + group | filter + groupby + topN form: `hx-get="/analytics/charts"`, `hx-target="#charts"`, `hx-swap="outerHTML"`, `hx-trigger="change delay:200ms, keyup changed delay:400ms from:input[name=q]"`, `hx-push-url="true"` |
| GET | `/analytics/charts` | same query | fragment `_charts.html` | same services | — |
| GET | `/analytics/export` | filter query + `format=csv\|parquet` + `view=spend_cat\|inc_exp\|cash_flow\|top_cats` | file download | selected analytics service → `export.export_csv` \| `export.export_parquet` | plain `<a>`, not HTMX |

## Template structure

`templates/analytics/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Analytics · Budget Planner{% endblock %}
{% block main %}
  <header class="mb-10 flex items-end justify-between gap-6">
    <div>
      <h1 class="font-serif text-5xl leading-none">Analytics</h1>
      <p class="text-muted mt-2">
        All figures in <span class="font-mono">{{ base_ccy }}</span>, historical FX.
      </p>
    </div>
    <nav class="flex flex-wrap gap-3 text-sm">
      <a class="link-muted" href="/analytics/export?view=spend_cat&format=csv&{{ filter.as_qs }}">Export spend-by-category</a>
      <a class="link-muted" href="/analytics/export?view=inc_exp&format=csv&{{ filter.as_qs }}">Export income vs expense</a>
      <a class="link-muted" href="/analytics/export?view=cash_flow&format=csv&{{ filter.as_qs }}">Export cash-flow</a>
      <a class="link-muted" href="/analytics/export?view=top_cats&format=csv&{{ filter.as_qs }}">Export top categories</a>
    </nav>
  </header>

  <div class="grid grid-cols-[300px_1fr] gap-10">
    <aside>{% include "partials/analytics/_filter_form.html" %}</aside>
    <section>
      {% include "partials/analytics/_charts.html" %}
    </section>
  </div>
{% endblock %}
```

`templates/partials/analytics/_charts.html` (chart grid is a **bento layout**, not a uniform tile set):

```jinja
<section id="charts" class="grid gap-6 grid-cols-6 auto-rows-[260px]">
  <article class="col-span-6 row-span-2">
    {% set fig = figs.spend_cat %}
    <h2 class="font-serif text-xl mb-2">Spend by category · {{ group_label }}</h2>
    {% include "partials/analytics/_chart.html" %}
  </article>

  <article class="col-span-3">
    {% set fig = figs.inc_exp %}
    <h2 class="font-serif text-xl mb-2">Income vs expense</h2>
    {% include "partials/analytics/_chart.html" %}
  </article>

  <article class="col-span-3">
    {% set fig = figs.cash_flow %}
    <h2 class="font-serif text-xl mb-2">Cash-flow by account</h2>
    {% include "partials/analytics/_chart.html" %}
  </article>

  <article class="col-span-6">
    {% set fig = figs.top_cats %}
    <h2 class="font-serif text-xl mb-2">Top categories per month</h2>
    {% include "partials/analytics/_chart.html" %}
  </article>
</section>
```

`templates/partials/analytics/_chart.html`:

```jinja
<figure>
  <div id="chart-{{ fig.id }}" class="h-full w-full"></div>
  <figcaption class="sr-only">{{ fig.aria_summary }}</figcaption>
</figure>
<script type="application/json" id="fig-{{ fig.id }}">{{ fig.json|safe }}</script>
<script>
  (() => {
    const el = document.getElementById("chart-{{ fig.id }}");
    const data = JSON.parse(document.getElementById("fig-{{ fig.id }}").textContent);
    Plotly.react(el, data.traces, data.layout, {displayModeBar: false, responsive: true});
  })();
</script>
```

Shared partials: `_flash` (OOB on fetch errors), `_direction_badge` (used in `_filter_form.html` for direction chips).

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| Filter form `change`/`keyup` | `#charts` | `outerHTML` | Chart grid re-renders; four Plotly `react` calls fire from the inlined scripts; URL updated. | 500 → OOB flash with a muted "retry" link. |
| Groupby `<select>` change | `#charts` | `outerHTML` | Same as above. | Same. |
| Top-N `<select>` change | `#charts` | `outerHTML` | Same as above. | Same. |
| Export links | — | — | Browser download. | — |

No `HX-Trigger` headers emitted. Analytics is read-only; it does **not** listen for `balance-stale` either (users explicitly re-run analytics; a tab left open does not need to recompute on every unrelated edit) — add it only if the home dashboard embeds an analytics card.

## Validation / acceptance

- `GET /analytics` → `200`; DOM has four `<article>`s with chart targets `chart-spend_cat`, `chart-inc_exp`, `chart-cash_flow`, `chart-top_cats`; each has a `<script type="application/json">` sibling with parseable JSON.
- `GET /analytics/charts?group=quarter&date_from=2026-01-01` → `200`; fragment only; `_charts.html` renders four articles; each service called once; conversion uses historical rates per txn `operation_date`.
- Transit + adjustment transactions are **excluded** from "Income vs expense" and "Spend by category" per ADR-0008 / ADR-0011 (visible as a filter stripe hint under the chart in `aria-describedby`: "Transits & reconciliations excluded.").
- Groupby `category` on cash-flow swaps the series grouping; `direction` groupby reduces to `income` vs `expense` vs `transit`.
- `top_n` default `5`; `top_n=10` renders 10 bars per month.
- Export: `GET /analytics/export?view=spend_cat&format=csv&...` → `200`; CSV body has one row per `(category, period)` with amounts in base currency minor units.
- A11y: each chart has a visually hidden `<figcaption>` summarising its content (totals + extremes); charts are keyboard-navigable via Plotly's built-in handlers; `<select>` controls have `<label for>`.
- The page performs **two or fewer** full-table scans of `transactions` per fragment load; aggregation lives in the service and uses SQL `GROUP BY` for all four charts (ideally one query that `UNION ALL`s or four narrow queries). N+1 risk is called out below.

## Risks & gotchas

- **Historical FX fan-out.** Converting every transaction at its own `operation_date` rate requires either (a) joining `fx_rates` by date in SQL — fastest, but needs all required rates present; or (b) iterating rows in Python calling `fx.convert`. Pick (a): fetch missing rates before aggregation. The service must prefetch unique `(operation_date, currency)` pairs and call `fx.get_rate` once per pair. Flag for T-020 if not supported.
- **Grouping buckets.** `month` = `strftime('%Y-%m', operation_date)`, `quarter` = `strftime('%Y', ...) || '-Q' || ((CAST(strftime('%m', ...) AS INT) - 1) / 3 + 1)`, `year` = `strftime('%Y', ...)`. Compute in SQL; service returns strings as period keys.
- **Top-N stability.** When two categories tie, sort by name secondary. Deterministic so chart doesn't jitter on refresh.
- **Chart container height.** The bento grid uses `auto-rows-[260px]` and spans — tall chart spans two rows for `540px` effective height. Plotly needs explicit height; `h-full w-full` inside a sized grid cell handles it, but `Plotly.react` must be re-called after swap (handled by the inline script).
- **Multiple Plotly `react` calls per swap.** Each `_chart.html` includes its own `<script>` block. On HTMX `innerHTML`/`outerHTML` swap, HTMX runs inline `<script>` tags by default — confirm by testing. If it does not in the current HTMX version, add `hx-on::afterSwap="…initCharts()…"` on `#charts` instead. Document and test.
- **Export selects one view at a time.** The query carries both the filter and the `view`; the handler dispatches to the matching service and streams.
- **No cross-currency fx for transits.** ADR-0009 blocks cross-currency transits in v1; the cash-flow chart therefore never has to split one txn across two FX rates.
- **Base-currency ambiguity.** Analytics is always in `base_currency`. The page tells the user this in the subheader. Users with a non-PLN base see the chip reflect that.
- **Date-less edge.** Transactions whose month pre-dates any FX rate for the pair fall back to the most recent historical rate; the chart shows a muted asterisk on affected periods and `aria-describedby` summarises the fallback.

## Anti-template design-quality move

The chart grid is a **bento composition**, not a 2×2 tile grid:

- Grid is 6 columns × multiple rows; the hero "Spend by category over time" is `col-span-6 row-span-2` (feels wide and historical); "Income vs expense" and "Cash-flow by account" are `col-span-3` side-by-side (two voices in conversation); "Top categories per month" is `col-span-6` beneath as a horizontal rhythm. Grid-breaking proportions beat uniform tiles.
- Chart typography inherits the shell: axis labels in a geometric sans at 11px, tick labels in `tabular-nums`, titles are plain `<h2>` in the serif display sitting **outside** the chart (not Plotly titles) — the figure feels like a magazine chart.
- Palette: a single oklch accent for the dominant series (fortune or sum), muted inks for the rest; one "warm warning" oklch for negative cash-flow months. Nothing rainbow.
- Hover interactions: `displayModeBar: false` to kill the floating Plotly toolbar; crosshair hover with a single tooltip in the serif figure style. No zoom buttons — users use filter sliders.
- Filter sidebar matches the transactions page's two-column rhythm so navigation feels continuous. Groupby selector sits above the sidebar, isolated with a hairline rule — a clear editorial pivot above a reading of the data.

## Handoff notes

- `services.analytics.*` is a new service module landed here; the shared `fx` prefetch helper can graduate to `services.fx.ensure_rates(conn, pairs)` for reuse. Flag for T-020 if that shape is missing.
- T-039 (home dashboard) **may** embed a stripped-down "last 30 days spend by category" sparkline — if so, call `services.analytics.spend_by_category_over_time` directly; no new endpoint needed.
- T-053 (polish) may lazy-load Plotly only on `/analytics` and `/forecast` via a `<link rel="preload">` from `base.html` conditional on route — a later ADR.
- The shared `parse_filter(request)` function from T-031 is imported here. Any new filter field must be added there, not duplicated.
