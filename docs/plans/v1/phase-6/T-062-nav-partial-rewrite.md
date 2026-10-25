# T-062 — Nav Partial Rewrite

> Phase 6 — UX redesign. Status: pending.

## Purpose

Rewrite `partials/_nav.html` as the 4-item left rail defined in ADR-0023. Four primary items (Overview, Ledger, Accounts, Budget) plus a Settings affordance pinned to the bottom of the rail. Active page gets an accent 2 px left-border and `aria-current="page"`. Each item carries a `data-shortcut` attribute so T-068's command-palette and shortcut listener can discover them without a hard-coded map.

## Inputs / prerequisites

- Upstream tasks: T-061 (shell refactor landed; rail column exists).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — defines the 4-item IA, keyboard shortcuts, Settings de-promoted into the rail footer.
- Adjacent standards: T-053 tokens, `rules/web/coding-style.md` (semantic HTML first), `rules/web/design-quality.md` (hover/focus/active states must feel designed).
- Current nav: `src/budget_planner/web/templates/partials/_nav.html` — horizontal top nav with 9 items. This file is fully rewritten.

## Deliverables

Updated files:

- `src/budget_planner/web/templates/partials/_nav.html` — rewritten.
  - `<nav aria-label="Primary">` wrapping a vertical `<ul>` with 4 `<li>`s + a trailing footer section containing Settings.
  - Each item is an `<a href="…">` with:
    - `aria-current="page"` when the current path matches (use the `request.url.path` provided by FastAPI; a small helper on `request.state` or a Jinja global is fine).
    - `data-shortcut` attribute: `g o` / `g l` / `g a` / `g b` / `g s`.
    - `data-nav-id` for stable targeting (e.g. `overview`, `ledger`, `accounts`, `budget`, `settings`).
  - Settings is a `<button type="button" data-open-drawer="settings">` not a link — it opens the drawer owned by T-067 and does not navigate.
- `src/budget_planner/web/templates/base.html` — only if the rail wrapper markup needs adjusting after the rewrite (likely no change; T-061 already created the column).
- `src/budget_planner/web/static/css/components.css` — append:
  - `.rail-item` base + `:hover` (`background: var(--color-surface-raised)`) + `:focus-visible` (focus-ring from T-052) + `[aria-current="page"]` (2 px solid `var(--color-accent)` left border, no background shift).
  - `.rail-shortcut` for the right-aligned keystroke label (mono, `--text-xs`, `--color-text-faint`).

Not deliverables:

- No shortcut listener JS — owned by T-068.
- No drawer injection — owned by T-067. The `data-open-drawer` attribute is the hand-off contract only.

## Step-by-step

1. **Model the items as data.** Define a `NAV_ITEMS` list in a Jinja global or in a small `web/nav.py` module:
   ```python
   NAV_ITEMS = [
       NavItem(id="overview", label="Overview", path="/",         shortcut="g o"),
       NavItem(id="ledger",   label="Ledger",   path="/ledger",   shortcut="g l"),
       NavItem(id="accounts", label="Accounts", path="/accounts", shortcut="g a"),
       NavItem(id="budget",   label="Budget",   path="/budget",   shortcut="g b"),
   ]
   ```
   `NavItem` is a `frozen=True` dataclass per ADR-0021. Register in the Jinja env as `nav_items`.
2. **Rewrite `_nav.html`.**
   ```jinja
   <nav aria-label="Primary" class="rail">
     <ul>
       {% for item in nav_items %}
         <li>
           <a href="{{ item.path }}"
              class="rail-item"
              data-nav-id="{{ item.id }}"
              data-shortcut="{{ item.shortcut }}"
              {% if request.url.path == item.path or (item.path != '/' and request.url.path.startswith(item.path)) %}aria-current="page"{% endif %}>
             <span class="rail-item__label">{{ item.label }}</span>
             <span class="rail-shortcut">{{ item.shortcut }}</span>
           </a>
         </li>
       {% endfor %}
     </ul>
     <footer class="rail__footer">
       <button type="button"
               class="rail-item"
               data-nav-id="settings"
               data-shortcut="g s"
               data-open-drawer="settings"
               aria-label="Open settings">
         <span class="rail-item__label">⚙ Settings</span>
         <span class="rail-shortcut">g s</span>
       </button>
     </footer>
   </nav>
   ```
3. **Current-page highlight.** Prefer an exact match for `/`, prefix match for the other three (e.g. `/accounts/42` still highlights Accounts). Capture that logic once in a Jinja test or filter (`is_current`) to avoid repeating the ternary.
4. **Reduced-motion.** The hover transition on `background` is instant on `prefers-reduced-motion: reduce`; T-053's existing media query already handles this — no new CSS branch needed.
5. **Register `nav_items` in the Jinja environment.** Add to `src/budget_planner/web/templating.py` (or wherever `Jinja2Templates(…)` is wired) once; routers inherit it automatically.

## Validation / acceptance

- Unit test: `tests/unit/web/test_nav.py::test_nav_items_shape` asserts the 4 primary items + settings item exist with the correct `id`, `path`, `shortcut`.
- Integration test: `tests/integration/web/test_nav.py::test_aria_current_on_current_route` navigates to `/`, `/ledger`, `/accounts`, `/budget` and asserts the matching rail item carries `aria-current="page"` and the others don't.
- Integration test: `test_data_shortcut_attributes_render` asserts every rail anchor has a `data-shortcut` attribute with the expected keystroke.
- Visual: left rail renders 4 items in order (Overview, Ledger, Accounts, Budget), with Settings pinned to the bottom. Current item has the 2 px accent left-border; others don't.
- `grep` guard: no hard-coded palette inside `_nav.html` — all colours come from `--color-*` via `components.css`.
- Design-quality check: this surface shows (1) scale contrast (label vs mono shortcut), (2) rhythm (vertical cadence from `--space-*`), (4) typography pairing (sans label + mono keystroke), (6) hover/focus/active states — four of ten, pass.

## Risks & gotchas

- **Prefix match for `/`** needs the `item.path != '/'` guard, otherwise every page highlights Overview.
- **Settings is not a link.** Don't give it `href`; a button opens the drawer. `aria-current` does not apply to buttons.
- **Shortcut collisions.** `g s` is Settings, not "search". T-068 wires `/` for search. Don't let both bind the same key.
- **Rail footer vs sticky.** `rail__footer` should be `margin-top: auto;` in a column flex container — pinning via CSS, not JS.
- **Icon in Settings label.** The `⚙` glyph is a Unicode fallback; if an SVG icon set lands later (not in Phase 6), swap it then. Keep the Unicode as a working baseline.

## Handoff notes

- Hand-off to T-068: `data-shortcut` on each rail item is the single source of truth. The palette reads these attrs to populate its NAVIGATE section — do not duplicate the keystroke map in JS.
- Hand-off to T-067: `data-open-drawer="settings"` on the Settings button is the contract; T-067's drawer JS listens for click + `g s` and swaps the drawer fragment into `#drawer-root`.
- Commit shape: `feat(T-062): rail nav rewrite — 4 items + settings affordance + shortcut data attrs`.
