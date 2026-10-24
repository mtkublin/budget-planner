# T-036 — Budget Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

Show the current month's budget state and let the user manage the three-tier budget: `default → recurring (per calendar month) → one-off (specific year+month)`. Resolution per ADR-0014 is `one_off ?? recurring ?? default`. Current-month view adds analytics: average monthly spend overall, average this year, delta vs previous month. No rollover.

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md).
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — `budgets.{list_defaults, list_recurring_overrides, list_one_off_overrides, upsert_default, upsert_recurring_override, upsert_one_off_override}`.
  - [`../phase-2/T-024-budget-service.md`](../phase-2/T-024-budget-service.md) — `budget.resolve_budget(conn, category_id, year, month)`, `budget.month_summary(conn, year, month) -> MonthSummary`.
- ADRs:
  - [`../../adr/0014-budget-flat-no-rollover-three-tier.md`](../../adr/0014-budget-flat-no-rollover-three-tier.md) — the model.
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — spend aggregated by direction=expense only.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md).
- Service calls:
  - `services.budget.month_summary(conn, year, month) -> MonthSummary` where each row carries `category`, `budgeted`, `spent`, `remaining`, `avg_overall`, `avg_this_year`, `delta_vs_prev_month`.
  - Repository upsert helpers listed above.

## Deliverables

- Router module path: `src/budget_planner/web/routers/budget.py`.
- Jinja templates:
  - `templates/budget/index.html` — current month view (full page): a table with per-category rows + a monthly header strip (total budgeted / total spent / remaining / overall delta).
  - `templates/budget/manage.html` — defaults + recurring + one-off override management (full page).
  - `templates/partials/budget/_summary_table.html` — the month table body (swapped on `budget-stale`).
  - `templates/partials/budget/_row.html` — one summary row per category (`<tr id="budget-{{ cat_id }}-{{ year }}-{{ month }}">`).
  - `templates/partials/budget/_defaults_table.html` — manage view: defaults table.
  - `templates/partials/budget/_defaults_row.html` — defaults row with inline editable `amount` input.
  - `templates/partials/budget/_recurring_grid.html` — 12-column grid, rows = categories, cells = per-month recurring override, swap on cell edit.
  - `templates/partials/budget/_one_off_table.html` — one-off override table.
  - `templates/partials/budget/_cell.html` — one editable amount cell used by both recurring + one-off editors.
- Tests: `tests/integration/web/test_budget.py`.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/budget` | query: `year`, `month` (default current, Europe/Warsaw) | full page `index.html` | `budget.month_summary(year, month)` | header listens: `hx-trigger="budget-stale from:body"`, `hx-get="/budget/table?year=…&month=…"`, `hx-target="#budget-table"`, `hx-swap="outerHTML"` |
| GET | `/budget/table` | query: `year`, `month` | fragment `_summary_table.html` | `budget.month_summary` | — |
| GET | `/budget/manage` | — | full page `manage.html` | `budgets.list_defaults`, `budgets.list_recurring_overrides`, `budgets.list_one_off_overrides` | — |
| POST | `/budget/defaults/{category_id}` | form: `amount` (decimal) | 200 fragment `_defaults_row.html` + OOB flash. 422 → `_defaults_row.html` with inline error | `budgets.upsert_default(category_id, minor)` | inline input: `hx-post="/budget/defaults/{{ cat.id }}"`, `hx-trigger="change delay:400ms"`, `hx-target="#default-{{ cat.id }}"`, `hx-swap="outerHTML"`. `HX-Trigger: budget-stale` |
| POST | `/budget/recurring/{category_id}/{month}` | form: `amount` (decimal; empty = clear) | 200 fragment `_cell.html` + OOB flash. 422 → `_cell.html` with inline error | `budgets.upsert_recurring_override(category_id, month, minor)` or `delete_recurring_override(cat, month)` when empty | `hx-post="/budget/recurring/{{ cat.id }}/{{ m }}"`, `hx-trigger="change delay:400ms"`, `hx-target="#rec-{{ cat.id }}-{{ m }}"`, `hx-swap="outerHTML"`. `HX-Trigger: budget-stale` |
| POST | `/budget/one-off/{category_id}/{year}/{month}` | form: `amount` (decimal; empty = clear) | 200 fragment `_cell.html` + OOB flash. 422 → `_cell.html` with inline error | `budgets.upsert_one_off_override(category_id, year, month, minor)` or delete when empty | `hx-post="/budget/one-off/{{ cat.id }}/{{ y }}/{{ m }}"`, `hx-trigger="change delay:400ms"`, `hx-target="#oneoff-{{ cat.id }}-{{ y }}-{{ m }}"`, `hx-swap="outerHTML"`. `HX-Trigger: budget-stale` |

## Template structure

`templates/budget/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Budget · {{ year }}-{{ "%02d"|format(month) }} · Budget Planner{% endblock %}
{% block main %}
  <header class="mb-10 flex items-end justify-between gap-6">
    <div>
      <h1 class="font-serif text-5xl leading-none">{{ month_name }} <span class="text-muted">{{ year }}</span></h1>
      <p class="text-muted mt-2">
        {{ summary.total_budgeted|money(base_ccy) }} budgeted ·
        {{ summary.total_spent|money(base_ccy) }} spent ·
        <span class="tabular-nums {% if summary.total_remaining < 0 %}text-destructive{% endif %}">
          {{ summary.total_remaining|money(base_ccy) }} remaining
        </span>
      </p>
    </div>
    <nav class="flex gap-2 text-sm">
      <a class="link-muted" href="/budget?year={{ prev.year }}&month={{ prev.month }}">← {{ prev_label }}</a>
      <a class="link-muted" href="/budget?year={{ next.year }}&month={{ next.month }}">{{ next_label }} →</a>
      <a class="link-accent" href="/budget/manage">Manage</a>
    </nav>
  </header>

  {% include "partials/budget/_summary_table.html" %}
{% endblock %}
```

`templates/partials/budget/_summary_table.html`:

```jinja
<table id="budget-table" class="w-full"
       hx-trigger="budget-stale from:body"
       hx-get="/budget/table?year={{ year }}&month={{ month }}"
       hx-swap="outerHTML">
  <caption class="sr-only">Budget vs spend for {{ month_name }} {{ year }}</caption>
  <thead>
    <tr>
      <th scope="col" class="text-left">Category</th>
      <th scope="col" class="text-right">Budgeted</th>
      <th scope="col" class="text-right">Spent</th>
      <th scope="col" class="text-right">Remaining</th>
      <th scope="col" class="text-right text-muted">Avg overall</th>
      <th scope="col" class="text-right text-muted">Avg {{ year }}</th>
      <th scope="col" class="text-right text-muted">Δ prev</th>
    </tr>
  </thead>
  <tbody class="divide-y divide-[color:var(--rule)]">
    {% for row in summary.rows %}
      {% include "partials/budget/_row.html" %}
    {% endfor %}
  </tbody>
