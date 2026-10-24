# T-039 — Navigation + Home Dashboard

> Phase 3 — Web Layer. Status: pending.

## Purpose

Stitch Phase 3 together. Finalize the left-nav shell in `base.html` so every router landed in T-031..T-038 is reachable, and ship the `GET /` home dashboard — the only route the user ever lands on by default. Dashboard composes three panels assembled from partials already produced by earlier Phase 3 tasks: current-month budget summary, total fortune (sum of per-account derived balances converted to `base_currency`), and the next 7 days of planned transactions. No new business logic — this task only orchestrates services and reuses partials.

## Inputs / prerequisites

- Upstream tasks (all must be green before this starts):
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md) — base template + Jinja env + partials dir + `get_db`/`get_settings` deps.
  - [`T-031-transactions-router.md`](T-031-transactions-router.md) — nav link target.
  - [`T-032-accounts-router.md`](T-032-accounts-router.md) — provides `partials/accounts/_balance_cell.html` reused on the fortune panel.
  - [`T-033-categories-router.md`](T-033-categories-router.md) — nav link target.
  - [`T-034-planned-router.md`](T-034-planned-router.md) — provides `partials/planned/_row.html` reused on the "Next 7 days" panel.
  - [`T-035-recurring-router.md`](T-035-recurring-router.md) — nav link target.
  - [`T-036-budget-router.md`](T-036-budget-router.md) — provides `partials/budget/_summary_row.html` reused on the budget panel.
  - [`T-037-forecast-router.md`](T-037-forecast-router.md) — nav link target.
  - [`T-038-analytics-router.md`](T-038-analytics-router.md) — nav link target.
- ADRs:
  - [`../../adr/0002-web-stack-fastapi-htmx-jinja.md`](../../adr/0002-web-stack-fastapi-htmx-jinja.md) — stack baseline.
  - [`../../adr/0005-single-user-no-auth-user-id-scaffold.md`](../../adr/0005-single-user-no-auth-user-id-scaffold.md) — `user_id = 1`; no login screen; `/` is public on `127.0.0.1`.
  - [`../../adr/0006-multi-currency-model.md`](../../adr/0006-multi-currency-model.md) — fortune aggregate converts to `base_currency` via FX.
  - [`../../adr/0007-timezone-handling.md`](../../adr/0007-timezone-handling.md) — "today" and the 7-day window resolve in `Europe/Warsaw`.
  - [`../../adr/0014-budget-flat-no-rollover-three-tier.md`](../../adr/0014-budget-flat-no-rollover-three-tier.md) — current-month budget semantics.
  - [`../../adr/0015-forecast-deterministic-live-htmx.md`](../../adr/0015-forecast-deterministic-live-htmx.md) — balance panel listens for `balance-stale`.
  - [`../../adr/0021-functional-style-no-oop.md`](../../adr/0021-functional-style-no-oop.md) — router module is plain functions.
- Service functions this router calls:
  - `services.budget.month_summary(conn, year, month)`
  - `services.balance.derive_balance(conn, account_id, as_of_date=None)`
  - `services.fx.convert(conn, amount_minor, date, from_ccy, to_ccy)`
  - `services.planned.list_planned(conn, PlannedFilter(date_from=today, date_to=today + 7d))`
  - `repositories.accounts.list_filtered(conn, AccountFilter(active=True))`
  - `repositories.categories.list_filtered(conn)` (for budget panel labels)

## Deliverables

- Router module path: `src/budget_planner/web/routers/home.py`.
- Jinja templates:
  - `src/budget_planner/web/templates/home/index.html` — full page extending `base.html`; three panels + CTA strip.
  - `src/budget_planner/web/templates/partials/home/_fortune_panel.html` — totals + per-account cards; HTMX-swappable on `balance-stale`.
  - `src/budget_planner/web/templates/partials/home/_budget_panel.html` — month header + top-5 categories (budgeted / spent / remaining); HTMX-swappable on `budget-stale`.
  - `src/budget_planner/web/templates/partials/home/_next7_panel.html` — compact planned-txn list for the next 7 days; HTMX-swappable on `forecast-stale`.
  - `src/budget_planner/web/templates/partials/home/_empty_state.html` — first-run message with CTAs to add an account / category / transaction.
