# T-064 — Ledger Unification

> Phase 6 — UX redesign. Status: pending.

## Purpose

Collapse `/transactions`, `/planned`, and `/recurring` into one page `/ledger` with a segmented control (Actual · Planned · Recurring) and a shared filter form. One template renders three view variants; one fragment endpoint (`/ledger/table?view=…`) dispatches to the right repository query. Keyboard `[` and `]` cycle the segmented control. Alias the three old fragment routes to the new one for a release so existing scripts keep working.

## Inputs / prerequisites

- Upstream tasks: T-061 (shell), T-062 (nav + shortcut attrs).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — ledger consolidation, segmented control, alias contract.
- Adjacent standards: T-053 tokens; `rules/web/patterns.md` (URL as state — view, filters, pagination live in the query string).
- Existing repositories (reuse):
  - `repositories.transactions.list_transactions(filters)` for Actual.
  - `repositories.planned.list_planned(filters)` for Planned.
  - `repositories.recurring.list_recurring(filters)` for Recurring.
- Existing fragment routes to alias (not delete): `/transactions/table`, `/planned/table`, `/recurring` (list).

## Deliverables

New files:

- `src/budget_planner/web/routers/ledger.py`:
  - `GET /ledger` — full page; reads `view` query param (default `actual`), renders `ledger/index.html`.
  - `GET /ledger/table?view=actual|planned|recurring&…filters` — fragment; renders `ledger/_table.html` with the result set for the selected view.
