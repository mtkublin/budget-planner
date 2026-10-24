# T-032 — Accounts Router

> Phase 3 — Web Layer. Status: pending.

## Purpose

Surface account state: name, type, currency, opening balance, derived current balance, and per-account stats. Allow create / rename / soft-delete, manual balance snapshots, and the reconciliation flow (user enters true bank balance → system inserts an adjustment transaction). Business logic sits in `balance`, `snapshots`, and `reconciliation` services; this router renders.

## Inputs / prerequisites

- Upstream tasks:
  - [`T-030-fastapi-app-skeleton.md`](T-030-fastapi-app-skeleton.md).
  - [`../phase-1/T-013-repository-layer.md`](../phase-1/T-013-repository-layer.md) — `accounts.{list, find_by_id, create, update, soft_delete}`, `snapshots.create`.
  - [`../phase-2/T-021-balance-service.md`](../phase-2/T-021-balance-service.md) — `balance.derive_balance`, `balance.account_stats`.
  - [`../phase-2/T-026-reconciliation-service.md`](../phase-2/T-026-reconciliation-service.md) — `reconciliation.reconcile`.
- ADRs:
  - [`../../adr/0010-account-model-free-text-type.md`](../../adr/0010-account-model-free-text-type.md) — `type` is free text.
  - [`../../adr/0011-derived-balance-snapshots-reconciliation.md`](../../adr/0011-derived-balance-snapshots-reconciliation.md) — balance is derived; snapshots are audit; reconciliation inserts an adjustment txn.
  - [`../../adr/0006-multi-currency-model.md`](../../adr/0006-multi-currency-model.md) — currency immutable after creation; display aggregates in `base_currency`.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md).
- Service calls:
  - `balance.derive_balance(conn, account_id, as_of_date=None)`, `balance.account_stats(conn, account_id)`.
  - `fx.convert(conn, amount_minor, date=today, from_ccy, to_ccy=base_currency)` for base-currency aggregates.
  - `reconciliation.reconcile(conn, account_id, actual_balance_minor)`.
  - `repositories.snapshots.create(conn, NewSnapshot)`.

## Deliverables

- Router module path: `src/budget_planner/web/routers/accounts.py`.
- Jinja templates:
  - `templates/accounts/index.html` — full page, grid of account cards + totals strip.
  - `templates/partials/accounts/_card.html` — single account card (`<article id="account-{{ a.id }}">`), swapped on edit / snapshot / reconcile.
  - `templates/partials/accounts/_form.html` — create / edit form fragment.
  - `templates/partials/accounts/_totals.html` — totals strip (sum per currency + fortune in base currency), swapped when any card updates.
  - `templates/partials/accounts/_reconcile_modal.html` — modal form; closes via `hx-swap-oob` of an empty `#modal-root` and a card swap.
  - `templates/partials/accounts/_snapshot_toast.html` — small toast rendered OOB after a snapshot (also appended to a `#account-{{id}}-snapshots` list).
- Static assets: none.
- Tests: `tests/integration/web/test_accounts.py`.

