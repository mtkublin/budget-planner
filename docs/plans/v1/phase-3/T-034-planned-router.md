# T-034 — Planned Transactions Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

Show the planned transaction log — a UNION of stored one-off planned rows and virtual occurrences generated from active recurring rules — with filtering, export, create / edit / delete of one-offs, and the **manual promotion** flow (planned → actual) that is the central UX of this app. Promotion opens a modal pre-filled with amount / date / description; user edits and confirms; service inserts a `transactions` row and stamps `promoted_to_txn_id` on the one-off (or inserts a stored planned row first in the virtual case).

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md).
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — `planned.{find_by_id, create, update, soft_delete}`, `recurring.list_active`, `recurring.list_overrides`.
  - [`../phase-1/T-014-domain-types.md`](../phase-1/T-014-domain-types.md) — `PlannedView` dataclass unifying stored + virtual rows.
  - [`../phase-2/T-022-recurring-occurrence-generator.md`](../phase-2/T-022-recurring-occurrence-generator.md) — `generate_occurrences`, `apply_overrides` (pure).
  - [`../phase-2/T-023-planned-log-service.md`](../phase-2/T-023-planned-log-service.md) — `planned.list_planned(filter)`, `planned.promote_to_actual(planned_or_virtual_id, edits)`.
  - [`../phase-2/T-027-export-service.md`](../phase-2/T-027-export-service.md).
- ADRs:
  - [`../../adr/0012-planned-manual-promotion.md`](../../adr/0012-planned-manual-promotion.md) — promotion is manual via modal.
  - [`../../adr/0013-recurring-virtual-occurrences-and-overrides.md`](../../adr/0013-recurring-virtual-occurrences-and-overrides.md) — virtual occurrences carry rule defaults.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md).
  - [`../../adr/0020-import-deferred-export-v1.md`](../../adr/0020-import-deferred-export-v1.md).
- Service calls:
  - `services.planned.list_planned(conn, filter) -> list[PlannedView]`.
  - `services.planned.promote_to_actual(conn, source_ref, edits) -> Transaction` — `source_ref` is either `("planned", id)` or `("virtual", rule_id, occurrence_date)` to disambiguate the two.
  - `repositories.planned.{create, update, soft_delete, find_by_id}`.
  - `repositories.categories.list`, `repositories.accounts.list`.

## Deliverables

- Router module path: `src/budget_planner/web/routers/planned.py`.
- Jinja templates:
  - `templates/planned/index.html` — full page with filter sidebar + table + export links.
  - `templates/partials/planned/_table.html` — table body + pagination.
  - `templates/partials/planned/_row.html` — a single row (`<tr id="planned-{{ view.key }}">` where `view.key` is `"p-{id}"` for stored, `"v-{rule_id}-{YYYYMMDD}"` for virtual).
  - `templates/partials/planned/_form.html` — one-off create / edit form.
  - `templates/partials/planned/_promote_modal.html` — promotion modal (editable amount / date / description + source summary + account/category readonly).
  - `templates/partials/planned/_filter_form.html` — filter sidebar (same inputs as transactions filter plus "include virtual" / "only unpromoted / past-due" toggles).
