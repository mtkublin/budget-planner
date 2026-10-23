# T-031 — Transactions Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

Expose the persistent transaction log through the browser: list with a filter sidebar, create / edit / soft-delete via HTMX fragments, and stream the current filtered view out as CSV or Parquet. All business logic lives in the Phase 2 services and the Phase 1 repository; this router parses requests, calls those, and renders Jinja fragments.

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md) — app factory, `get_db`, Jinja env, shared partials, `trigger()` helper.
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — `transactions.list_filtered`, `.create`, `.update`, `.soft_delete`, `.find_by_id`; `categories.list`, `accounts.list`.
  - [`../phase-1/T-014-domain-types.md`](../phase-1/T-014-domain-types.md) — `NewTransaction`, `PatchTransaction`, `TransactionFilter`, `Direction` enum, `Money` helpers.
  - [`../phase-2/T-027-export-service.md`](../phase-2/T-027-export-service.md) — `export_csv`, `export_parquet`.
- ADRs:
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — positive integer minor units, direction derived from category.
  - [`../../adr/0009-transit-single-row-model.md`](../../adr/0009-transit-single-row-model.md) — transit rows carry `dest_account_id`; same-currency only.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md) — delete is `UPDATE deleted_at`; audit written in the same transaction by the repo.
  - [`../../adr/0020-import-deferred-export-v1.md`](../../adr/0020-import-deferred-export-v1.md) — export operates on the current filter.
  - [`../../adr/0021-functional-style-no-oop.md`](../../adr/0021-functional-style-no-oop.md) — handlers are decorated functions, no router class.
- Service calls:
  - `repositories.transactions.{list_filtered, find_by_id, create, update, soft_delete}` (DB mutations).
  - `repositories.categories.list(include_system=True)` + `repositories.accounts.list()` for form choices.
  - `adapters.export.{csv_bytes, parquet_bytes}` (or `services.export.{export_csv, export_parquet}`).

## Deliverables

- Router module path: `src/budget_planner/web/routers/transactions.py`.
- Jinja templates:
  - `templates/transactions/index.html` — full page: filter sidebar + table + "new" button, extends `base.html`.
  - `templates/partials/transactions/_filter_form.html` — HTMX filter form fragment (GET).
  - `templates/partials/transactions/_table.html` — table wrapper (header + body + pagination), swapped on filter changes.
  - `templates/partials/transactions/_row.html` — a single `<tr id="txn-{{ txn.id }}">`, swapped on create / update / delete.
  - `templates/partials/transactions/_form.html` — the create / edit form (used for both; `method`/`action` differ via context).
  - `templates/partials/transactions/_empty.html` — zero-state block rendered inside `_table.html` when the filter returns nothing.
- Static assets: none specific; relies on T-030 tokens.
- Tests: `tests/integration/web/test_transactions.py` using FastAPI `TestClient` + BeautifulSoup.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/transactions` | query: `date_from`, `date_to`, `category_id`, `account_id`, `min_amount`, `max_amount`, `q` (description substring), `page`, `page_size` | full HTML page (`index.html`) | `transactions.list_filtered(filter)` | on filter form: `hx-get="/transactions/table"`, `hx-target="#txn-table"`, `hx-swap="outerHTML"`, `hx-trigger="change delay:200ms, keyup changed delay:400ms from:input[name=q]"`, `hx-push-url="true"` |
| GET | `/transactions/table` | same query params | fragment `_table.html` | `transactions.list_filtered` | — (consumed by `/transactions` form) |
| GET | `/transactions/new` | — | fragment `_form.html` (create mode) | `categories.list`, `accounts.list` | on "+ New" button: `hx-get="/transactions/new"`, `hx-target="#txn-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/transactions` | multipart form: `operation_date`, `category_id`, `account_id`, `dest_account_id?`, `amount` (decimal in major units), `description` | 200 fragment `_row.html` + OOB `_flash.html`. On validation error → 422 `_form.html` with inline errors | `transactions.create(NewTransaction)` | form: `hx-post="/transactions"`, `hx-target="#txn-table tbody"`, `hx-swap="afterbegin"`. Response headers: `HX-Trigger: {"balance-stale":true,"forecast-stale":true}` |
| GET | `/transactions/{id}/edit` | path | fragment `_form.html` (edit mode) | `transactions.find_by_id` | row edit button: `hx-get="/transactions/{id}/edit"`, `hx-target="#txn-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/transactions/{id}` | multipart form (same shape as create) | 200 fragment `_row.html` (same `id`, outer-swap replaces the row). On error → 422 `_form.html` | `transactions.update(id, PatchTransaction)` | form: `hx-post="/transactions/{id}"`, `hx-target="#txn-{{id}}"`, `hx-swap="outerHTML"`. Response: `HX-Trigger: balance-stale, forecast-stale` |
| POST | `/transactions/{id}/delete` | path | 200 empty fragment (removes the row via `hx-swap="outerHTML"` with no content) + OOB flash | `transactions.soft_delete(id)` | row delete button: `hx-post="/transactions/{id}/delete"`, `hx-target="#txn-{{id}}"`, `hx-swap="outerHTML"`, `hx-confirm="Soft-delete this transaction?"`. Response: `HX-Trigger: balance-stale, forecast-stale` |
| GET | `/transactions/export` | same filter query + `format=csv\|parquet` | file download (`Content-Disposition: attachment; filename="transactions_YYYYMMDD.csv"`) | `transactions.list_filtered` → `export.export_csv` \| `export.export_parquet` | export buttons: standard `<a href="/transactions/export?format=csv&…">`; **not** HTMX — browsers must handle download. |

