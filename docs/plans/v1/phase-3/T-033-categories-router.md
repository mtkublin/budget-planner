# T-033 — Categories Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

CRUD for the flat category list that drives transaction direction. Direction (`income` | `expense` | `transit` | `adjustment`) is chosen at creation and **locked once the category has been used by any transaction, planned transaction, or recurring rule**. System categories (`Transit`, `Reconciliation`) seeded by T-012 are undeletable. No currency, no hierarchy (ADR-0014 — hierarchy is a deferred concern; not planned for v2 or v3).

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md).
  - [`../phase-1/T-012-seed-data-migration.md`](../phase-1/T-012-seed-data-migration.md) — `Transit`, `Reconciliation` seeded with `is_system = TRUE`.
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — `categories.{list, find_by_id, create, update, soft_delete, is_used}`.
  - [`../phase-1/T-014-domain-types.md`](../phase-1/T-014-domain-types.md) — `Direction` enum.
- ADRs:
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — direction drives signed amount derivation.
  - [`../../adr/0014-budget-flat-no-rollover-three-tier.md`](../../adr/0014-budget-flat-no-rollover-three-tier.md) — flat category list, no parent.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md).
- Service calls: repository functions only; no Phase 2 service needs are introduced here. `categories.is_used(conn, category_id) -> bool` is the single business rule — if that function does not yet exist, add it as a repo helper (flag in Risks).

## Deliverables

- Router module path: `src/budget_planner/web/routers/categories.py`.
- Jinja templates:
  - `templates/categories/index.html` — full page: list grouped by direction (four columns).
  - `templates/partials/categories/_row.html` — single row (`<li id="cat-{{ c.id }}">`), swapped on create / update / delete.
  - `templates/partials/categories/_form.html` — create / edit form (direction field disabled on edit if `is_used`).
  - `templates/partials/categories/_empty.html` — per-direction empty state.
- Tests: `tests/integration/web/test_categories.py`.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/categories` | — | full page | `categories.list(include_system=True)` + for each: `categories.is_used` | `hx-trigger="load"` on the main container is **not** used; this page is a simple full-render. |
| GET | `/categories/new` | — | fragment `_form.html` (create) | — | `hx-get="/categories/new"`, `hx-target="#cat-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/categories` | form: `name`, `direction` (enum) | 200 fragment `_row.html` (new row) + OOB `_flash.html`. 422 → `_form.html` with errors | `categories.create(NewCategory)` | form: `hx-post="/categories"`, `hx-target="#cat-list-{{ direction }}"`, `hx-swap="beforeend"`. The `hx-target` is dynamically computed in JS-less way: form has four hidden list slots, server returns row with `hx-swap-oob="beforeend:#cat-list-{{ cat.direction }}"` so the client swap target is overridden by an OOB directive. |
| GET | `/categories/{id}/edit` | path | fragment `_form.html` (edit mode; direction disabled if `is_used`) | `categories.find_by_id`, `categories.is_used` | `hx-get="/categories/{id}/edit"`, `hx-target="#cat-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/categories/{id}` | form: `name` (always), `direction` (ignored if `is_used`) | 200 fragment `_row.html` (same id). 422 → `_form.html` with errors | `categories.update(id, PatchCategory)` (rejects direction change when `is_used`) | form: `hx-post="/categories/{id}"`, `hx-target="#cat-{{id}}"`, `hx-swap="outerHTML"` |
| POST | `/categories/{id}/delete` | path | 200 empty fragment (row removed) + OOB flash. 409 → OOB flash with reason, row unchanged (system cat or still used may be soft-deleted but blocks only system) | `categories.soft_delete(id)` — repo blocks `is_system = TRUE` | `hx-post="/categories/{id}/delete"`, `hx-target="#cat-{{id}}"`, `hx-swap="outerHTML"`, `hx-confirm="Soft-delete this category? Existing transactions keep the link."` |

## Template structure

