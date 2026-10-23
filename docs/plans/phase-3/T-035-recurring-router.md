# T-035 — Recurring Rules Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

Manage the recurring rules that drive virtual planned occurrences: list rules, create, edit, deactivate (soft-stop), and manage per-occurrence overrides (skip / override amount / description / date). Overrides are the sparse exception table defined by ADR-0013; the UI shows an **upcoming occurrences preview** next to each rule with per-row toggle buttons for skip / override.

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md).
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — `recurring.{list, find_by_id, create, update, deactivate, soft_delete}`, override CRUD helpers.
  - [`../phase-1/T-014-domain-types.md`](../phase-1/T-014-domain-types.md) — `Cadence` enum, `NewRecurringRule`, `PatchRecurringRule`, `RecurringOverride`.
  - [`../phase-2/T-022-recurring-occurrence-generator.md`](../phase-2/T-022-recurring-occurrence-generator.md) — `generate_occurrences(rule, start, end)` + `apply_overrides(occurrences, overrides)`.
- ADRs:
  - [`../../adr/0013-recurring-virtual-occurrences-and-overrides.md`](../../adr/0013-recurring-virtual-occurrences-and-overrides.md) — rules are the source of truth; occurrences virtual; sparse override table.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md).
  - [`../../adr/0012-planned-manual-promotion.md`](../../adr/0012-planned-manual-promotion.md) — overrides never auto-promote; promotion still manual.
- Service calls:
  - `services.recurring.list_rules(conn, include_inactive=False) -> list[RuleView]`.
  - `services.recurring.preview_occurrences(conn, rule_id, horizon_months=12) -> list[OccurrenceView]` (applies overrides).
  - `repositories.recurring.{create, update, deactivate, soft_delete}`.
  - `repositories.recurring_overrides.{upsert, delete_by_rule_and_date}`.

## Deliverables

- Router module path: `src/budget_planner/web/routers/recurring.py`.
- Jinja templates:
  - `templates/recurring/index.html` — full page: list of rule cards, each with a preview strip.
  - `templates/partials/recurring/_card.html` — rule card (`<article id="rule-{{ r.id }}">`), swapped on edit / deactivate.
  - `templates/partials/recurring/_form.html` — create / edit rule form (cadence, dates, amount, description, category, account, dest_account, day_of_month, month_of_year, active).
  - `templates/partials/recurring/_preview.html` — the preview block rendered inside a card (`<ol id="rule-{{ r.id }}-preview">` with each occurrence as `<li id="occ-{{ r.id }}-{{ YYYYMMDD }}">`).
  - `templates/partials/recurring/_occurrence_row.html` — single occurrence row with override toggle buttons.
  - `templates/partials/recurring/_override_form.html` — small inline form on an occurrence row to set amount / description / date override.