## Endpoints

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/accounts` | — | full page | `accounts.list` → map(derive_balance + account_stats + fx.convert) | listens on `HX-Trigger: balance-stale` via `hx-trigger="balance-stale from:body"` on `#accounts-grid` with `hx-get="/accounts"` + `hx-select="#accounts-grid"` |
| GET | `/accounts/new` | — | fragment `_form.html` (create) | — | `hx-get="/accounts/new"`, `hx-target="#account-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/accounts` | form: `name`, `type?`, `currency` (ISO 4217), `opening_balance` (decimal) | 200 fragment `_card.html` (new card) + OOB `_totals.html` + OOB `_flash.html`. 422 → `_form.html` with errors | `accounts.create(NewAccount)` | form: `hx-post="/accounts"`, `hx-target="#accounts-grid"`, `hx-swap="beforeend"`. Headers: `HX-Trigger: balance-stale` |
| GET | `/accounts/{id}/edit` | path | fragment `_form.html` (edit; currency field disabled) | `accounts.find_by_id` | `hx-get="/accounts/{id}/edit"`, `hx-target="#account-form-slot"`, `hx-swap="innerHTML"` |
| POST | `/accounts/{id}` | form (`name`, `type` only — currency ignored) | 200 fragment `_card.html` (same id) + OOB totals. 422 → `_form.html` with errors | `accounts.update(id, PatchAccount)` (rejects currency change) | form: `hx-post="/accounts/{id}"`, `hx-target="#account-{{id}}"`, `hx-swap="outerHTML"` |
| POST | `/accounts/{id}/delete` | path | 200 empty fragment (card removed via `outerHTML`) + OOB totals + OOB flash | `accounts.soft_delete` | `hx-post="/accounts/{id}/delete"`, `hx-target="#account-{{id}}"`, `hx-swap="outerHTML"`, `hx-confirm="Soft-delete this account? Transactions remain."`. `HX-Trigger: balance-stale, forecast-stale` |
| POST | `/accounts/{id}/snapshot` | path | 200 fragment: appended `<li>` into `#account-{{id}}-snapshots` + OOB toast | `snapshots.create(conn, {account_id, balance=derived_now, taken_at=now, note="user snapshot"})` | `hx-post="/accounts/{id}/snapshot"`, `hx-target="#account-{{id}}-snapshots"`, `hx-swap="beforeend"` |
| GET | `/accounts/{id}/reconcile` | path | fragment `_reconcile_modal.html` with current derived balance pre-filled | `balance.derive_balance(id, None)` | `hx-get="/accounts/{id}/reconcile"`, `hx-target="#modal-root"`, `hx-swap="innerHTML"` |
| POST | `/accounts/{id}/reconcile` | form: `actual_balance` (decimal, signed allowed) | 200 fragment `_card.html` (swapped in place) + OOB `#modal-root` empty + OOB flash. 422 → `_reconcile_modal.html` with errors | `reconciliation.reconcile(conn, id, actual_minor)` | form: `hx-post="/accounts/{id}/reconcile"`, `hx-target="#account-{{id}}"`, `hx-swap="outerHTML"`. `HX-Trigger: balance-stale, forecast-stale` |

## Template structure

`templates/accounts/index.html`:

```jinja
{% extends "base.html" %}
{% block title %}Accounts · Budget Planner{% endblock %}
{% block main %}
  <header class="mb-10 flex items-end justify-between gap-6">
    <div>
      <h1 class="font-serif text-5xl leading-none">Accounts</h1>
      <p class="text-muted mt-2">{{ accounts|length }} accounts · fortune
        <span class="tabular-nums">{{ fortune_base|money(base_ccy) }}</span></p>
    </div>
    <button hx-get="/accounts/new" hx-target="#account-form-slot" hx-swap="innerHTML" class="btn-accent">
      + New account
    </button>
  </header>

  {% include "partials/accounts/_totals.html" %}

  <div id="account-form-slot" class="my-6"></div>

  <section id="accounts-grid"
           class="grid gap-6 grid-cols-[repeat(auto-fit,minmax(320px,1fr))]"
           hx-trigger="balance-stale from:body"
           hx-get="/accounts"
           hx-select="#accounts-grid"
           hx-swap="outerHTML">
    {% for a in accounts %}
      {% include "partials/accounts/_card.html" %}
    {% endfor %}
  </section>

  <div id="modal-root"></div>
{% endblock %}
```

`templates/partials/accounts/_card.html` (identity is load-bearing for HTMX swaps):