`templates/categories/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Categories · Budget Planner{% endblock %}
{% block main %}
  <header class="mb-10 flex items-end justify-between">
    <h1 class="font-serif text-5xl leading-none">Categories</h1>
    <button hx-get="/categories/new" hx-target="#cat-form-slot" hx-swap="innerHTML" class="btn-accent">
      + New category
    </button>
  </header>

  <div id="cat-form-slot" class="mb-6"></div>

  <section class="grid gap-10 grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
    {% for direction, label in directions %}
      <div>
        <h2 class="font-serif text-xl mb-3 flex items-baseline gap-2">
          <span>{{ label }}</span>
          {{ direction_badge(direction) }}
        </h2>
        <ul id="cat-list-{{ direction }}" class="divide-y divide-[color:var(--rule)]">
          {% for c in categories_by_direction[direction] %}
            {% include "partials/categories/_row.html" %}
          {% else %}
            {% include "partials/categories/_empty.html" %}
          {% endfor %}
        </ul>
      </div>
    {% endfor %}
  </section>
{% endblock %}
```

`templates/partials/categories/_row.html`:

```jinja
<li id="cat-{{ c.id }}" class="py-3 flex items-center justify-between gap-3">
  <div>
    <span class="font-medium">{{ c.name }}</span>
    {% if c.is_system %}
      <span class="chip-muted ml-2" title="System category — undeletable">system</span>
    {% elif c.is_used %}
      <span class="chip-muted ml-2" title="In use — direction locked">in use</span>
    {% endif %}
  </div>
  <div class="text-sm space-x-2">
    <button hx-get="/categories/{{ c.id }}/edit"
            hx-target="#cat-form-slot" hx-swap="innerHTML"
            aria-label="Edit {{ c.name }}">Edit</button>
    {% if not c.is_system %}
      <button class="text-destructive"
              hx-post="/categories/{{ c.id }}/delete"
              hx-target="#cat-{{ c.id }}" hx-swap="outerHTML"
              hx-confirm="Soft-delete this category? Existing transactions keep the link."
              aria-label="Delete {{ c.name }}">Delete</button>
    {% endif %}
  </div>
</li>
```

Shared partials: `partials/_direction_badge.html`, `partials/_flash.html` (OOB), `partials/_form_errors.html`.

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| `+ New` | `#cat-form-slot` | `innerHTML` | Form inserted. | — |
| Create submit | `#cat-list-{{ direction }}` (via OOB override) | `beforeend` | New row appended to the correct column; OOB flash. | 422 → form slot gets `_form.html` with errors. |
| Edit button | `#cat-form-slot` | `innerHTML` | Form inserted; direction select disabled if `is_used` or `is_system`. | — |
| Update submit | `#cat-{{id}}` | `outerHTML` | Row swapped in place. If the row's direction column changed (never, since direction is locked once used) the server returns an OOB `beforeend:#cat-list-<new>` + OOB `outerHTML:#cat-{{id}}` empty. | 422 → form slot gets `_form.html` with errors. |
| Delete button | `#cat-{{id}}` | `outerHTML` | Row removed; OOB flash. | 409 (system) → row untouched, OOB flash with reason "System category cannot be deleted." |

No `HX-Trigger` headers are emitted by this router. Categories do not change balances; a direction change on an **unused** category is confined to this page.

## Validation / acceptance

- `GET /categories` → `200`; four column headers for the four directions; seeded `Transit` + `Reconciliation` rows have the `system` chip and no Delete button.
- `GET /categories/new` → `200`; `select name="direction"` has four options and is enabled.
- `POST /categories` with valid payload → `200`; row body matches `_row.html`; new row observed in DB with `is_system = FALSE`.
- `POST /categories` with duplicate `name` → `422`; inline error on `name`.
- `POST /categories` with `direction=garbage` → `422`; inline error.
- `GET /categories/{used_id}/edit` → `200`; direction `<select>` has `disabled` attribute and `aria-describedby` pointing to a short note "Direction is locked while this category is in use."
- `POST /categories/{used_id}` with a different `direction` → `200` and direction **unchanged** (silently ignored, documented), or `422` with inline note — pick 422 for clarity, assert exact copy.
- `POST /categories/{system_id}/delete` → `409`; row untouched; OOB flash fragment present with role=alert.
- `POST /categories/{plain_id}/delete` on an unused non-system category → `200`; empty body; `deleted_at` set; audit entry present.
- A11y: each row's action buttons have `aria-label` with the category name; columns have `<h2>` headings linked by `aria-labelledby` on the `<ul>`.

