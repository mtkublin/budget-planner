# T-069 — Quick-add FAB

> Phase 6 — UX redesign. Status: pending.

## Purpose

Add a fixed bottom-right 56×56 accent floating action button with a `+` glyph, `aria-label="Add"`, that opens a slide-over form scoped to the current context: actual transaction on Overview / Accounts, planned on `/ledger?view=planned`, recurring rule on `/ledger?view=recurring`. The `n` key opens the same slide-over. On submit, HTMX fires one of `txn-created` / `planned-created` / `recurring-created` so the Overview panels and Ledger table re-fetch their fragments.

## Inputs / prerequisites

- Upstream tasks: T-061 (shell + `{% block fab %}`), T-064 (ledger `view` param defined).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — FAB placement, context routing, HTMX event names.
- Adjacent standards: T-053 tokens; `rules/web/coding-style.md` (semantic HTML + animate transform/opacity only).
- Existing forms (reuse):
  - `partials/_form.html` + the actual-transaction create handler (likely `POST /transactions`).
  - `POST /planned` for planned.
  - `POST /recurring` for recurring rules.

## Deliverables

New files:

- `src/budget_planner/web/templates/partials/_fab.html`:
  ```jinja
  <button type="button"
          class="fab"
          data-fab
          data-add-kind="{{ add_kind }}"
          aria-label="Add"
          hx-get="/quick-add?kind={{ add_kind }}"
          hx-target="#modal-root"
          hx-swap="innerHTML">+</button>
  ```
- `src/budget_planner/web/templates/partials/_quick_add.html`:
  - Slide-over panel with the appropriate form for the current `kind`. Reuses `_form.html` field markup; form `hx-post`s to the corresponding endpoint and emits an `HX-Trigger` response header on success.
- `src/budget_planner/web/routers/quick_add.py`:
  - `GET /quick-add?kind=actual|planned|recurring` — returns the slide-over fragment with the right form.
- `src/budget_planner/web/static/css/components.css` — append:
  - `.fab` — position fixed bottom + right using `--space-6` offsets, 56 × 56, border-radius `--radius-pill`, `background: var(--color-accent)`, `color: var(--color-text-on-accent)`, `box-shadow: var(--elevation-2)`, hover `transform: translateY(-1px)`, focus-visible ring from T-052.
  - `.quick-add` — slide-over right panel, 420 px wide, slide-in from right (transform + opacity).

Updated files:

- `src/budget_planner/web/routers/home.py` and other base-rendering routers — add a Jinja context helper `add_kind_for(request)` that returns:
  - `"planned"` if `request.url.path == "/ledger"` and `request.query_params.get("view") == "planned"`.
  - `"recurring"` if path is `/ledger` and view is `recurring`.
  - `"actual"` otherwise.
  - Register as a Jinja global so `_fab.html` can read `add_kind` without plumbing it through every router.
- `src/budget_planner/web/templates/base.html`:
  - `{% block fab %}{% include "partials/_fab.html" with add_kind=add_kind_for(request) %}{% endblock %}` (or render via the global and keep the include simpler).

Not deliverables:

- No new domain services or validation. The three POST endpoints exist.
- No reconcile integration (reconcile is a card-level affordance in T-065).

## Step-by-step

1. **Context helper.** Add `web/context.py::add_kind_for(request) -> AddKind` where `AddKind = Literal["actual", "planned", "recurring"]`. Pure function. Register in Jinja globals.
2. **FAB markup.** Single button in `_fab.html`. `data-fab` is the selector `shortcuts.js` uses to simulate click on `n`. `aria-label="Add"` is the only accessible name — the `+` glyph is decorative.
3. **Slide-over.** `_quick_add.html` renders a `<aside class="quick-add" role="dialog" aria-modal="true" aria-labelledby="qa-title" tabindex="-1">`. Inside, a title (`New transaction` / `New planned` / `New recurring rule`), the form fields from `_form.html`, Cancel + Save buttons.
4. **Form targets per kind.**
   - `actual` → `POST /transactions`. On success, response includes `HX-Trigger: txn-created`.
   - `planned` → `POST /planned`. `HX-Trigger: planned-created, planned-stale`.
   - `recurring` → `POST /recurring`. `HX-Trigger: recurring-created`.
5. **Listeners.** The Overview Panel C already listens for `txn-created, planned-stale`. The Ledger table listens for all three (added via `hx-trigger` on the table container):
   ```jinja
   <section id="ledger-table"
            hx-get="/ledger/table?view={{ view }}&{{ filter_qs }}"
            hx-trigger="txn-created from:body, planned-created from:body, recurring-created from:body, planned-stale from:body"
            hx-swap="innerHTML">…</section>
   ```
6. **Keyboard `n`.** `shortcuts.js` (T-068) binds `n` to `document.querySelector("[data-fab]").click()`.
7. **Reduced motion.** Slide-in via `transform: translateX(100%)` → `translateX(0)` with 220 ms; `prefers-reduced-motion` branch to instant.
8. **Close affordances.** Cancel button, `×` button, click outside backdrop, Esc (routed via overlay-stack per T-071).

## Validation / acceptance

- `GET /` renders a visible FAB inside `{% block fab %}`.
- `GET /ledger?view=planned` renders the FAB with `data-add-kind="planned"`.
- `GET /quick-add?kind=actual|planned|recurring` returns the right slide-over fragment with the matching form action.
- Integration test `tests/integration/web/test_quick_add.py`:
  - `test_fab_present_on_primary_pages` for `/`, `/ledger`, `/accounts`, `/budget`.
  - `test_add_kind_matches_route`: `/ledger?view=planned` → `data-add-kind="planned"`.
  - `test_submit_fires_htmx_trigger_header`: POST a transaction, assert `response.headers["HX-Trigger"]` contains `txn-created`.
- Playwright `tests/e2e/test_fab_flow.py`:
  - Click FAB on `/`, submit a transaction, assert the Panel C fragment re-fetched (asserts a request to `/overview/upcoming?window=…`) and the new row is visible.
  - Press `n` on `/ledger?view=planned`, assert the slide-over opens with the planned form, submit, assert the ledger table refreshes.
- `n` key does not fire while a text input is focused (asserted in T-068).

## Risks & gotchas

- **Overlapping overlays.** FAB-opened slide-over + a modal + the drawer can coexist. The overlay-stack rule (T-071) governs Esc.
- **Context mismatch.** If a user is on `/accounts/42` (deep account page) and presses `n`, the context helper returns `actual`. That is intended — accounts don't have a planned-transaction concept here.
- **Mobile FAB** can obscure a Save button at the bottom of a form on narrow viewports. Phase 6 is desktop-first; no responsive adaptation required for the FAB in v1.
- **`HX-Trigger` header case.** HTMX reads it case-insensitively but FastAPI responses must set exactly `HX-Trigger` to be consistent. Centralise in a response helper.
- **Form reset on open.** The slide-over is fetched fresh on each open (no in-memory cache), so form state defaults are clean.
- **Submission failure.** If the POST returns 4xx, the slide-over must stay open and show inline errors (owned by T-051 patterns already). Do not auto-close on failure.

## Handoff notes

- Hand-off to T-068: the `[data-fab]` selector is the single contract. T-068's `n` key uses it.
- Hand-off to T-071: focus trap inside the slide-over, Esc stacking, reduced-motion branch verification.
- Commit shape: `feat(T-069): quick-add FAB + slide-over form with context-aware kind`.