```jinja
<article id="account-{{ a.id }}" class="card">
  <header class="flex items-baseline justify-between">
    <h2 class="font-serif text-2xl">{{ a.name }}</h2>
    <span class="chip-muted">{{ a.currency }}</span>
  </header>
  <p class="text-muted text-sm">{{ a.type or "—" }}</p>

  <dl class="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
    <dt>Balance</dt>   <dd class="text-right tabular-nums">{{ a.balance|money(a.currency) }}</dd>
    <dt>Txns</dt>      <dd class="text-right tabular-nums">{{ a.stats.count }}</dd>
    <dt>Avg in</dt>    <dd class="text-right tabular-nums">{{ a.stats.avg_in|money(a.currency) }}</dd>
    <dt>Avg out</dt>   <dd class="text-right tabular-nums">{{ a.stats.avg_out|money(a.currency) }}</dd>
    <dt>Last</dt>      <dd class="text-right">{{ a.stats.last_activity|date_fmt }}</dd>
  </dl>

  <ul id="account-{{ a.id }}-snapshots" class="sr-only" aria-label="recent snapshots"></ul>

  <footer class="mt-6 flex gap-2 text-sm">
    <button hx-post="/accounts/{{ a.id }}/snapshot" hx-target="#account-{{ a.id }}-snapshots" hx-swap="beforeend">
      Snapshot
    </button>
    <button hx-get="/accounts/{{ a.id }}/reconcile" hx-target="#modal-root" hx-swap="innerHTML">
      Reconcile
    </button>
    <button hx-get="/accounts/{{ a.id }}/edit" hx-target="#account-form-slot" hx-swap="innerHTML">
      Edit
    </button>
    <button class="text-destructive ml-auto"
            hx-post="/accounts/{{ a.id }}/delete"
            hx-target="#account-{{ a.id }}"
            hx-swap="outerHTML"
            hx-confirm="Soft-delete this account? Transactions remain.">
      Delete
    </button>
  </footer>
</article>
```

Shared partials consumed:

- `partials/_money.html`, `partials/_flash.html` (OOB), `partials/_form_errors.html`.

## HTMX interactions

| Trigger | Target | Swap | Success UX | Error UX |
|---------|--------|------|------------|----------|
| `+ New account` | `#account-form-slot` | `innerHTML` | Form inserted. | — |
| Create submit | `#accounts-grid` | `beforeend` | New card appended; OOB totals re-rendered; OOB flash. | 422 → form slot gets `_form.html` with errors. |
| Edit button | `#account-form-slot` | `innerHTML` | Form inserted (currency disabled). | — |
| Update submit | `#account-{{id}}` | `outerHTML` | Card swapped; OOB totals re-rendered. | 422 → form slot gets `_form.html` with errors. |
| Delete button | `#account-{{id}}` | `outerHTML` | Empty response removes card; OOB totals; flash; `balance-stale` + `forecast-stale` triggered. | 500 → flash OOB; card untouched. |
| Snapshot button | `#account-{{id}}-snapshots` | `beforeend` | Appends `<li>` with timestamp + balance; OOB toast flash. | 500 → OOB flash with error copy. |
| Reconcile button | `#modal-root` | `innerHTML` | Modal appears pre-filled with derived balance. | — |
| Reconcile submit | `#account-{{id}}` | `outerHTML` | Modal cleared via OOB (`#modal-root`); card swapped with new balance; flash; `balance-stale` + `forecast-stale` triggered. | 422 → modal gets `_reconcile_modal.html` with errors. |
| `balance-stale` event from any mutation anywhere | `#accounts-grid` | `outerHTML` (via `hx-select`) | Grid re-renders with new balances; cards keep their ids so focus does not jump unexpectedly. | — |

`HX-Trigger` headers emitted by this router:

- Create / update: `HX-Trigger: {"balance-stale":true}` (fortune may change via opening balance).
- Delete: `{"balance-stale":true,"forecast-stale":true}`.
- Reconcile (POST): `{"balance-stale":true,"forecast-stale":true}` (inserts a new txn).

## Validation / acceptance

`TestClient` + BeautifulSoup:

- `GET /accounts` → `200`, DOM has `#accounts-grid` + a card for every seeded account; each card has stable `id="account-<n>"`; a totals strip renders a `tabular-nums` fortune in base currency.
- `POST /accounts` with valid payload → `200`, body is a `<article id="account-...">`, DB row inserted via repo (verified by direct read), `HX-Trigger` header JSON contains `balance-stale`.
- `POST /accounts` with duplicate `name` → `422`, `_form.html` fragment with inline error on `name` field.
- `POST /accounts/{id}` with `currency=XYZ` → `422`; repo currency unchanged.
- `POST /accounts/{id}/snapshot` → `200`; `account_snapshots` row inserted with `balance == derive_balance(id, today)`; derived balance **unchanged** (ADR-0011).
- `GET /accounts/{id}/reconcile` → `200`, modal fragment contains an input `name="actual_balance"` and shows the current derived balance.
- `POST /accounts/{id}/reconcile` with `actual_balance = derived + 10.00` → `200`; a new transaction row created with `category = Reconciliation`, `amount = 1000` (signed), `description = "auto-reconciliation {today}"` (ADR-0011); card re-rendered; `HX-Trigger` has `balance-stale` and `forecast-stale`.
- Soft-delete sets `deleted_at IS NOT NULL`; existing transactions **are not** cascaded (ADR-0019); audit log has a `delete` entry for the account.
- A11y: every card has `<article aria-labelledby="account-{{id}}-name">` wrapping the heading; action buttons carry readable labels; modal has `role="dialog"` and `aria-modal="true"` with focus-trap seeded by HTMX swap event hook (documented in template comment, implementation detail).
- Totals strip renders one row per currency plus the fortune row in `base_currency`; FX rate conversion uses the latest cached rate (not historical) via `fx.convert(..., date=today)`.