- Tests: `tests/integration/web/test_planned.py`.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/planned` | query: filter + `page` + `page_size` + `include_virtual=true` + `scope=all\|unpromoted\|past_due_unpromoted` | full page | `planned.list_planned(filter)` | filter form: `hx-get="/planned/table"`, `hx-target="#planned-table"`, `hx-swap="outerHTML"`, `hx-trigger="change delay:200ms, keyup changed delay:400ms from:input[name=q]"`, `hx-push-url="true"` |
| GET | `/planned/table` | same query | fragment `_table.html` | `planned.list_planned` | — |
| GET | `/planned/new` | — | fragment `_form.html` (create one-off) | `categories.list`, `accounts.list` | `hx-get="/planned/new"`, `hx-target="#planned-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/planned` | form: `operation_date`, `category_id`, `account_id`, `dest_account_id?`, `amount`, `description` | 200 fragment `_row.html` (prepend) + OOB flash. 422 → `_form.html` with errors | `planned.create(NewPlanned)` | `hx-post="/planned"`, `hx-target="#planned-table tbody"`, `hx-swap="afterbegin"`. Header: `HX-Trigger: {"forecast-stale":true}` |
| GET | `/planned/{id}/edit` | path (stored id only) | fragment `_form.html` (edit) | `planned.find_by_id` | `hx-get="/planned/{id}/edit"`, `hx-target="#planned-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/planned/{id}` | form | 200 fragment `_row.html` (same key) + OOB flash. 422 → `_form.html` with errors | `planned.update(id, PatchPlanned)` | `hx-post="/planned/{id}"`, `hx-target="#planned-{{ view.key }}"`, `hx-swap="outerHTML"`. `HX-Trigger: forecast-stale` |
| POST | `/planned/{id}/delete` | path (stored id only) | 200 empty fragment (row removed) + OOB flash | `planned.soft_delete(id)` | `hx-post="/planned/{id}/delete"`, `hx-target="#planned-{{ view.key }}"`, `hx-swap="outerHTML"`, `hx-confirm="Soft-delete this planned entry?"`. `HX-Trigger: forecast-stale` |
| GET | `/planned/{key}/promote` | path: `key` is the view key (`p-{id}` or `v-{rule}-{YYYYMMDD}`) | fragment `_promote_modal.html` with amount/date/description pre-filled | `planned.list_planned` lookup by key or dedicated `planned.view_by_key(conn, key)` | `hx-get="/planned/{key}/promote"`, `hx-target="#modal-root"`, `hx-swap="innerHTML"` |
| POST | `/planned/{key}/promote` | form: `operation_date`, `amount`, `description` (category, accounts inherited and not editable) | 200 fragment `_row.html` (same key — row re-renders with "promoted" chip or disappears per spec) + OOB `#modal-root` empty + OOB flash. 422 → `_promote_modal.html` with errors | `planned.promote_to_actual(conn, source_ref, edits)` | `hx-post="/planned/{key}/promote"`, `hx-target="#planned-{{ view.key }}"`, `hx-swap="outerHTML"`. `HX-Trigger: {"balance-stale":true,"forecast-stale":true}` |
| GET | `/planned/export` | filter query + `format=csv\|parquet` | file download | `planned.list_planned` → `export.export_csv` \| `export.export_parquet` | plain `<a>`, not HTMX. |

## Template structure

`templates/planned/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Planned · Budget Planner{% endblock %}
{% block main %}
  <header class="mb-10 flex items-end justify-between gap-6">
    <h1 class="font-serif text-5xl leading-none">Planned</h1>
    <button hx-get="/planned/new" hx-target="#planned-form-slot" hx-swap="innerHTML" class="btn-accent">
      + New one-off
    </button>
  </header>

  <div class="grid grid-cols-[300px_1fr] gap-10">
    <aside>{% include "partials/planned/_filter_form.html" %}</aside>
    <section>
      <div id="planned-form-slot"></div>
      {% include "partials/planned/_table.html" %}
      <div class="mt-6 flex gap-3 text-sm">
        <a class="link-muted" href="/planned/export?format=csv&{{ filter.as_qs }}">Export CSV</a>
        <a class="link-muted" href="/planned/export?format=parquet&{{ filter.as_qs }}">Export Parquet</a>
      </div>
    </section>
  </div>

  <div id="modal-root"></div>
{% endblock %}
```

`templates/partials/planned/_row.html` (unified for stored and virtual):