- Tests: `tests/integration/web/test_recurring.py`.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/recurring` | query: `include_inactive=false` | full page | `recurring.list_rules`, `recurring.preview_occurrences` per rule | — |
| GET | `/recurring/new` | — | fragment `_form.html` (create) | `categories.list`, `accounts.list` | `hx-get="/recurring/new"`, `hx-target="#rule-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/recurring` | form: `cadence`, `start_date`, `end_date?`, `category_id`, `account_id`, `dest_account_id?`, `default_amount`, `default_description`, `day_of_month?`, `month_of_year?`, `active=true` | 200 fragment `_card.html` + OOB flash. 422 → `_form.html` with errors | `recurring.create(NewRecurringRule)` | `hx-post="/recurring"`, `hx-target="#rules-grid"`, `hx-swap="beforeend"`. Header: `HX-Trigger: forecast-stale` |
| GET | `/recurring/{id}/edit` | path | fragment `_form.html` (edit) | `recurring.find_by_id` | `hx-get="/recurring/{id}/edit"`, `hx-target="#rule-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/recurring/{id}` | form | 200 fragment `_card.html` (same id, preview re-generated) + OOB flash. 422 → `_form.html` with errors | `recurring.update(id, PatchRecurringRule)` | `hx-post="/recurring/{id}"`, `hx-target="#rule-{{id}}"`, `hx-swap="outerHTML"`. `HX-Trigger: forecast-stale` |
| POST | `/recurring/{id}/deactivate` | path | 200 fragment `_card.html` (same id; shows "inactive" chip; preview emptied) + OOB flash | `recurring.deactivate(id)` | `hx-post="/recurring/{id}/deactivate"`, `hx-target="#rule-{{id}}"`, `hx-swap="outerHTML"`, `hx-confirm="Deactivate this rule? No future virtual occurrences."`. `HX-Trigger: forecast-stale` |
| POST | `/recurring/{rule_id}/overrides` | form: `occurrence_date` (YYYY-MM-DD), `state=skipped\|overridden`, `amount_override?`, `description_override?`, `date_override?` | 200 fragment `_occurrence_row.html` (same `id`) + OOB flash | `recurring_overrides.upsert({rule_id, occurrence_date, state, ...})` | `hx-post="/recurring/{rule_id}/overrides"`, `hx-target="#occ-{{rule_id}}-{{YYYYMMDD}}"`, `hx-swap="outerHTML"`. `HX-Trigger: forecast-stale` |
| POST | `/recurring/{rule_id}/overrides/{occurrence_date}/delete` | path (`YYYY-MM-DD`) | 200 fragment `_occurrence_row.html` (same id; override cleared) + OOB flash | `recurring_overrides.delete_by_rule_and_date(rule_id, date)` | `hx-post="/recurring/{rule_id}/overrides/{YYYY-MM-DD}/delete"`, `hx-target="#occ-{{rule_id}}-{{YYYYMMDD}}"`, `hx-swap="outerHTML"`. `HX-Trigger: forecast-stale` |

## Template structure

`templates/recurring/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Recurring · Budget Planner{% endblock %}
{% block main %}
  <header class="mb-10 flex items-end justify-between gap-6">
    <div>
      <h1 class="font-serif text-5xl leading-none">Recurring rules</h1>
      <p class="text-muted mt-2">{{ rules|length }} active rules</p>
    </div>
    <button hx-get="/recurring/new" hx-target="#rule-form-slot" hx-swap="innerHTML" class="btn-accent">
      + New rule
    </button>
  </header>

  <label class="text-sm">
    <input type="checkbox" name="include_inactive"
           hx-get="/recurring"
           hx-trigger="change"
           hx-target="body" hx-swap="outerHTML"
           hx-push-url="true">
    Show inactive
  </label>

  <div id="rule-form-slot" class="my-6"></div>

  <section id="rules-grid" class="grid gap-6 grid-cols-1 lg:grid-cols-2">
    {% for r in rules %}
      {% include "partials/recurring/_card.html" %}
    {% endfor %}
  </section>
{% endblock %}
```

`templates/partials/recurring/_card.html`:

```jinja
<article id="rule-{{ r.id }}" class="card" aria-labelledby="rule-{{ r.id }}-name">
  <header class="flex items-baseline justify-between gap-3">
    <h2 id="rule-{{ r.id }}-name" class="font-serif text-2xl">{{ r.default_description }}</h2>
    <span class="chip-muted">{{ r.cadence }}</span>
  </header>
  <p class="text-sm text-muted">
    {{ r.category.name }} · {{ r.account.name }}
    {% if r.dest_account %} → {{ r.dest_account.name }}{% endif %}
    · default {{ r.default_amount|money(r.account.currency) }}
    {% if not r.active %}<span class="chip-warn ml-2">inactive</span>{% endif %}
  </p>

  <section class="mt-5">
    <h3 class="text-xs uppercase tracking-wider text-muted mb-2">Next 12 months</h3>
    <ol id="rule-{{ r.id }}-preview" class="divide-y divide-[color:var(--rule)]">
      {% for occ in r.preview %}
        {% include "partials/recurring/_occurrence_row.html" %}
      {% endfor %}
    </ol>
  </section>

  <footer class="mt-6 flex gap-2 text-sm">
    <button hx-get="/recurring/{{ r.id }}/edit"
            hx-target="#rule-form-slot" hx-swap="innerHTML">Edit</button>
    {% if r.active %}
      <button class="text-destructive ml-auto"
              hx-post="/recurring/{{ r.id }}/deactivate"
              hx-target="#rule-{{ r.id }}" hx-swap="outerHTML"
              hx-confirm="Deactivate this rule? No future virtual occurrences.">
        Deactivate
      </button>
    {% endif %}
  </footer>
</article>
```