## Template structure

`templates/transactions/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Transactions · Budget Planner{% endblock %}
{% block main %}
  <header class="flex items-baseline justify-between gap-6 mb-10">
    <h1 class="font-serif text-5xl leading-none">Transactions</h1>
    <button hx-get="/transactions/new"
            hx-target="#txn-form-slot"
            hx-swap="innerHTML"
            class="btn-accent">
      + New transaction
    </button>
  </header>

  <div class="grid grid-cols-[280px_1fr] gap-10">
    <aside aria-labelledby="filter-heading">
      <h2 id="filter-heading" class="sr-only">Filter transactions</h2>
      {% include "partials/transactions/_filter_form.html" %}
    </aside>

    <section>
      <div id="txn-form-slot"></div>
      {% include "partials/transactions/_table.html" %}
      <div class="mt-6 flex gap-3">
        <a class="link-muted" href="/transactions/export?format=csv&{{ filter.as_qs }}">Export CSV</a>
        <a class="link-muted" href="/transactions/export?format=parquet&{{ filter.as_qs }}">Export Parquet</a>
      </div>
    </section>
  </div>
{% endblock %}
```

`templates/partials/transactions/_row.html` (representative; row identity is load-bearing for HTMX):

```jinja
<tr id="txn-{{ txn.id }}" class="row">
  <td class="whitespace-nowrap">{{ txn.operation_date|date_fmt }}</td>
  <td>
    {{ txn.category.name }}
    {{ direction_badge(txn.category.direction) }}
  </td>
  <td>{{ txn.account.name }}{% if txn.dest_account %} → {{ txn.dest_account.name }}{% endif %}</td>
  <td class="text-right">{% include "partials/_money.html" %}</td>
  <td class="text-muted">{{ txn.description }}</td>
  <td class="text-right space-x-2">
    <button hx-get="/transactions/{{ txn.id }}/edit"
            hx-target="#txn-form-slot"
            hx-swap="innerHTML"
            aria-label="Edit transaction {{ txn.id }}">Edit</button>
    <button hx-post="/transactions/{{ txn.id }}/delete"
            hx-target="#txn-{{ txn.id }}"
            hx-swap="outerHTML"
            hx-confirm="Soft-delete this transaction?"
            aria-label="Delete transaction {{ txn.id }}">Delete</button>
  </td>
</tr>
```

Partials used across routers (defined in T-030):

- `partials/_money.html` — invoked by `{{ ... }}` or `{% include %}` with `amount`, `currency` in context.
- `partials/_direction_badge.html`
- `partials/_pagination.html` — footer of `_table.html`.
- `partials/_form_errors.html` — inside `_form.html` when 422.
- `partials/_flash.html` — OOB-swapped on every mutation.

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| Filter form `change` / `keyup` (debounced) | `#txn-table` | `outerHTML` | New table fragment; URL updated (`hx-push-url`). | 500 → flash OOB. |
| `+ New transaction` button | `#txn-form-slot` | `innerHTML` | Form inserted above the table. | — |
| Create submit (`POST /transactions`) | `#txn-table tbody` | `afterbegin` | New `<tr>` prepended; form slot cleared; flash OOB; `HX-Trigger: balance-stale, forecast-stale`. | 422 → form slot swapped with `_form.html` carrying inline errors; no row inserted. |
| Edit button on a row | `#txn-form-slot` | `innerHTML` | Form inserted with values populated. | — |
| Update submit (`POST /transactions/{id}`) | `#txn-{{id}}` | `outerHTML` | Row replaced in place; form slot cleared; flash OOB; triggers emitted. | 422 → `_form.html` with errors. |
| Delete button | `#txn-{{id}}` | `outerHTML` | Empty body → row removed; flash OOB; triggers emitted. | 500 → row untouched, flash OOB. |
| Export links | — (full navigation) | — | Browser download. | — |

`HX-Trigger` headers emitted:

- Create / update / delete: `HX-Trigger: {"balance-stale":true,"forecast-stale":true}` — accounts page and forecast fragment re-fetch themselves if visible in another tab or in the home dashboard.

## Validation / acceptance

`TestClient` + BeautifulSoup, structural (no full snapshots):