</table>
```

`templates/partials/budget/_cell.html` (shared across recurring + one-off editors):

```jinja
<form id="{{ cell_id }}"
      class="inline"
      hx-post="{{ action }}"
      hx-trigger="change delay:400ms"
      hx-target="#{{ cell_id }}"
      hx-swap="outerHTML">
  <label class="sr-only" for="{{ cell_id }}-input">{{ aria_label }}</label>
  <input id="{{ cell_id }}-input"
         name="amount"
         type="text"
         inputmode="decimal"
         value="{{ value_display }}"
         placeholder="—"
         class="w-24 text-right tabular-nums bg-transparent border-0 border-b border-dotted focus-visible:border-solid"
         aria-describedby="{{ cell_id }}-help">
  {% if error %}<span id="{{ cell_id }}-help" role="alert" class="text-xs text-destructive">{{ error }}</span>{% endif %}
</form>
```

Shared partials: `_money`, `_flash` (OOB), `_form_errors`.

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| `budget-stale from:body` on `#budget-table` | `#budget-table` | `outerHTML` | Table re-renders with updated spent/remaining. | — |
| Default input `change` (manage) | `#default-{{ cat.id }}` | `outerHTML` | Row re-renders with new value in `tabular-nums`; OOB flash "saved"; `budget-stale`. | 422 → row re-renders with inline error, previous value preserved. |
| Recurring cell `change` (manage grid) | `#rec-{{ cat.id }}-{{ m }}` | `outerHTML` | Cell re-renders; `budget-stale`. Empty value clears the override. | 422 → cell with inline error. |
| One-off cell `change` (manage) | `#oneoff-{{ cat.id }}-{{ y }}-{{ m }}` | `outerHTML` | Cell re-renders; `budget-stale`. Empty value clears the override. | 422 → cell with inline error. |

`HX-Trigger` headers emitted:

- Any upsert: `{"budget-stale":true}` — the current-month table re-fetches itself whenever an override at any tier changes.

## Validation / acceptance