`templates/partials/recurring/_occurrence_row.html`:

```jinja
<li id="occ-{{ occ.rule_id }}-{{ occ.occurrence_date|date_fmt('%Y%m%d') }}"
    class="py-2 flex items-center justify-between gap-3 text-sm">
  <div>
    <span class="tabular-nums">{{ occ.occurrence_date|date_fmt }}</span>
    {% if occ.override_state == 'skipped' %}
      <span class="chip-muted ml-2">skipped</span>
    {% elif occ.override_state == 'overridden' %}
      <span class="chip-muted ml-2">overridden</span>
    {% endif %}
  </div>
  <div class="tabular-nums">{{ occ.amount|money(occ.currency) }}</div>
  <div class="space-x-2">
    {% if occ.override_state %}
      <button hx-post="/recurring/{{ occ.rule_id }}/overrides/{{ occ.occurrence_date|date_fmt }}/delete"
              hx-target="#occ-{{ occ.rule_id }}-{{ occ.occurrence_date|date_fmt('%Y%m%d') }}"
              hx-swap="outerHTML">Clear</button>
    {% else %}
      <button hx-post="/recurring/{{ occ.rule_id }}/overrides"
              hx-vals='{"occurrence_date":"{{ occ.occurrence_date|date_fmt }}","state":"skipped"}'
              hx-target="#occ-{{ occ.rule_id }}-{{ occ.occurrence_date|date_fmt('%Y%m%d') }}"
              hx-swap="outerHTML">Skip</button>
      <button hx-get="/recurring/{{ occ.rule_id }}/overrides/{{ occ.occurrence_date|date_fmt }}/edit"
              hx-target="#occ-{{ occ.rule_id }}-{{ occ.occurrence_date|date_fmt('%Y%m%d') }}"
              hx-swap="outerHTML">Override</button>
    {% endif %}
  </div>
</li>
```

(The small `Override` inline form is rendered by returning `_override_form.html` as the row body on a GET; the submit `POST`s to `/recurring/{rule_id}/overrides` and the response is again `_occurrence_row.html` — in-place reversible UX. The GET for the override form is optional and is a nice-to-have; if omitted, keep the plain `Skip` + a modal `Override` instead.)