```jinja
<tr id="planned-{{ view.key }}" class="row">
  <td class="whitespace-nowrap">
    {{ view.operation_date|date_fmt }}
    {% if view.is_virtual %}
      <span class="chip-muted ml-2" title="Virtual occurrence from rule {{ view.rule_id }}">rule</span>
    {% endif %}
    {% if view.is_past_due_unpromoted %}
      <span class="chip-warn ml-2">past due</span>
    {% endif %}
  </td>
  <td>{{ view.category.name }} {{ direction_badge(view.category.direction) }}</td>
  <td>{{ view.account.name }}{% if view.dest_account %} → {{ view.dest_account.name }}{% endif %}</td>
  <td class="text-right tabular-nums">{% include "partials/_money.html" %}</td>
  <td class="text-muted">{{ view.description }}</td>
  <td class="text-right space-x-2">
    <button hx-get="/planned/{{ view.key }}/promote"
            hx-target="#modal-root" hx-swap="innerHTML">
      Mark executed
    </button>
    {% if not view.is_virtual %}
      <button hx-get="/planned/{{ view.id }}/edit"
              hx-target="#planned-form-slot" hx-swap="innerHTML">Edit</button>
      <button class="text-destructive"
              hx-post="/planned/{{ view.id }}/delete"
              hx-target="#planned-{{ view.key }}" hx-swap="outerHTML"
              hx-confirm="Soft-delete this planned entry?">Delete</button>
    {% endif %}
  </td>
</tr>
```

Shared partials: `_money`, `_direction_badge`, `_pagination`, `_flash`, `_form_errors`.

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| Filter form | `#planned-table` | `outerHTML` | New table fragment; URL updated. | 500 → OOB flash. |
| `+ New one-off` | `#planned-form-slot` | `innerHTML` | Form inserted. | — |
| Create submit | `#planned-table tbody` | `afterbegin` | Row prepended; OOB flash; `HX-Trigger: forecast-stale`. | 422 → `_form.html` in slot. |
| Edit button (stored only) | `#planned-form-slot` | `innerHTML` | Form inserted populated. | — |
| Update submit | `#planned-{{ view.key }}` | `outerHTML` | Row swapped; `HX-Trigger: forecast-stale`. | 422 → `_form.html` in slot. |
| Delete button (stored only) | `#planned-{{ view.key }}` | `outerHTML` | Empty body → row removed; `HX-Trigger: forecast-stale`. | 500 → OOB flash. |
| `Mark executed` button | `#modal-root` | `innerHTML` | Modal fragment. | — |
| Promote submit | `#planned-{{ view.key }}` | `outerHTML` | Row re-renders. For a stored planned: row shows "promoted" chip with a link to the new transaction. For a virtual: the view key changes to the new stored planned row id (if the service persists one), **or** the response includes an OOB `#planned-{{ old_key }}` empty swap removing the virtual row and an `afterbegin` on `#planned-table tbody` adding the promoted row. OOB flash. `HX-Trigger: balance-stale, forecast-stale`. | 422 → `_promote_modal.html` with errors. |

`HX-Trigger` headers emitted:

- Create / update / delete: `{"forecast-stale":true}`.
- Promote: `{"balance-stale":true,"forecast-stale":true}` — a real txn now exists.

## Validation / acceptance

- `GET /planned?include_virtual=true` → `200`; table shows stored rows and virtual rows interleaved by `operation_date` ascending.
- Virtual row has `chip-muted "rule"` and **no** Edit / Delete buttons; its promote button is enabled.
- `GET /planned/table?include_virtual=false` → `200`; no row carries the `rule` chip.
- `POST /planned` with valid payload → `200`; body is a `<tr id="planned-p-<n>">`; `HX-Trigger` JSON has `forecast-stale`.
- `POST /planned/{id}/delete` on a stored row → `200`; `deleted_at IS NOT NULL` in `planned_transactions`.
- `GET /planned/v-{rule_id}-{YYYYMMDD}/promote` → `200`; modal pre-fills `amount`, `operation_date`, `description` from `generate_occurrences(rule, start, end)` + overrides.
- `POST /planned/v-.../promote` with edited amount → `200`; a row inserted into `transactions`; the service either (a) persists a stored planned row to carry `promoted_to_txn_id`, or (b) records the promotion under `recurring_rule_overrides` with `state='overridden'` and amount override — specify in T-023 which. For this plan, assume (a): service persists a stored planned row with `recurring_rule_id` + `occurrence_date` set, then marks `promoted_to_txn_id`.
- Promote response has `HX-Trigger` JSON with `balance-stale` and `forecast-stale`.
- Export respects the current filter; CSV and Parquet both parse and contain the same count as the filter result.
- A11y: modal has `role="dialog"` and `aria-modal="true"`; "Mark executed" has `aria-label` carrying the row date + description.

