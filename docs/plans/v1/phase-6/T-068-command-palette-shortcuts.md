# T-068 — Command Palette + Keyboard Shortcuts

> Phase 6 — UX redesign. Status: pending.

## Purpose

Add a minimal Cmd+K / Ctrl+K command palette plus a global keyboard shortcut map. The palette is a Jinja partial + ~60 lines of vanilla JS. Shortcuts are ~40 lines of vanilla JS. No external library. The palette discovers navigation items from the DOM (`data-shortcut` on rail items, owned by T-062) so there's no duplicated keymap.

## Inputs / prerequisites

- Upstream tasks: T-062 (nav items carry `data-shortcut`), T-061 (`#modal-root` and `{% block scripts %}` present).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — palette + shortcut map.
- Adjacent standards: `rules/web/coding-style.md` (animation-only properties), `rules/web/performance.md` (bundle budget).

## Deliverables

New files:

- `src/budget_planner/web/templates/partials/_palette.html`:
  - `<dialog class="palette" aria-label="Command palette">` or `<div role="dialog" aria-modal="true">` wrapper.
  - Input at top; grouped list below: `NAVIGATE` (built from `[data-shortcut]` elements), `ACTIONS` (new transaction `n`, new planned `N`, reconcile `r`, filter `/`), `JUMP` (per-account + per-category shortcuts rendered server-side).
  - Each item has `data-command` + `data-keystroke`.
- `src/budget_planner/web/templates/partials/_shortcuts.html`:
  - `?` cheatsheet. Static table of key → action rows.
- `src/budget_planner/web/static/js/palette.js` (~60 lines):
  - Opens on `Cmd+K` / `Ctrl+K`. Fetches `/palette` fragment on first open (then caches in-memory).
  - Fuzzy filter on left-column text (substring + simple char-skip).
  - `↑`/`↓` navigate; `Enter` activates the highlighted item; `Esc` closes.
  - Activating a `NAVIGATE` row = `window.location.assign(href)`; `ACTIONS` row = fires the keystroke binding; `JUMP` row = navigates to the deep link.
- `src/budget_planner/web/static/js/shortcuts.js` (~40 lines):
  - Global keydown listener on `document`.
  - Guards against capturing when the active element is `INPUT`, `TEXTAREA`, or `[contenteditable]`.
  - Bindings:
    - `g o/l/a/b/s` (chord: `g` then next key within 1500 ms) — navigate to the corresponding nav item (read from `[data-shortcut]`).
    - `n` — open the FAB slide-over (dispatch `click` on the FAB).
    - `/` — focus the active page's `[data-search]` input (Ledger search, else no-op).
    - `[` / `]` — cycle Ledger segmented control via `[data-view]` discovery.
    - `?` — open shortcut cheatsheet (`htmx.ajax` the partial into `#modal-root` or inline toggle a `<dialog>`).
    - `Esc` — close the topmost overlay (delegated to `overlay-stack.js`, T-071).
- `src/budget_planner/web/static/js/overlay-stack.js` (~30 lines) — owned by T-071; T-068 depends on it existing by Esc wiring. If T-071 hasn't landed yet, T-068 ships a stub (one-overlay-at-a-time, closes the topmost) and T-071 generalises.
- `src/budget_planner/web/routers/palette.py` (or add to `home.py`):
  - `GET /palette` — returns `_palette.html` fragment with server-rendered JUMP rows (accounts + categories).

Updated files:

- `src/budget_planner/web/templates/base.html` — in `{% block scripts %}`, append:
  ```html
  <script src="{{ url_for('static', path='js/overlay-stack.js') }}" defer></script>
  <script src="{{ url_for('static', path='js/palette.js') }}" defer></script>
  <script src="{{ url_for('static', path='js/shortcuts.js') }}" defer></script>
  ```

Not deliverables:

- No external npm packages (local-first, no build step).
- No framework (React / Vue / Alpine).

## Step-by-step