Shared partials: `_money`, `_direction_badge` (direction shown via rule's category), `_flash`, `_form_errors`.

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| `+ New rule` | `#rule-form-slot` | `innerHTML` | Form inserted. | — |
| Create submit | `#rules-grid` | `beforeend` | Card appended with preview rendered; `HX-Trigger: forecast-stale`. | 422 → `_form.html` in slot. |
| Edit button | `#rule-form-slot` | `innerHTML` | Form inserted populated. | — |
| Update submit | `#rule-{{id}}` | `outerHTML` | Card swapped; preview re-generated server-side; `HX-Trigger: forecast-stale`. | 422 → `_form.html` in slot. |
| Deactivate | `#rule-{{id}}` | `outerHTML` | Card swapped (preview emptied / `inactive` chip); `HX-Trigger: forecast-stale`. | 500 → OOB flash. |
| Skip (occurrence) | `#occ-{{rule_id}}-{{YYYYMMDD}}` | `outerHTML` | Row re-renders with `skipped` chip; `HX-Trigger: forecast-stale`. | 500 → OOB flash. |
| Override submit | `#occ-{{rule_id}}-{{YYYYMMDD}}` | `outerHTML` | Row re-renders with `overridden` chip and new amount; `HX-Trigger: forecast-stale`. | 422 → `_override_form.html` with errors. |
| Clear override | `#occ-{{rule_id}}-{{YYYYMMDD}}` | `outerHTML` | Row re-renders without chip; `HX-Trigger: forecast-stale`. | 500 → OOB flash. |

`HX-Trigger` headers emitted:

- All mutations here: `{"forecast-stale":true}`. No `balance-stale` — nothing in `transactions` changes until the user manually promotes.

## Validation / acceptance

- `GET /recurring` → `200`; DOM contains a card per rule; each card has `<ol id="rule-<n>-preview">` with 12 months of occurrences (default horizon).
- A `monthly` rule starting `2026-01-15` with no end date yields 12 occurrences in the preview with dates `2026-01-15, 2026-02-15, …`; `yearly` yields one in the horizon.
- `POST /recurring` with `cadence=weekly` → `422` ("Unsupported cadence; use monthly/quarterly/yearly" per ADR-0013 — note: ADR excludes weekly in v1).
- `POST /recurring/{id}/deactivate` → `200`; card has `inactive` chip; `recurring_rules.active == FALSE`; preview list rendered empty (or omitted).
- `POST /recurring/{rule_id}/overrides` with `state=skipped` on an existing occurrence date → `200`; overrides table has the row; the occurrence `<li>` now has the `skipped` chip; `HX-Trigger` present.
- Multi-skip: `POST` twice with different `occurrence_date` values; both overrides persist independently (ADR-0013 multi-occurrence skip).
- `POST /recurring/{rule_id}/overrides/{date}/delete` → `200`; override row removed; occurrence `<li>` reverts to the default amount.
- Clearing an override on an occurrence that is **not** overridden → `404` (no row to delete).
- A11y: card has `aria-labelledby`; occurrence row buttons have `aria-label` carrying the date; preview list uses `<ol>` (ordered).

## Risks & gotchas

- **Preview horizon.** Default 12 months; configurable via query (`horizon_months=24`). Pure function in the service; cheap.
- **Day-of-month overflow.** A `monthly` rule with `day_of_month=31` on February must clamp to Feb 28/29. Service decision (ADR-0013 note); router shows the clamped date as-is.
- **Yearly cadence with `month_of_year`.** Required for yearly rules; validate in the form parser.
- **Occurrence id format in DOM.** `occ-{rule_id}-{YYYYMMDD}` (no dashes in the date segment) so CSS selectors do not break; the URL path still uses `YYYY-MM-DD` for readability. Convert in the template filter.
- **Override race.** Upsert is `INSERT ... ON CONFLICT (rule_id, occurrence_date) DO UPDATE`. Covered in the repository (ADR-0013).
- **Deactivation vs soft-delete.** Deactivation is `active=false` (keeps history); soft-delete is reserved and not exposed by the UI in v1. Virtual occurrences from an inactive rule disappear immediately (ADR-0013).
- **Overrides on an inactive rule.** Blocked at the service level — reactivating replays the stored overrides. Router returns 409 if attempted.
- **Transit rules.** Allowed only when `account` and `dest_account` share currency (ADR-0009). Enforced at service create / update.
- **Rendering performance.** 20 rules × 12 occurrences = 240 rows; cheap. Beyond 100 rules add a "load more" per card — flag for a later ADR, not in v1.
- **`HX-Trigger: forecast-stale` from inline occurrence toggles.** The forecast page must listen on `forecast-stale from:body` and re-fetch its fragment (see T-037).

## Anti-template design-quality move

The recurring page uses a **two-up editorial card grid** where each card is a calendar-first layout:

- The headline inside the card is the rule's `default_description` in the serif display, giving a magazine-like "name" to each rule. Cadence pill sits to the right in uppercase micro-caps. No chart, no icon noise.
- The preview is an **ordered list with hairline dividers**, not a table — the vertical rhythm matches a printed schedule. Dates on the left in `tabular-nums`, amount center-right, action buttons flush right.
- Skip / Override / Clear buttons use a monochrome **state-styled set**: default is quiet neutral; hovered is `--accent`; `:focus-visible` draws the 2px outline from `app.css`. States feel designed, not slapped on.
- Overridden rows carry a small italic "overridden" chip in the same ink color as the amount, giving a subtle depth signal; the amount itself does not change weight, keeping scanning uniform.
- `inactive` cards use a lighter ink (`--muted`) across the whole card body (not opacity) — ensures contrast ratios still pass WCAG AA. The whole card gains a dashed left rail to signal it is suspended.

## Handoff notes

- T-037 (forecast) subscribes to `forecast-stale from:body` which this router emits on every rule / override mutation.
- T-034 (planned) consumes `services.recurring.preview_occurrences` indirectly via `services.planned.list_planned`; this router's overrides affect the planned log automatically with no explicit coordination.
- The `preview_occurrences(conn, rule_id, horizon_months)` service surface is a hard dependency; if T-022/T-023 only expose `generate_occurrences` + `apply_overrides`, add this thin wrapper rather than inlining in the router.
