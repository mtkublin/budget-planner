# T-037 — Forecast Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

Render the deterministic fortune forecast: per-account projected balance + base-currency fortune across a user-chosen horizon. Pure recompute on every GET (ADR-0015). Live update via a single HTMX fragment that listens for `forecast-stale` / `balance-stale` on `body` and re-fetches itself whenever any mutation elsewhere in the app invalidates projections.

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md).
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — read helpers.
  - [`../phase-2/T-020-fx-service.md`](../phase-2/T-020-fx-service.md) — `fx.get_rate(..., latest=True)`.
  - [`../phase-2/T-021-balance-service.md`](../phase-2/T-021-balance-service.md) — `balance.derive_balance`.
  - [`../phase-2/T-022-recurring-occurrence-generator.md`](../phase-2/T-022-recurring-occurrence-generator.md) — pure generator.
  - [`../phase-2/T-025-forecast-service.md`](../phase-2/T-025-forecast-service.md) — `forecast.forecast(conn, horizon_days) -> ForecastSeries`.
- ADRs:
  - [`../../adr/0015-forecast-deterministic-live-htmx.md`](../../adr/0015-forecast-deterministic-live-htmx.md) — on-request recompute; `HX-Trigger: forecast-stale` on relevant mutations.
  - [`../../adr/0006-multi-currency-model.md`](../../adr/0006-multi-currency-model.md) — base currency via latest FX rate (not historical) for forward projections (ADR-0015).
  - [`../../adr/0007-timezone-handling.md`](../../adr/0007-timezone-handling.md) — "today" uses display timezone.
- Service calls:
  - `services.forecast.forecast(conn, horizon_days: int) -> ForecastSeries` where `ForecastSeries` = `{dates: list[date], per_account: dict[account_id, list[int_minor_base]], fortune: list[int_minor_base], unit_currency: str, fx_rate_asof: date | None, fx_fallback: bool}`.

## Deliverables

- Router module path: `src/budget_planner/web/routers/forecast.py`.
- Jinja templates:
  - `templates/forecast/index.html` — full page: horizon selector + chart container + summary table.
  - `templates/partials/forecast/_fragment.html` — the chart + table block (`<section id="forecast-fragment" hx-trigger="forecast-stale from:body, balance-stale from:body" hx-get="/forecast/fragment?horizon_days={{h}}" hx-swap="outerHTML">`).
  - `templates/partials/forecast/_chart.html` — Plotly target `<div id="forecast-chart">` + the embedded `<script>` that calls `Plotly.react("forecast-chart", figJson, layout, config)`.
  - `templates/partials/forecast/_table.html` — tabular form of the series (end-of-horizon per account, delta from today, min/max).
  - `templates/partials/forecast/_fx_note.html` — small note "FX from {{ asof|date_fmt }}" with a warning dot when fallback used.
- Static assets: none (Plotly from CDN per ADR-0002, loaded by base.html).
- Tests: `tests/integration/web/test_forecast.py`.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/forecast` | query: `horizon_days` (default 365; min 7, max 10 * 365) | full page `index.html` | `forecast.forecast(horizon_days)` | horizon selector: `hx-get="/forecast/fragment?horizon_days={{ value }}"`, `hx-target="#forecast-fragment"`, `hx-swap="outerHTML"`, `hx-trigger="change"`, `hx-push-url="true"` |
| GET | `/forecast/fragment` | query: `horizon_days` | fragment `_fragment.html` | `forecast.forecast` | self-refresh: `hx-trigger="forecast-stale from:body, balance-stale from:body"`, `hx-get="/forecast/fragment?horizon_days={{h}}"`, `hx-swap="outerHTML"` |

## Template structure

`templates/forecast/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Forecast · Budget Planner{% endblock %}
{% block main %}
  <header class="mb-10 flex items-end justify-between gap-6">
    <div>
      <h1 class="font-serif text-5xl leading-none">Forecast</h1>
      <p class="text-muted mt-2">
        Deterministic projection in <span class="font-mono">{{ base_ccy }}</span>.
        {% include "partials/forecast/_fx_note.html" %}
      </p>
    </div>
    <form class="flex items-center gap-2 text-sm">
      <label for="horizon">Horizon</label>
      <select id="horizon" name="horizon_days"
              hx-get="/forecast/fragment"
              hx-target="#forecast-fragment"
              hx-swap="outerHTML"
              hx-trigger="change"
              hx-push-url="true">
        <option value="30"   {% if horizon_days == 30 %}selected{% endif %}>30 days</option>
        <option value="90"   {% if horizon_days == 90 %}selected{% endif %}>3 months</option>
        <option value="180"  {% if horizon_days == 180 %}selected{% endif %}>6 months</option>
        <option value="365"  {% if horizon_days == 365 %}selected{% endif %}>1 year</option>
        <option value="1825" {% if horizon_days == 1825 %}selected{% endif %}>5 years</option>
      </select>
    </form>
  </header>

  {% include "partials/forecast/_fragment.html" %}
{% endblock %}
```

`templates/partials/forecast/_fragment.html`:

```jinja
<section id="forecast-fragment"
         hx-trigger="forecast-stale from:body, balance-stale from:body"
         hx-get="/forecast/fragment?horizon_days={{ horizon_days }}"
         hx-swap="outerHTML">
  {% include "partials/forecast/_chart.html" %}
  {% include "partials/forecast/_table.html" %}