1. **Palette partial.** Server-render the NAVIGATE section as a static list; ACTIONS from a hard-coded array in the template; JUMP from `accounts` + `categories` passed in route context. Each `<li>` has `data-label`, `data-command`, and either `data-href` (NAVIGATE / JUMP) or `data-keystroke` (ACTIONS).
2. **`palette.js` state.**
   - `state = { open: false, items: [], filter: "", cursor: 0 }`.
   - `openPalette()` fetches `/palette` once, injects into a dedicated `#palette-root` sibling of `#modal-root` (added in `base.html` under T-068, or reuse `#modal-root` if T-071 agrees).
   - `onInput()` updates `state.filter`, re-renders highlighted matches, resets `state.cursor = 0`.
   - `onKeydown()` handles `↑`/`↓`/`Enter`/`Esc`.
   - `activate(item)` dispatches based on `data-command` kind.
3. **Fuzzy match.** Minimal: substring on lowercased `data-label`, then a secondary pass where characters appear in order (not required to be contiguous). Score by first match position; stable sort. ~15 lines of JS.
4. **`shortcuts.js` chord handling.** `g` sets `pendingChord = { prefix: "g", expiresAt: now + 1500 }`. Next key within window combines; else chord expires. Listener filters out any keydown originating in an input (per the "guard" standard pattern — `rules/web/design-quality.md` / `coding-style.md`).
5. **`?` cheatsheet.** Render `_shortcuts.html` with a two-column table. Open via `?` key; close via Esc or click-outside. Mount into `#modal-root`.
6. **Reduced motion.** Palette uses `transform: translateY(-8px)` → `translateY(0)` + `opacity` fade. Under `prefers-reduced-motion: reduce`, no transition — instant swap.
7. **Discoverability.** The ADR-0023 note about "no hard-coded keymap" is enforced: `shortcuts.js` reads `[data-shortcut]` from the rail at startup. Changing a shortcut in the Jinja nav flows through automatically.

## Validation / acceptance

- `GET /palette` returns a fragment that includes a NAVIGATE section with 5 items (Overview, Ledger, Accounts, Budget, Settings) — assertion checks `data-shortcut` matches.
- Playwright test `tests/e2e/test_palette.py`:
  - Opens `/`, presses `Cmd+K` (or `Control+K` on headless Chromium), asserts the palette becomes visible.
  - Types `ledger`, asserts `Go to Ledger` is highlighted.
  - Presses `Enter`, asserts URL is now `/ledger`.
  - Presses `Esc`, asserts palette is hidden.
- Playwright `tests/e2e/test_shortcuts.py`:
  - `g l` navigates to `/ledger`.
  - `/` on `/ledger` focuses the search input.
  - `[`, `]` cycle the ledger segmented control.
  - Typing inside the search input does **not** fire the chord (guarded).
  - `?` opens the cheatsheet; `Esc` closes it.
- `wc -l src/budget_planner/web/static/js/palette.js` ≤ 90 (allow 60 target + 30 slack).
- `wc -l src/budget_planner/web/static/js/shortcuts.js` ≤ 70.
- Bundle budget: three scripts total < 15 KB uncompressed.

## Risks & gotchas

- **Capturing keys inside form fields** breaks typing. The guard must check `tagName`, `isContentEditable`, and `type === "text" | "email" | …`. Standard pattern.
- **`Cmd+K` on macOS** is sometimes claimed by browser chrome. The listener should call `event.preventDefault()` on match, but confirm Safari behaviour — it may require tracking the composition state.
- **Palette fragment stale** when a new account or category is added. Invalidate the in-memory cache on `HX-Trigger: account-created` / `category-created` HTMX events; refetch on next open.
- **ADA conflict** with `?` key: in some assistive tech, `?` is reserved. Document and leave as-is; it's inert if focus is in a text input.
- **Chord expiry.** 1500 ms is generous; too short confuses users. Keep configurable via a top-level constant in `shortcuts.js`.
- **Esc behaviour must respect overlay stack.** If a modal is open on top of the palette, Esc closes the modal first — T-071 provides the stack. The initial T-068 shipping can be single-overlay; T-071 generalises.

## Handoff notes

- Hand-off to T-069: `n` key dispatches `document.querySelector("[data-fab]").click()`. T-069 owns the FAB and the slide-over form.
- Hand-off to T-071: focus trap inside the palette, Esc stacking, reduced-motion branch verification.
- Commit shape: `feat(T-068): command palette + global keyboard shortcuts (~100 lines vanilla)`.