- `GET /budget` → `200`; renders a table with one row per category that has either a default, a recurring override for `month`, a one-off for `(year, month)`, or an expense transaction in `(year, month)`.
- Three-tier resolution: for category `X`, set default=100, recurring[Jan]=120, one-off[2026-01]=150. `GET /budget?year=2026&month=1` shows `budgeted = 150`. Remove one-off → shows 120. Remove recurring → shows 100.
- Spent for category `X` in month `M` = `SUM(amount_minor)` over non-deleted transactions in `(X, M)` with `direction=expense` (transits + adjustments excluded, per ADR-0008/-0009/-0011).
- `remaining = budgeted - spent`; negative displayed in `text-destructive` (semantic color token, not a plus/minus sign).
- `avg_overall` = mean monthly spend for `X` across all months with any txn; `avg_this_year` = mean monthly spend for `X` within `year`; `delta_vs_prev_month` = `spent(X, M) - spent(X, M-1)` (handles year wrap).
- `POST /budget/defaults/{id}` with `amount=50.00` → `200`; `budget_defaults.amount == 5000`; row returns with `tabular-nums` rendered value; `HX-Trigger: budget-stale` present.
- `POST /budget/recurring/{id}/{m}` with empty amount → `200`; the row in `budget_recurring_overrides` is deleted (soft-deleted? — in the budget overrides case, hard-deleted is acceptable because the row has no history value; service decides. Document in T-024.). The cell swap shows the fallback value (recurring if cleared → shows default) with a muted hint "inherits default".
- `POST /budget/one-off/{id}/{y}/{m}` with `amount=0` → `200`; stores `0` (an explicit zero is meaningful, differentiating from "no override"). Empty string = clear.
- A11y: table has `<caption class="sr-only">`; every input in the manage grid has an `aria-label` carrying `category · month`; `role="alert"` on inline errors.
- `GET /budget/manage` → `200`; three sections, each labelled `<h2>` with a short help paragraph explaining the tier.

## Risks & gotchas

- **Empty vs zero.** Empty input = clear the override. Zero = store `0`. The router parses `""` as `None` → delete; `"0"` → `0` minor units. Document in the manage view with a muted hint.
- **Decimal precision per currency.** Spent amounts come from transactions in the account's currency; **budget amounts are configured in base currency** (ADR-0014 is silent on this — flag). Resolution: v1 budgets are per category in base currency; spent is converted via `fx.convert(..., operation_date)` historical rate (ADR-0006). If T-024 does not already fold conversion in, add it (not a router concern).
- **Month navigation.** `prev` / `next` compute with year wrap; a tiny pure helper (`prev_month(y, m)`, `next_month(y, m)`) in the service. Router passes labels to the template.
- **Timezone.** "Current month" = today's month in `Europe/Warsaw` (ADR-0007). Compute `today = datetime.now(ZoneInfo(settings.display_timezone)).date()` in the router.
- **Analytics columns are read-only and muted** — they are context, not actions. Confirm they are not announced as interactive by screen readers (no `tabindex`).
- **Debounced inputs.** `change delay:400ms` prevents a request per keystroke; the user leaving the field also triggers `change`. Beware iOS keyboard — if `change` fires too late, consider `hx-trigger="change, blur delay:200ms"`.
- **Cell error leaves stale value.** On 422 the response fragment carries the **last valid value** from the DB plus the invalid user input echoed into the input field via `value=` — the user keeps context without the DB being updated. Covered by a test.
- **N+1 risk in month_summary.** Service must compute all rows in one or two aggregated SQL statements, not N queries. Flag for T-024.
- **Budget page listens for `budget-stale`** emitted by this router; it does **not** listen for `balance-stale` from T-031 because transactions do not immediately invalidate budget cells beyond "spent" totals — add a `balance-stale → budget-stale` chain? No. Add a dedicated listener on `#budget-table` for `balance-stale from:body` as well, so a new transaction updates spent immediately. (Documented in HTMX interactions.)

## Anti-template design-quality move

The current-month view is a **ledger first**, not a KPI grid:

- The header is editorial: a serif month name at `text-5xl` with the year set as a muted span — reads like a magazine section opener. The totals strip is a single sentence under it, not three stacked tiles.
- The table uses **hairline rules** between rows, `tabular-nums` across every numeric column, muted labels on the three analytics columns, and no color on the "spent" column — only `remaining` picks up an oklch destructive token when negative. Hierarchy via **weight contrast** (`font-semibold` on category name, numeric columns in regular weight).
- Negative remaining is a **two-step signal**: color token for the number + a tiny inline arrow glyph; motion is a 150ms color transition on recompute, so a swap feels like a reveal rather than a flash.
- The manage view is a **12-column grid** for recurring overrides: columns = Jan..Dec, rows = categories, cells = inline-editable dotted-underline inputs. Looks like a working spreadsheet, not a config page. The dotted underline is CSS tokens, not a Tailwind cliché; focus-visible promotes it to solid underline in `--accent`.
- No save buttons — change events save on blur/debounce; a tiny OOB toast "Saved 10:42" confirms. Reinforces the "it's a document you're editing", not "a form you're filling in".

## Handoff notes

- T-037 (forecast) does **not** depend on budget state; no event flows from here to forecast.
- T-038 (analytics) reads from the same transaction log but through its own aggregations; no event flows.
- T-039 (home dashboard) includes `partials/budget/_summary_table.html` for the current month card and listens on `budget-stale` the same way.
- `budget.month_summary` must include `balance-stale from:body` as another trigger for self-refresh (handled by adding a second `hx-trigger` on `#budget-table` — the template shows one; the final implementation adds `balance-stale from:body` alongside `budget-stale`).