</section>
```

`templates/partials/forecast/_chart.html`:

```jinja
<figure class="mt-6">
  <div id="forecast-chart" class="h-[420px]"></div>
  <figcaption class="sr-only">Projected fortune over {{ horizon_days }} days, broken down per account.</figcaption>
</figure>
<script type="application/json" id="forecast-fig">{{ fig_json|safe }}</script>
<script>
  (() => {
    const el = document.getElementById("forecast-chart");
    const data = JSON.parse(document.getElementById("forecast-fig").textContent);
    Plotly.react(el, data.traces, data.layout, {displayModeBar: false, responsive: true});
  })();
</script>
```

Note: Plotly is loaded globally via CDN in T-030's `base.html`. The `fig_json` is built server-side with `plotly.graph_objects.Figure(...).to_json()` and injected via a dedicated `<script type="application/json">` block to avoid HTML escaping pitfalls when swapped by HTMX.

Shared partials: `_money` (table cells), `_flash` (OOB on fetch errors).

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| Horizon select `change` | `#forecast-fragment` | `outerHTML` | Fragment re-renders; URL updated via `hx-push-url`. | 500 → OOB flash. |
| `forecast-stale from:body` | `#forecast-fragment` | `outerHTML` | Fragment re-renders silently; chart redraws via `Plotly.react`. | — |
| `balance-stale from:body` | `#forecast-fragment` | `outerHTML` | Same as above — opening-balance edits, deletes, and reconciliation all shift the forecast. | — |

This router emits **no** `HX-Trigger` headers of its own — forecast is read-only.

## Validation / acceptance

- `GET /forecast` → `200`; DOM contains `#forecast-chart`, `#forecast-fig` script tag with valid JSON, and a summary table.
- `GET /forecast/fragment?horizon_days=90` → `200`; response body **does not** contain `<html>` (fragment only); JSON parses with keys `{traces, layout}` suitable for `Plotly.react`.
- `horizon_days < 7` or `> 3650` → `422` with an inline error on the select (returned as fragment with `_form_errors.html` note and the previous valid value restored).
- Deterministic test: given a fixture with (opening balance 1000, one planned +500 at today+10, one recurring monthly +200 starting today), `forecast(horizon_days=35)` yields a series whose end-of-horizon value equals `1000 + 500 + 200` for day 35 (± floor for same-day same-amount tie-breakers). Service covers; the router test asserts the number renders in the summary table.
- Base-currency conversion: with an account in `EUR` and `base_ccy=PLN`, series values are in minor units of PLN; `fx.get_rate(..., latest=True)` is called once per account, not per day. Flag for T-025 if the service queries per day.
- FX fallback: when `fx_fallback == True`, `_fx_note.html` renders a muted warning dot with `aria-describedby` pointing to a short "using last-known rate from {{ asof }}".
- Live update: open two tabs, both on `/forecast`. In tab A, trigger a planned transaction create (via `TestClient` emulation); tab B receives nothing (no SSE in v1). The listener only fires when the mutation returns in the same browser session — document this limitation in the ADR already (ADR-0015 implicit) and in the risks section below.
- A11y: `<figure>` + `<figcaption class="sr-only">`; summary table carries `<caption class="sr-only">`; horizon `<select>` is keyboard-navigable; `_fx_note` warning has `role="status"` + `aria-live="polite"`.