## Risks & gotchas

- **`is_used` performance.** Called N times on the index page. Repo should fulfil this with a single aggregated query (`LEFT JOIN` across `transactions`, `planned_transactions`, `recurring_rules` with `GROUP BY category_id`) that returns a `set[int]` of used ids; the router computes `is_used` from set membership. Flag for T-013.
- **Direction change rules.** Spec: direction locked once used. The form **disables** the control; the service **enforces** by rejecting any change. Belt + suspenders because clients can bypass disabled attributes.
- **System categories.** `is_system` flag is set in T-012. The route for delete returns 409 (not 422) because the request shape is valid; the resource state forbids it.
- **Soft delete and existing transactions.** Deleting a category does **not** cascade to transactions (ADR-0019). Transactions referencing a deleted category still render in the txn list via the stale name — the join must include deleted categories (`LEFT JOIN categories ON ... AND categories.deleted_at IS NULL` fails here). Repo layer must handle this. Flag for T-013. The copy in `hx-confirm` warns the user.
- **Direction column swap after update.** Direction cannot change on an in-use category, and name does not move the row. For unused categories a direction change does move the row; the OOB double-swap pattern is documented in HTMX interactions.
- **Form target computed server-side.** The create response's row uses `hx-swap-oob="beforeend:#cat-list-{{ direction }}"` to pick the correct column — this is the one place where the router sidesteps the client's `hx-target`. Document in a comment in `_row.html`.
- **No `HX-Trigger` emission.** Keep this clean — categories do not invalidate forecast or balance.
- **Deletion when `is_used=true` and non-system.** Allowed (soft) by spec. Audit log records it; the row vanishes from `/categories` but transactions still show the name via a `LEFT JOIN categories ... include_deleted=True` (repo-level `include_deleted` kwarg). This is a cross-cutting concern surfaced here, enforced in T-013.

## Anti-template design-quality move

A **four-column editorial list** rather than a shadcn table:

- Direction becomes a **structural pivot**, not a filter chip. Each direction gets its own column with a serif heading and its direction-badge pill right-aligned next to the title — the badge color is the only chromatic signal on an otherwise ink-on-paper page.
- Hairline dividers between rows (`divide-y divide-[color:var(--rule)]`), zero shadows, zero backgrounds. Hierarchy comes from column grouping + the single `font-medium` category name against muted `in use` / `system` chips.
- The "+ New" primary button sits top-right in isolation; the inline form slot appears above the four columns on open, pushing them down with an easing transform — a subtle depth cue without animating layout-bound properties on the columns themselves.
- Empty-state partial for each column is a one-liner: "No {{ label }} categories yet · [+ Add]"; the inline link opens the create form pre-selected on the right direction via query string (`/categories/new?direction=expense`). Grid-breaking: the empty state spans the column with slightly lighter type and italic serif, deliberately different from a row.

## Handoff notes

- T-031 (transactions), T-034 (planned), T-035 (recurring), T-036 (budget) all read `categories.list(include_system=True)` to populate `<select>` controls. No new API from this router is consumed by them — they all go through the repo directly.
- The `is_used` set-based repo helper is a hard dependency of this router; if it is not present after T-013, add it as a repo helper (not a service — this is a storage shape question).
- No `HX-Trigger` is emitted; sibling panels do not refresh on category edits. Document any future change in the T-030 HTMX event table.