- `GET /transactions` → `200`; parsed DOM contains `#txn-table`, filter form with every expected `name` attribute, "+ New" button whose `hx-get` equals `/transactions/new`.
- `GET /transactions/table?category_id=X` → `200`; response body **does not** contain `<html>` (fragment, not full page) and all rendered rows have `category_id=X`.
- `GET /transactions/new` → `200`; form has `hx-post="/transactions"`, inputs for every mandatory field, selects for `category_id` and `account_id` populated from the DB.
- `POST /transactions` with valid data → `200`; body is a `<tr>` with `id="txn-<n>"`; `HX-Trigger` header parses as JSON with `balance-stale` and `forecast-stale` set to true. Insert verified via a direct repo read.
- `POST /transactions` with invalid data (missing `amount`) → `422`; body is `_form.html` fragment with `role="alert"` block listing the missing field.
- Decimal amount `"12.34"` (PLN account) persists as `1234` minor units; `"12"` persists as `1200`. Negative amounts rejected with 422 (ADR-0008).
- Transit between accounts of **different** currencies rejected with 422 (ADR-0009).
- `POST /transactions/{id}/delete` → `200`; empty body; repo row has `deleted_at IS NOT NULL`; audit entry present.
- `GET /transactions/export?format=csv` with a 3-row filter → `200`; `Content-Type: text/csv; charset=utf-8`; `Content-Disposition` is `attachment` with timestamped filename; body is three data rows + header.
- `GET /transactions/export?format=parquet` → `application/vnd.apache.parquet` or `application/octet-stream`; body parses via `pyarrow.parquet.read_table(BytesIO(body))` and has the same row count as the filter.
- A11y: filter form has `<label for="...">` for every input; row action buttons carry `aria-label`; table has `<caption class="sr-only">`.

## Risks & gotchas

- **Decimal ↔ minor units.** The form accepts a user-friendly decimal (`12.34`); the service expects positive integer minor units. Convert via `Money.to_minor_units(Decimal(s), ccy)` in the router (parsing layer only, not business logic). Reject NaN / sign / excess precision at the parse step with a 422 and inline error.
- **`python-multipart`.** Required for form POSTs; already pinned in T-001. If missing, FastAPI raises an opaque 500; a boot check in T-030 handles this.
- **Timezone display.** `created_at`/`updated_at` are UTC; render via `dt_local` filter from T-030 (ADR-0007). `operation_date` is a `DATE`, display verbatim.
- **Row identity.** `id="txn-{{ txn.id }}"` is the only swap target used for update/delete; renaming it breaks HTMX. Covered by a dedicated structural test.
- **Partial swap identity (`hx-select` vs `hx-swap-oob`).** On create we return `_row.html` targeted at the tbody and OOB-swap `#flash`. Do **not** nest the flash inside the row; the OOB element must be a top-level sibling in the response body.
- **N+1 risk on list.** `transactions.list_filtered` must return joined category + account rows (repo responsibility; this plan surfaces the dependency). Add a test asserting the number of SQL statements per `GET /transactions/table` is bounded regardless of page size.
- **Filter persistence.** `hx-push-url="true"` on the filter form plus `pydantic` parsing in the handler covers deep-link reload. Confirm `page` resets to 1 whenever a non-page filter changes.
- **Export respects filter.** Export handler reuses the same `TransactionFilter` parser; do **not** copy-paste logic. Shared parser is a module-level function `parse_filter(request) -> TransactionFilter`.
- **CSRF.** No auth in v1 (ADR-0005); CSRF is a no-op. The `csrf_token` global is empty.
- **Transits in the row partial.** Show `source → dest` and never a signed amount; the badge communicates direction.

## Anti-template design-quality move

Lean editorial, not a shadcn grid:

- The page is a **two-column asymmetric layout** (`grid-cols-[280px_1fr] gap-10`): a quiet filter sidebar at the left set in muted type, and a wide ledger-style table at the right. No cards, no shadows — hairline rules at `--rule` separate rows; alternating row backgrounds are **disabled**, hierarchy comes from the date column being heavier (`font-semibold`) and the amount column being right-aligned with `tabular-nums`.
- Direction is conveyed by a **pill with semantic oklch color**, not a plus/minus sign in the amount. Transits render as `source → dest` with a thin arrow glyph; the row has no sign on the amount (ADR-0008).
- Row hover: a subtle 1px left border in `--accent` and a 50ms transition on `color`. No full-row background flip — motion is used to clarify, not decorate (per `rules/web/design-quality.md`).
- Filter form uses **grid-breaking rhythm**: date range on its own row, category + account side-by-side, amount range inline, free-text search on its own row with a visible debounce indicator (`<span aria-live="polite">`).

## Handoff notes

- T-039's home dashboard reads from `/transactions` row partials indirectly via a "recent 7 days" slice; T-039 may call `transactions.list_filtered(...)` directly and reuse `partials/transactions/_row.html` without changes.
- T-032 (accounts) and T-037 (forecast) consume the `balance-stale` + `forecast-stale` events emitted here. Any new event name requires adding it to the T-030 "HTMX interactions" table before use.
- The `parse_filter(request) -> TransactionFilter` helper exposed from this module is reused by T-038 (analytics) for its over-the-same-log views; it stays public.