- Base template changes (owned by T-030 but finalized here):
  - `src/budget_planner/web/templates/base.html` — populate `block nav` with the final `<aside>` sidebar linking the eight routers + home.
  - `src/budget_planner/web/templates/partials/_nav.html` — new partial consumed by `base.html` so the nav can be re-rendered independently in tests.
- Static assets:
  - `src/budget_planner/web/static/img/logo.svg` — monochrome mark (keeps nav intentional, see Anti-template note). Inline SVG preferred over external file; path only if we need favicon reuse.
- Tests: `tests/integration/web/test_home.py` using FastAPI `TestClient` + BeautifulSoup.

## Endpoints

| Method | Path | Request shape | Response | Service call(s) | HTMX attrs |
|--------|------|---------------|----------|-----------------|-----------|
| GET | `/` | — | full page `home/index.html` | `budget.month_summary(conn, Y, M)`, `accounts.list_filtered(...)` → `balance.derive_balance(...)` ×N → `fx.convert(...)` ×N, `planned.list_planned(conn, filter)` | — |
| GET | `/panels/fortune` | — | HTMX fragment (`_fortune_panel.html`) | same as above (fortune slice) | triggered by `hx-trigger="balance-stale from:body"` on the fortune panel, `hx-get="/panels/fortune"`, `hx-swap="outerHTML"` |
| GET | `/panels/budget` | — | HTMX fragment (`_budget_panel.html`) | `budget.month_summary(conn, Y, M)` | `hx-trigger="budget-stale from:body"`, `hx-get="/panels/budget"`, `hx-swap="outerHTML"` |
| GET | `/panels/next7` | — | HTMX fragment (`_next7_panel.html`) | `planned.list_planned(conn, PlannedFilter(date_from=today, date_to=today+7d))` | `hx-trigger="forecast-stale from:body"`, `hx-get="/panels/next7"`, `hx-swap="outerHTML"` |

All three panel endpoints return the same partial that is embedded in the full page, so the initial `/` request is a single query bundle, not three.

## Template structure

```jinja
{# templates/home/index.html #}
{% extends "base.html" %}

{% block title %}Dashboard · Budget Planner{% endblock %}

{% block main %}
  <section class="dashboard" aria-labelledby="dashboard-heading">
    <header class="dashboard__header">
      <h1 id="dashboard-heading">{{ today | format_date }}</h1>
      <p class="dashboard__subtitle">{{ month_label }} · {{ display_timezone }}</p>
    </header>

    {% if show_empty_state %}
      {% include "partials/home/_empty_state.html" %}
    {% else %}
      <div class="dashboard__grid">
        {% include "partials/home/_fortune_panel.html" %}
        {% include "partials/home/_budget_panel.html" %}
        {% include "partials/home/_next7_panel.html" %}
      </div>
    {% endif %}
  </section>
{% endblock %}
```

```jinja
{# templates/partials/home/_fortune_panel.html #}
<section id="panel-fortune"
         class="panel panel--fortune"
         aria-labelledby="panel-fortune-heading"
         hx-get="/panels/fortune"
         hx-trigger="balance-stale from:body"
         hx-swap="outerHTML">
  <header class="panel__header">
    <h2 id="panel-fortune-heading" class="panel__title">Fortune</h2>
    <p class="panel__eyebrow">as of {{ today | format_date }}</p>
  </header>

  <p class="panel__big-number"
     aria-live="polite">{{ fortune_total | format_money(base_currency) }}</p>

  <ul class="panel__list" role="list">
    {% for account in accounts %}
      <li class="account-card">
        <span class="account-card__name">{{ account.name }}</span>
        <span class="account-card__currency">{{ account.currency }}</span>
        <span class="account-card__balance">
          {{ account.balance_native | format_money(account.currency) }}
        </span>
        {% if account.currency != base_currency %}
          <span class="account-card__base" title="Converted at {{ fx_rates[account.currency] }}">
            ≈ {{ account.balance_base | format_money(base_currency) }}
          </span>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
</section>
```