## Risks & gotchas

- **Live update is single-tab only.** `HX-Trigger` headers only fire on responses to the same browser's HTMX calls. Cross-tab sync requires SSE — out of scope for v1 (ADR-0015). Document in page copy via a muted "re-render on your edits" note or omit; do not promise cross-tab.
- **Plotly injection.** Interpolating a JSON blob directly into `<script>` is risky if the data contains `</script>`. Use the `<script type="application/json">` + `textContent` + `JSON.parse` pattern as shown; template filter `|safe` is applied to a json.dumps output, not to free-form HTML.
- **Horizon memory.** `hx-push-url="true"` keeps the URL in sync; reload preserves horizon. Default horizon lives in the handler, not the template.
- **Pure recompute cost.** `forecast(horizon_days=1825)` with 50 recurring rules × 60 months ≈ 3000 virtual occurrences — still cheap. If a benchmark shows this exceeds 100 ms, cache keyed on `max(audit_log.id)` (noted in `implementation_plan.md` risks). Not for this PR.
- **FX rate caching.** `fx.get_rate(..., latest=True)` fetches today's rate once and caches in `fx_rates`. On repeated requests the service must not re-fetch unless the cached rate is older than today in the display timezone. Flag for T-020 if that heuristic is missing.
- **Base currency aggregation precision.** All per-account series are in each account's own currency internally; the fortune series multiplies by the latest FX rate and rounds to minor units once at the end. Avoid accumulating rounding drift by rounding only at the aggregation step. Covered by T-025.
- **Deterministic promotion skew.** Promotion (manual) does not affect forecast until confirmed by the user — virtual occurrences already encode "if nothing changes". Document in the forecast page's muted header line to set expectations.
- **Plotly bundle size.** CDN loads ~3 MB uncompressed. First render budget acceptable for local-only (ADR-0002). T-053 may lazy-load Plotly only on `/forecast` and `/analytics` via `hx-on::load` — flag for polish phase.
- **The listener on `balance-stale`** means any transaction create/delete in another panel also re-triggers the forecast — right behaviour, but costly if a user is batch-editing. The 200 ms debounce built into HTMX by default is enough; `hx-trigger="forecast-stale from:body throttle:500ms, balance-stale from:body throttle:500ms"` smooths this out — recommended.

## Anti-template design-quality move

A **single hero chart with editorial restraint**, not a dashboard:

- The chart container occupies a wide `h-[420px]` strip above the fold. Plotly layout is overridden server-side with: no gridlines on x, hairline gridlines on y, no legend box (per-account lines labelled at their right end), no title (the H1 serves as title), and the hover is a thin crosshair with the base-currency amount in a serif figure. Color palette comes from `app.css` tokens — one oklch accent for fortune (stacked total), one muted ink per account line. Rejects the stock Plotly theme.
- Below the chart: a **two-column summary** — left is a bulleted list of per-account end-of-horizon figures with delta-from-today arrows; right is the fortune card in `text-4xl` serif with "today → +{{N}} days" above and the two end-points in `tabular-nums`. Grid-breaking: the two columns are intentionally unequal (`grid-cols-[1fr_320px]`).
- The FX note sits in muted type at the end of the subheader, with a 6px dot in `--accent` when the rate came from the live API and in `--warn` when from fallback cache. One depth cue, no banner.
- Horizon selector is a plain `<select>` with the two-tone focus ring from the shell — no fancy segmented control, deliberate restraint matching the editorial direction.

## Handoff notes

- T-031 / T-032 / T-034 / T-035 emit `balance-stale` and / or `forecast-stale` on their mutations; this router consumes both. No new coordination required.
- Any future router that invalidates forecast (e.g. a trend overlay) must emit `forecast-stale`. Document in T-030 HTMX event table before implementation.
- The `ForecastSeries.to_plotly_figure()` conversion lives in the **router module** (presentation concern) or a tiny `src/budget_planner/web/plot.py` helper — not in `services.forecast`. The service returns raw numeric arrays; the router transforms to Plotly JSON. Keeps services UI-free.