- `src/budget_planner/web/templates/ledger/index.html`:
  - Page shell with:
    - Segmented control at top (`<fieldset>` of three `<button>`s, `aria-pressed`, keyboard `[` / `]` cycle via T-068's listener).
    - Shared filter form (`<form hx-get="/ledger/table" hx-target="#ledger-table" hx-trigger="change, submit">`) with: date-range, category multi-select, account multi-select, direction, search box (`description` substring, 400 ms debounce via `hx-trigger="input changed delay:400ms"`).
    - Container `<section id="ledger-table" aria-live="polite">{% include "ledger/_table.html" %}</section>`.
- `src/budget_planner/web/templates/ledger/_table.html`:
  - Shared columns: date · direction pill · amount (mono, right-aligned, tabular-nums) · category · account · description.
  - View-specific columns via `{% if view == "planned" %}` … `{% elif view == "recurring" %}` …:
    - `planned`: adds `Promoted?` column + `Promote →` button (opens `_promote_modal.html` into `#modal-root`).
    - `recurring`: adds `Cadence` + `Next due` columns + an inline Overrides accordion (`<details>` with override table).
  - Pagination controls bottom-right; links are `hx-get` to the same fragment with updated `page=` param.

Updated files:

- `src/budget_planner/web/routers/transactions.py`:
  - `GET /transactions/table` returns `RedirectResponse(url=f"/ledger/table?view=actual&{query_string}", status_code=307)` **or** internally renders the same `ledger/_table.html` with `view="actual"` — pick redirect for simplicity; HTMX follows 307.
- `src/budget_planner/web/routers/planned.py`:
  - `GET /planned/table` → `307` to `/ledger/table?view=planned&…`.
- `src/budget_planner/web/routers/recurring.py`:
  - `GET /recurring` fragment → `307` to `/ledger/table?view=recurring&…`.

Page-level redirects (`/transactions`, `/planned`, `/recurring` → `/ledger?view=…`) are owned by T-070, not here.

Not deliverables:

- No new transaction create/update flows. Create path is the Quick-add FAB (T-069).
- No new recurring override logic. The accordion reuses the existing override table.

## Step-by-step

1. **Model the view enum.** `ViewKind = Literal["actual", "planned", "recurring"]` in `web/ledger_types.py`. Validate `view` query param against the enum; invalid values 400 or fall back to `actual`.
2. **Compose filters.** Define `LedgerFilters` as a `frozen=True` dataclass (date_from, date_to, category_ids, account_ids, direction, search, page, page_size). Parse once from `request.query_params`; pass to the per-view repository call.
3. **Dispatch.** In `GET /ledger/table`:
   ```python
   match view:
       case "actual":    rows = repositories.transactions.list_transactions(filters)
       case "planned":   rows = repositories.planned.list_planned(filters.with_promoted(None))
       case "recurring": rows = repositories.recurring.list_recurring(filters)
   ```
4. **Segmented control.** Three buttons with `data-view="actual|planned|recurring"`, `hx-get="/ledger/table?view=…"` + current filter params, `hx-target="#ledger-table"`, `hx-push-url="true"` (reflect view in URL). Active button carries `aria-pressed="true"`. Keyboard: T-068's listener binds `[` to previous view and `]` to next view by reading `data-view` from the control.
5. **Promote modal (planned view).** Reuse existing `_promote_modal.html`. The row's Promote button HTMX-swaps the modal into `#modal-root`; on submit, the modal emits `HX-Trigger: txn-created, planned-stale`. The Panel C listener on Overview and the Ledger table pick these up.
6. **Overrides accordion (recurring view).** `<details><summary>Overrides…</summary><table>…</table></details>`. On expand, HTMX fetches the override list for that rule (`/recurring/{id}/overrides`). No new router here if that endpoint already exists.
7. **Alias old fragment routes.** Return `RedirectResponse(status_code=307, url=…)` from `/transactions/table`, `/planned/table`, `/recurring` list. HTMX follows 307s. Tests confirm the response bytes after redirect match the new endpoint's output.
8. **Search debounce.** `hx-trigger="input changed delay:400ms"` on the search `<input>`. `change, submit` triggers the broader form.

## Validation / acceptance

- `GET /ledger` returns 200 and defaults to `view=actual` (visible via `aria-pressed="true"` on the Actual button).
- `GET /ledger?view=planned` renders the Promoted column + Promote button in each row.
- `GET /ledger?view=recurring` renders Cadence + Next due columns + collapsed Overrides accordion per row.
- `GET /ledger/table?view=actual&date_from=2026-10-01&date_to=2026-10-31` returns only transactions in that window.
- Integration test `tests/integration/web/test_ledger.py`:
  - `test_default_view_is_actual`
  - `test_segmented_control_cycles_view_param`
  - `test_filter_form_submits_as_fragment` (uses `hx-get`, response has no `<html>` wrapper)
  - `test_search_debounce_attribute_present`
  - `test_promote_button_targets_modal_root`
  - `test_overrides_accordion_present_in_recurring_view`
  - `test_alias_routes_return_same_bytes`: `GET /transactions/table?…` after redirect-follow equals `GET /ledger/table?view=actual&…`; same for planned and recurring.
- Keyboard: pressing `]` while on `/ledger?view=actual` cycles the control to `planned` (asserted via Playwright in T-071).

## Risks & gotchas

- **Alias storm.** Scripts (and any user bookmarks of fragment URLs) still hit the old paths. Keep aliases through one release; the Phase 7 cleanup task removes them.
- **View-specific columns in one template.** If the `{% if view == %}` branches start sprawling, split `_table.html` into `_row_actual.html` / `_row_planned.html` / `_row_recurring.html` and include per row. Decide before line 150 of the shared template.
- **Filter form submits full-page vs fragment.** The default `<form>` submit must call `hx-get`, not navigate. Confirm by removing JS and verifying `method="get"` + `action="/ledger/table"` works as a progressive-enhancement fallback.
- **`hx-push-url="true"` on view switch** keeps the back button useful; make sure the filter form doesn't push a new history entry for every keystroke (`hx-push-url="false"` on the search input swap).
- **Pagination resets** on filter change. Reset `page=1` whenever filters change; keep `page` on view switch (same filter context).
- **Search substring.** The repository already does `LIKE %q%`; keep it case-insensitive. Guard against SQL injection via parameters (we do; the repos use parameterised queries per ADR-0019 helpers).

## Handoff notes

- Hand-off to T-068: the segmented control's `data-view` attrs + the `[` / `]` bindings live in `static/js/shortcuts.js`. Don't hard-code the view list there; discover it from DOM.
- Hand-off to T-069: FAB on `/ledger?view=planned` opens the planned form; on `/ledger?view=recurring` opens the recurring rule form; on actual (or any other page) opens the actual form. The FAB reads `view` from `request.url` server-side when rendering `data-add-kind`.
- Hand-off to T-070: page-level redirects for `/transactions`, `/planned`, `/recurring` → `/ledger?view=…` are added in T-070's router updates.
- Commit shape: `feat(T-064): /ledger — unified table + segmented control + fragment dispatch + aliases`.