```jinja
{# templates/partials/home/_budget_panel.html #}
<section id="panel-budget"
         class="panel panel--budget"
         aria-labelledby="panel-budget-heading"
         hx-get="/panels/budget"
         hx-trigger="budget-stale from:body"
         hx-swap="outerHTML">
  <header class="panel__header">
    <h2 id="panel-budget-heading" class="panel__title">This month</h2>
    <p class="panel__eyebrow">{{ month_label }}</p>
    <a class="panel__cta" href="/budget">Open budget →</a>
  </header>

  <dl class="panel__stat-row">
    <div><dt>Spent</dt><dd>{{ summary.total_spent | format_money(base_currency) }}</dd></div>
    <div><dt>Budgeted</dt><dd>{{ summary.total_budgeted | format_money(base_currency) }}</dd></div>
    <div><dt>Remaining</dt>
         <dd class="{{ 'is-negative' if summary.total_remaining < 0 else '' }}">
           {{ summary.total_remaining | format_money(base_currency) }}
         </dd></div>
  </dl>

  <ul class="panel__list" role="list">
    {% for row in top_categories %}
      {% include "partials/budget/_summary_row.html" with context %}
    {% endfor %}
  </ul>
</section>
```

```jinja
{# templates/partials/home/_next7_panel.html #}
<section id="panel-next7"
         class="panel panel--next7"
         aria-labelledby="panel-next7-heading"
         hx-get="/panels/next7"
         hx-trigger="forecast-stale from:body"
         hx-swap="outerHTML">
  <header class="panel__header">
    <h2 id="panel-next7-heading" class="panel__title">Next 7 days</h2>
    <a class="panel__cta" href="/planned">Open planned →</a>
  </header>

  {% if planned %}
    <ol class="panel__timeline" role="list">
      {% for item in planned %}
        {% include "partials/planned/_row.html" with context %}
      {% endfor %}
    </ol>
  {% else %}
    <p class="panel__empty">Nothing scheduled.</p>
  {% endif %}
</section>
```

```jinja
{# templates/partials/_nav.html #}
<aside class="sidebar" aria-label="Primary">
  <a class="sidebar__brand" href="/">
    {% include "partials/_logo.svg" %}
    <span>Budget Planner</span>
  </a>

  <nav class="sidebar__nav" aria-label="Sections">
    <a href="/"            class="sidebar__link {{ 'is-active' if request.url.path == '/' }}">Dashboard</a>
    <a href="/transactions" class="sidebar__link {{ 'is-active' if request.url.path.startswith('/transactions') }}">Transactions</a>
    <a href="/accounts"    class="sidebar__link {{ 'is-active' if request.url.path.startswith('/accounts') }}">Accounts</a>
    <a href="/categories"  class="sidebar__link {{ 'is-active' if request.url.path.startswith('/categories') }}">Categories</a>
    <a href="/planned"     class="sidebar__link {{ 'is-active' if request.url.path.startswith('/planned') }}">Planned</a>
    <a href="/recurring"   class="sidebar__link {{ 'is-active' if request.url.path.startswith('/recurring') }}">Recurring</a>
    <a href="/budget"      class="sidebar__link {{ 'is-active' if request.url.path.startswith('/budget') }}">Budget</a>
    <a href="/forecast"    class="sidebar__link {{ 'is-active' if request.url.path.startswith('/forecast') }}">Forecast</a>
    <a href="/analytics"   class="sidebar__link {{ 'is-active' if request.url.path.startswith('/analytics') }}">Analytics</a>
  </nav>

  <footer class="sidebar__footer">
    <span class="sidebar__meta">{{ base_currency }} · {{ display_timezone }}</span>
  </footer>
</aside>
```

Router sketch:

```python
# src/budget_planner/web/routers/home.py
from __future__ import annotations

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from budget_planner.config import Settings
from budget_planner.repositories import accounts, categories
from budget_planner.services import balance, budget, fx, planned
from budget_planner.web.deps import get_db, get_settings, today_local
from budget_planner.web.templating import render

router = APIRouter(tags=["home"])


def _fortune(conn, settings: Settings, as_of: date) -> dict:
    rows = []
    total_base = 0
    rates: dict[str, str] = {}
    for a in accounts.list_filtered(conn):
        bal = balance.derive_balance(conn, a.id, as_of_date=as_of)
        bal_base = fx.convert(conn, bal, as_of, a.currency, settings.base_currency)
        total_base += bal_base
        rates[a.currency] = str(fx.get_rate(conn, as_of, a.currency, settings.base_currency))
        rows.append({"id": a.id, "name": a.name, "currency": a.currency,
                     "balance_native": bal, "balance_base": bal_base})
    return {"accounts": rows, "fortune_total": total_base,
            "fx_rates": rates, "base_currency": settings.base_currency}


def _budget_slice(conn, year: int, month: int, limit: int = 5) -> dict:
    summary = budget.month_summary(conn, year, month)
    top = sorted(summary.rows, key=lambda r: r.spent, reverse=True)[:limit]
    return {"summary": summary, "top_categories": top,
            "month_label": f"{year}-{month:02d}"}


def _next7(conn, as_of: date) -> list:
    return planned.list_planned(conn, date_from=as_of, date_to=as_of + timedelta(days=7))


@router.get("/", response_class=HTMLResponse)
def home(request: Request, conn=Depends(get_db), settings: Settings = Depends(get_settings),
         today: date = Depends(today_local)) -> HTMLResponse:
    show_empty_state = not accounts.list_filtered(conn)
    ctx = {
        "request": request,
        "today": today,
        "display_timezone": settings.display_timezone,
        "show_empty_state": show_empty_state,
    }
    if not show_empty_state:
        ctx.update(_fortune(conn, settings, today))
        ctx.update(_budget_slice(conn, today.year, today.month))
        ctx["planned"] = _next7(conn, today)
        ctx["month_label"] = ctx["month_label"]
    return render("home/index.html", ctx)


@router.get("/panels/fortune", response_class=HTMLResponse)
def fortune_panel(request: Request, conn=Depends(get_db), settings: Settings = Depends(get_settings),
                  today: date = Depends(today_local)) -> HTMLResponse:
    ctx = {"request": request, "today": today, **_fortune(conn, settings, today)}
    return render("partials/home/_fortune_panel.html", ctx)


@router.get("/panels/budget", response_class=HTMLResponse)
def budget_panel(request: Request, conn=Depends(get_db),
                 today: date = Depends(today_local)) -> HTMLResponse:
    ctx = {"request": request, **_budget_slice(conn, today.year, today.month)}
    return render("partials/home/_budget_panel.html", ctx)


@router.get("/panels/next7", response_class=HTMLResponse)
def next7_panel(request: Request, conn=Depends(get_db),
                today: date = Depends(today_local)) -> HTMLResponse:
    ctx = {"request": request, "planned": _next7(conn, today)}
    return render("partials/home/_next7_panel.html", ctx)
```

`today_local` is a dependency added here that returns `datetime.now(ZoneInfo(settings.display_timezone)).date()` so the "today" boundary respects ADR-0007 without routers calling `datetime.now` themselves.

## HTMX interactions

| Trigger | Source | Target | Swap | UX |
|---------|--------|--------|------|-----|
| `balance-stale` on `body` | emitted by txns / accounts / reconciliation routers | `#panel-fortune` | `outerHTML` | fortune panel re-fetches silently; `aria-live="polite"` on the big-number node announces the new total |
| `budget-stale` on `body` | emitted by budget router | `#panel-budget` | `outerHTML` | budget panel re-fetches; top-5 ordering may change |
| `forecast-stale` on `body` | emitted by txns / planned / recurring / accounts routers | `#panel-next7` | `outerHTML` | 7-day list re-fetches |

Panels do not block each other: HTMX requests are independent. Each panel owns its own HTMX attributes on its outermost `<section>` and the server returns the same `<section>` element with the same `id`, so swap identity is preserved. On error the panel renders a small `partials/_panel_error.html` fragment with a retry link.

Keyboard focus handling: if the user has focus inside a panel when it swaps, HTMX replaces the element and focus moves to `<body>`. For the fortune and budget panels this is acceptable (no interactive controls inside). The planned-txn list rows do include links; use `hx-focus="closest a"` on the outer `<section>` to restore focus to the first row anchor after a swap.

## Validation / acceptance

Test file: `tests/integration/web/test_home.py`. Required assertions, all via `TestClient` + BeautifulSoup selectors on `data-testid` attributes added to each panel:

- `GET /` returns 200 with `<main>` containing `#panel-fortune`, `#panel-budget`, `#panel-next7`.
- With no accounts seeded, response contains the empty-state block and the three panels are absent.
- With one account + a few transactions seeded, `[data-testid="fortune-total"]` text parses to the expected minor-unit total converted via `services.fx.convert` with the stubbed FX rate (seed `fx_rates` row deterministically).
- Budget panel renders exactly the top 5 categories by spend; a sixth seeded category with a smaller spend does not appear.
- `[data-testid="next7"] li` count equals the number of planned occurrences (persisted + virtual) with `date_from <= operation_date <= date_from + 7d`.
- `GET /panels/fortune`, `/panels/budget`, `/panels/next7` return the same fragment markup embedded on `/` (identity test: inner HTML of panel on `/` equals response body of its panel route).
- Nav rendering: `GET /` response contains all 9 nav anchors with their expected `href`s; `.is-active` class is on the dashboard link.
- A11y basics: every `<section class="panel">` has an `aria-labelledby` whose target `h2` exists in-document; `.is-negative` on remaining-amount `<dd>` when remaining < 0.
- Response includes `<main>` landmark exactly once, and no empty `aria-labelledby` references.