## Risks & gotchas

- **Currency immutability.** PATCH route must silently drop any `currency` field (not 422 if omitted; 422 only if sent and different). Default: template disables the input.
- **Reconciliation adjustment sign.** The service writes a **signed** amount (ADR-0008 exception, ADR-0011). The router passes `actual_minor` into the service; the service computes the delta. Router does not reach into the amount sign.
- **Transits on soft-deleted account.** Soft-deleting an account that is referenced by `dest_account_id` of a transit does not cascade; `balance.derive_balance` on a deleted account must still work (no 500) because historical derivations may need it. Covered by a test.
- **FX for totals strip.** Base-currency conversion uses `fx.convert(..., today)`. Service caches rates in `fx_rates` (ADR-0006). If network is down and no cached rate exists, service returns last-known rate; router shows a muted note "FX rate from <date>" in the strip for transparency.
- **HTMX `hx-select` on grid.** The `balance-stale` listener re-fetches `/accounts` and selects `#accounts-grid`; this re-renders the whole grid in one swap. Avoids per-card targeting storms when many cards are stale. Keep card ids stable so focus and scroll position hold.
- **Snapshot `taken_at`.** Stored UTC; displayed `Europe/Warsaw` via `dt_local` (ADR-0007).
- **Decimal parsing.** `opening_balance` and `actual_balance` accept a locale-free decimal with `.` separator. Router rejects `,` with a specific inline error pointing to the format.
- **Modal close is OOB.** Response body is the swapped card; `#modal-root` is cleared via a top-level `<div id="modal-root" hx-swap-oob="true"></div>` sibling in the same response.
- **N+1 on account cards.** `balance.derive_balance` is called per account; services layer batches via a single SQL aggregated query (`balance.derive_balances(conn, [ids])`) — add that service call if it doesn't exist (flag for T-021 handoff rather than inventing SQL here).

## Anti-template design-quality move

Account cards are **not shadcn cards**:

- The grid is `grid-cols-[repeat(auto-fit,minmax(320px,1fr))]` with `gap-6` — the cards resize responsively but line up on a shared baseline. Hierarchy via **scale contrast**: account name set in the serif display at `text-2xl`, currency chip in uppercase micro-caps, numbers in `tabular-nums` so columns in the definition list align without a table.
- The balance row **does not** rely on color-coded signs; direction is a non-issue at the account level, only the magnitude matters.
- Primary action layout: `Snapshot | Reconcile | Edit | Delete` where `Delete` is pushed to the far right with `ml-auto` and uses a muted destructive tint on hover only — states feel designed, not stickered on.
- Totals strip is a horizontal **two-row editorial band** at the top of the page: per-currency row above a thin rule, fortune (base currency) below in larger numerals. Avoids the "KPI tiles" cliché.
- Modal is a **sheet from the top of `#main`** rather than a centered overlay; `prefers-reduced-motion` shortcut cut via `app.css` tokens — motion clarifies the layer, not the whole page.

## Handoff notes

- T-039 (home dashboard) reads the fortune number by including `partials/accounts/_totals.html` and listening on `balance-stale`.
- T-037 (forecast) consumes `balance-stale` + `forecast-stale` events emitted here.
- `balance.derive_balances(conn, [ids]) -> dict[int, int]` is **the batched read** this router expects. If T-021 landed with only the single-id form, add the batched form before T-032 ships; this plan documents the dependency.
- The `#modal-root` div in `base.html` is this router's modal host; T-034 (planned promotion) reuses the same slot.
