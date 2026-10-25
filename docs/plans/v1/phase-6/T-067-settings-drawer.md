# T-067 — Settings Drawer

> Phase 6 — UX redesign. Status: pending.

## Purpose

Introduce a right-side slide-over Settings drawer with three internal tabs (Categories, FX, Preferences). Categories CRUD is lifted from the current `/categories` page verbatim. FX is a read-only list of cached rates. Preferences is a read-only view of base currency + display timezone (per ADR-0006 and ADR-0007; editing is a v2 concern). The drawer is a persistent `#drawer-root` consumer — HTMX injects the fragment HTML, no new URL in the browser bar.

## Inputs / prerequisites

- Upstream tasks: T-061 (shell + `#drawer-root` slot).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — drawer pattern, three tabs, 480 px wide.
- Adjacent standards: ADR-0006 (multi-currency), ADR-0007 (timezones), T-053 tokens.
- Existing surfaces (lift):
  - `src/budget_planner/web/routers/categories.py` + templates — stays for one release (T-070 redirects `/categories` to the drawer open state).
  - `repositories.fx.list_recent(limit=50)` — recent cached FX rates.
  - `repositories.settings.get()` — current base currency + timezone.

## Deliverables

New files:

- `src/budget_planner/web/routers/settings.py`:
  - `GET /settings?tab=categories|fx|prefs` — returns the drawer fragment HTML with the requested tab active.
  - `GET /settings/categories/table` — the categories list fragment (reuses current list renderer).
  - `POST /settings/categories` — delegates to the existing category create handler.
  - `PATCH /settings/categories/{id}` + `DELETE /settings/categories/{id}` — same.
  - Fragment responses only; no full-page shell.
- `src/budget_planner/web/templates/settings/_drawer.html` — the drawer shell with:
  - `<aside class="drawer" role="dialog" aria-modal="true" aria-label="Settings" tabindex="-1">`.
  - Tab bar with three `<button role="tab">`s (`aria-selected`, `aria-controls`).
  - Close button (`aria-label="Close settings"`), responds to click + Esc (Esc handled by overlay-stack in T-071).
- `src/budget_planner/web/templates/settings/_categories.html` — lifted from current categories templates.
- `src/budget_planner/web/templates/settings/_fx.html` — read-only table: pair · as-of date · rate.
- `src/budget_planner/web/templates/settings/_prefs.html` — read-only labels: `Base currency: {{ settings.base_currency }}` · `Display timezone: {{ settings.display_timezone }}` + a note "editable in a future release".

Updated files:

- `src/budget_planner/web/templates/partials/_nav.html` (owned by T-062) already has `data-open-drawer="settings"` on the Settings button; wire the client listener in `static/js/shortcuts.js` (owned by T-068) to call:
  ```js
  htmx.ajax("GET", "/settings?tab=categories", { target: "#drawer-root", swap: "innerHTML" })
  ```
- `src/budget_planner/web/static/css/components.css` — append `.drawer` + `.drawer--open` + reduced-motion branch.

Not deliverables:

- No new category model, repository, or validation changes.
- No FX ingestion changes.
- No preference editing (v2).

## Step-by-step

1. **Route and schema.** In `settings.py`, define `TabKind = Literal["categories", "fx", "prefs"]`. `GET /settings?tab=…` renders `settings/_drawer.html` with `active_tab=tab` in context; invalid tabs 400.
2. **Drawer shell.**
   ```jinja
   <aside class="drawer drawer--open" role="dialog" aria-modal="true" aria-label="Settings" tabindex="-1">
     <header class="drawer__header">
       <h2>Settings</h2>
       <button type="button" aria-label="Close settings" data-close-drawer>×</button>
     </header>
     <nav role="tablist" aria-label="Settings tabs">
       {% for tab in [("categories","Categories"), ("fx","FX"), ("prefs","Preferences")] %}
         <button role="tab"
                 id="tab-{{ tab[0] }}"
                 aria-selected="{{ 'true' if active_tab == tab[0] else 'false' }}"
                 aria-controls="panel-{{ tab[0] }}"
                 hx-get="/settings?tab={{ tab[0] }}"
                 hx-target="#drawer-root"
                 hx-swap="innerHTML">{{ tab[1] }}</button>
       {% endfor %}
     </nav>
     <section id="panel-{{ active_tab }}" role="tabpanel" aria-labelledby="tab-{{ active_tab }}">
       {% include "settings/_" ~ active_tab ~ ".html" %}
     </section>
   </aside>
   ```