## Risks & gotchas

- **View key disambiguation.** Stored planned ids and virtual occurrences share a UI surface. Use `view.key = "p-<id>"` or `"v-<rule_id>-<YYYYMMDD>"` consistently. Route path parameter decoded in a tiny parser; service dispatches by prefix. A regex path constraint catches typos (`{key:^[pv]-\\d+(-\\d{8})?$}`).
- **Virtual promotion must create a stored row first.** Per ADR-0013 virtual occurrences are not materialised; promotion persists a planned row (sets `recurring_rule_id` + `occurrence_date` + `promoted_to_txn_id` on it) and inserts the transaction. The row in the table then changes key from `v-...` to `p-...` — handled via an OOB double-swap (remove old key + add new row).
- **Past-due detection.** `is_past_due_unpromoted` = `operation_date < today AND promoted_to_txn_id IS NULL AND state NOT IN ('skipped')`. Computed in the service, not the router.
- **Filter + scope coupling.** `scope=past_due_unpromoted` short-circuits `include_virtual=true` + a derived date filter. Route handler maps scope → filter DTO; keeps the service free of UI shape.
- **Decimal parsing.** Same convention as T-031 — reject `,`, reject sign, reject NaN. Transits same-currency only (ADR-0009).
- **Promotion signed amount.** Not applicable — promotion inserts a plain transaction (positive minor units) with direction derived from category (ADR-0008). Signed exception only applies to reconciliation (ADR-0011).
- **Modal close is OOB.** As with accounts: response includes `<div id="modal-root" hx-swap-oob="true"></div>` to clear.
- **Pagination keys.** Must be stable across virtual + stored rows; the service sorts by (`operation_date`, `view.key`) so pagination is deterministic.
- **N+1 risk.** Virtual occurrence generation is pure Python; make sure the service fetches overrides in one batched read per rule, not per occurrence. Flag for T-023 if the shape is single-row.
- **Export of virtual rows.** Export flattens them; the virtual flag is a column (`source` = `one_off`/`rule:<id>`).

## Anti-template design-quality move

The planned log is a **ledger of intent**, not a dashboard:

- Rows that are **past-due unpromoted** carry a tiny `chip-warn` with an oklch amber that stays legible against the warm `--surface`; it is the single warm accent on the page and functions as a direct call-to-action rather than decoration. No full-row background flip.
- Virtual rows carry a `chip-muted "rule"` + a subtle **left rail** on the row (`border-l` 2px in `--rule`) — a depth cue that visually distinguishes rules from one-offs without needing a separate column, giving a **grid-breaking** feel to an otherwise ordinary table.
- The promotion modal uses an **editorial two-pane layout**: a readonly summary panel on the left (date / category / account / rule-of-origin) and the three editable fields on the right. Typography-driven: the pre-filled amount uses the serif display at `text-4xl` so edits feel consequential; a muted "default: 500" below shows what the rule defaults to.
- Submit on the modal uses an accent button; cancel is a quiet text button far from the primary action — states feel designed.

## Handoff notes

- T-035 (recurring) emits `forecast-stale` from rule / override edits; the planned page listens for `forecast-stale` indirectly via its filter form being re-submitted on tab visibility — alternatively, add a `hx-trigger="forecast-stale from:body"` on `#planned-table` and `hx-get="/planned/table"` with the same qs. Document the choice in the final implementation; this plan allows either.
- T-037 (forecast) reads the same `planned.list_planned` service output; `forecast-stale` emissions here must propagate.
- `planned.view_by_key(conn, key) -> PlannedView` is the service surface this router expects for the promote GET; if T-023 only exposes `list_planned`, add this helper rather than filtering in the router.