Phase gate from `docs/implementation_plan.md`: `GET /` lands on a dashboard showing current-month budget state + total fortune + next 7 days. This task is where that gate closes.

## Risks & gotchas

- **FX round-trips on fortune panel**: `derive_balance` returns native-currency minor units; converting each account separately produces N FX lookups. All should hit the local `fx_rates` cache on a warm DB — but on first-run of a new currency pair the request will fan out to the external API during server startup / page load. Mitigate by prefetching rates for all distinct account currencies once at the start of `home()` and reusing.
- **Base-currency conversion drift**: use the same `as_of` date (today in `Europe/Warsaw`) for every account to keep the fortune total internally consistent. Do not pass `None` to `derive_balance` in a loop where "now" could tick between calls.
- **Date boundary**: "today" and "next 7 days" must resolve in `Europe/Warsaw`, not UTC. The `today_local` dependency covers this. Do not use `date.today()` directly anywhere in this router.
- **Panel swap identity**: the server must emit the outer `<section id="panel-...">` wrapper in both the full-page include and the `/panels/*` fragment. If the wrapper is only on the full page, HTMX swap duplicates the element.
- **Empty state**: on first run (no accounts), skip the service calls entirely — do not attempt to render fortune with zero accounts (division-by-zero in top-5 budget ordering is also avoided this way).
- **Nav active state**: computed on the server by matching `request.url.path`. A fragment response from `/panels/*` should not re-render the nav; keep `_nav.html` outside the panel partials.
- **HTMX `from:body` scope**: panel triggers listen on `body` so cross-router emissions (e.g. a new txn creates balance-stale from `/transactions`) propagate. If a future partial uses `hx-swap="outerHTML" hx-select` without matching the `from:body` scope the subscription dies silently — document this in the base template as a convention.
- **N+1 on budget panel**: `budget.month_summary` already aggregates in SQL (per T-024 plan). Do not iterate categories calling the service in a loop.

## Anti-template design move

Dashboard is explicitly editorial, not a stock card grid:

- **Hierarchy by scale contrast**: fortune total renders at the largest display size (`clamp(2.5rem, 1rem + 4vw, 5rem)`), category rows and planned entries at the small end. Two eyebrows (`today` date and month label) provide a quiet second register.
- **Rhythm not uniform padding**: the fortune panel has generous vertical rhythm around the big number; the next-7 timeline is dense; the budget panel sits between. Panels use a 12-column CSS grid where fortune spans 7, budget spans 5, next-7 spans 12 on the row below.
- **Depth via overlap**: fortune panel's big number vertically overlaps the top of its account list with a `translateY(-0.5em)` nudge; subtle but intentional.
- **Semantic color**: `.is-negative` on remaining uses a desaturated red from the token palette; the big number is neutral unless the fortune is below a configured warning floor (deferred until T-053).

See `rules/web/design-quality.md` and plan [`T-053-visual-polish.md`](../phase-5/T-053-visual-polish.md) for the token palette and type scale this surface will adopt in Phase 5.

## Handoff notes

- Phase 4 e2e smoke test `test_add_txn_see_balance_update` lands on `/`, creates a transaction via `/transactions`, and asserts the fortune panel updates — relies on `balance-stale` from `/transactions` reaching `#panel-fortune`.
- Phase 5 polish (`T-053`) owns the final typography, palette, and spacing tokens applied here; this task ships functional structure with Tailwind utility defaults.
- Phase 5 a11y (`T-052`) will add a visible skip link and audit the dashboard; this task already supplies the required landmarks and `aria-labelledby` targets so the audit passes with zero A violations on `/`.
- Any new top-level route added after this phase must also appear in `partials/_nav.html` and, if it mutates state in a way the dashboard cares about, must emit one of `balance-stale` / `budget-stale` / `forecast-stale`.