3. **Categories tab.** Lift the content of `templates/categories/index.html` into `templates/settings/_categories.html`. All form actions post to the new `/settings/categories*` endpoints, which delegate to the existing service. The old `/categories` page remains until T-070 redirects it.
4. **FX tab.** Table with headers `Pair · As-of · Rate`. Rows from `repositories.fx.list_recent(limit=50)`. Add an eyebrow note: `rates are cached; refresh runs on application start.` Read-only.
5. **Preferences tab.** Static read-only key-value list. The "future release" note links to the roadmap (`docs/plans/v1/`).
6. **Keyboard.** T-068 binds `g s` to the drawer open action (same `htmx.ajax` call as the Settings button).
7. **Close affordances.** Click outside (`.drawer-backdrop`) + Esc + the `×` button. Esc is routed by T-071's overlay-stack so modals above the drawer absorb Esc first.
8. **Focus trap.** Owned by T-071. T-067 only guarantees the drawer root has `tabindex="-1"` so the overlay-stack can focus it on open.
9. **Reduced motion.** Default: 220 ms slide-in via `transform: translateX(100%)` → `translateX(0)`. Under `prefers-reduced-motion: reduce`, swap to instant open.

## Validation / acceptance

- `GET /settings?tab=categories` returns a fragment containing a `<aside role="dialog">` with `aria-label="Settings"`.
- `GET /settings?tab=fx` renders the FX table (asserts at least a `<table>` with a `<thead>`).
- `GET /settings?tab=prefs` renders base currency and timezone from `settings.get()`.
- Clicking a tab inside the drawer HTMX-swaps the drawer content with `aria-selected="true"` on the clicked tab.
- Integration test `tests/integration/web/test_settings_drawer.py`:
  - `test_each_tab_renders`
  - `test_category_crud_from_drawer` — create, patch, delete through `/settings/categories*`; the categories list refreshes.
  - `test_fx_tab_is_read_only` — no form posts rendered.
  - `test_prefs_tab_is_read_only`.
- Keyboard `g s` opens the drawer (asserted via Playwright in T-071).
- No new palette values.

## Risks & gotchas

- **Dual sources of truth** for categories (`/categories` and `/settings/categories`) during the alias period. Both call the same service — the templates are the only duplicate. Keep until T-070 cleanup.
- **Drawer content is CSP-sensitive.** No inline `<script>`; shortcut wiring lives in `shortcuts.js` only.
- **FX rate "as-of" format.** Use the display timezone from settings (Europe/Warsaw default per ADR-0007). Dates in DB are naive; convert on render.
- **Drawer + modal coexistence.** The Promote modal (Ledger) can open on top of the drawer. The overlay-stack rule (T-071) ensures only the topmost responds to Esc. Keep the drawer `role="dialog" aria-modal="true"` — the stack handles aria-hidden on background content.
- **URL ergonomics.** The drawer deliberately does **not** change the URL. `g s` from any page opens the drawer in-place; closing restores whatever page they were on. If deep-linkability is wanted later, add `?settings=categories` as a progressive-enhancement query param (defer).

## Handoff notes

- Hand-off to T-068: the `g s` keystroke binds to `htmx.ajax("GET", "/settings?tab=categories", { target: "#drawer-root", swap: "innerHTML" })`. The palette's `Open Settings` row triggers the same call.
- Hand-off to T-070: `/categories` → 302 to `/` with a flash "Categories moved to Settings → Categories". Alternatively, `/categories` → open drawer client-side by returning a page that triggers `g s` on load — but the simpler 302 is preferred.
- Hand-off to T-071: focus trap, Esc behaviour, reduced-motion branch, and overlay-stack ownership all land here.
- Commit shape: `feat(T-067): settings drawer — categories (lifted), FX read-only, prefs read-only`.
