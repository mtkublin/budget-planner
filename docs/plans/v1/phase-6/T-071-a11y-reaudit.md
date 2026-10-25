# T-071 — Accessibility Re-audit

> Phase 6 — UX redesign. Status: pending.

## Purpose

Follow up T-052 on the new Phase 6 surfaces: left-rail nav, three-panel Overview, Ledger (segmented control + table + modal), Accounts cards (sparkline + disclosure + inline reconcile), Budget page, Settings drawer, Command palette, Quick-add slide-over, FAB, shortcut cheatsheet. Add a "topmost overlay" rule so drawer + modal + palette coexist cleanly: only one responds to Esc at a time; opening a new overlay layers it on top with correct focus trap and `aria-hidden` on the layer below. Rules live in `static/js/overlay-stack.js`.

## Inputs / prerequisites

- Upstream tasks: T-063…T-069 (all new surfaces built).
- Binding standards:
  - T-052 (the Phase 5 a11y baseline — focus-ring token, sr-only tables, reduced-motion media query).
  - [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — overlay coexistence requirement.
  - `rules/web/testing.md` (accessibility testing section).

## Deliverables

New files:

- `src/budget_planner/web/static/js/overlay-stack.js` (~30 lines):
  - Module exports `pushOverlay(el)` and `popOverlay(el)`.
  - Maintains a stack. On push: previous top gets `aria-hidden="true"` + `inert`; new top gets focus (via `el.focus()` after moving tabindex=-1 to the dialog root).
  - On `Esc` keydown: if `document.activeElement` is inside the top overlay, call the top's registered close handler.
  - Guarantees exactly one overlay owns Esc at a time.
- `tests/e2e/test_a11y_overlays.py` — Playwright keyboard-only walk covering: open drawer, open palette on top, Esc closes palette only, Esc closes drawer, focus restored to opener.

Updated files:

- `partials/_drawer.html` (T-067), `partials/_quick_add.html` (T-069), `partials/_palette.html` (T-068), `partials/_promote_modal.html` (existing) — each registers with the overlay stack on open:
  ```js
  overlayStack.push({
    el: dialogEl,
    onClose: () => dialogEl.remove(),
    openerEl: lastFocusedTrigger,
  });
  ```
- `_nav.html` — confirm `aria-current="page"` renders on exactly one item.
- `base.html` — add `defer`-loaded `overlay-stack.js` before `palette.js` + `shortcuts.js` in `{% block scripts %}`.
- `static/css/a11y.css` — add reduced-motion branches for the drawer, palette, and slide-over transitions (`@media (prefers-reduced-motion: reduce) { .drawer, .quick-add, .palette { transition: none !important; } }`).
- `static/css/components.css` — verify colour contrast on new tiles (fortune hero on card, pace tag against card bg, sparkline stroke against card bg); adjust tokens only if a contrast ratio fails WCAG AA.

Not deliverables:

- No new UI surfaces. This task hardens the ones built in T-063…T-069.
- No new ARIA roles beyond `dialog` / `tablist` / `tabpanel` / `tab` already in use.

## Step-by-step

1. **Baseline scan.** Run `axe-core` (via Playwright or the browser extension) on `/`, `/ledger`, `/accounts`, `/budget`, and the drawer + palette + FAB slide-over + Promote modal states. Record violations.
2. **Fix contrast.** For every violation, trace to a token in T-053's `tokens.css`. Adjust the token (not per-component CSS) unless the token is in general-purpose use elsewhere — then introduce a new semantic alias (e.g. `--color-on-raised`) in `tokens.css` and reference it.
3. **Overlay stack.** Build `overlay-stack.js`. API shape above. Register on push, deregister on pop. Esc routing is in this module, not scattered in each overlay's script.
4. **Focus trap.** On push: find all focusable descendants (`a[href], button, input, textarea, select, [tabindex]:not([tabindex="-1"])`). On Tab from the last, wrap to first; Shift-Tab from the first wraps to last.
5. **`aria-hidden` + `inert` on the layer below.** When pushing a second overlay, set `aria-hidden="true"` and `inert` on the previous top. On pop, restore.
6. **Focus restoration.** `pushOverlay({ openerEl })` stores the opener. On pop, `openerEl.focus()` so keyboard users land back where they triggered the overlay.
7. **Reduced-motion.** Append the media query to `a11y.css`. Confirm with devtools emulation (`prefers-reduced-motion: reduce`) that the drawer appears instantly.
8. **ARIA current.** Assert `aria-current="page"` on exactly one rail item per page (integration test).
9. **Playwright keyboard walk.** `tests/e2e/test_a11y_overlays.py`:
   - Navigate to `/`.
   - Press `g s` → drawer opens; `document.activeElement` is inside drawer.
   - Press `Cmd+K` → palette opens on top of drawer; focus is in palette input.
   - Press `Esc` → palette closes; focus returns to drawer.
   - Press `Esc` → drawer closes; focus returns to the Settings button in rail.
   - Repeat for modal-over-drawer (open a Promote modal from Ledger while drawer is open — if possible — or verify in isolation).

## Validation / acceptance

- `axe-core` returns zero new violations on the five primary surfaces (`/`, `/ledger`, `/accounts`, `/budget`, and the open-drawer state of any page).
- `tests/e2e/test_a11y_overlays.py` passes: palette-on-drawer, modal-on-drawer, slide-over-on-page all correctly route Esc and restore focus.
- Integration test `tests/integration/web/test_nav_aria_current.py` asserts exactly one `aria-current="page"` per page load across `/`, `/ledger`, `/accounts`, `/budget`.
- Reduced-motion: devtools emulation shows no slide/fade on drawer, palette, slide-over.
- Colour contrast: every text/background pair on the new surfaces meets WCAG AA (4.5:1 for body text, 3:1 for large text / UI elements).
- `grep -nE 'aria-hidden="true"' src/budget_planner/web/templates/` — only on inert layers; no stray true-set hiding content from AT.

## Risks & gotchas

- **`inert` attribute support.** Modern browsers (Chrome, Firefox, Safari 15.5+) support it. Fall back to a tabindex sweep (`setAttribute("tabindex", "-1")` on every focusable descendant) if inert is missing. Local-first app means owner's browser is modern — the fallback is defensive.
- **Esc from a native dialog** can bubble to the browser (e.g. closing devtools). Call `event.preventDefault()` only when the stack handles it.
- **Focus restoration after HTMX swap.** If an overlay's parent container is swapped by HTMX while the overlay is open, the `openerEl` reference goes stale. Guard: null-check before `focus()`; fall back to the first rail item.
- **Reduced-motion `!important`.** Only use `!important` inside `@media (prefers-reduced-motion: reduce)` to defeat the base transition rule; nowhere else.
- **Multi-tab navigation inside drawer.** The drawer's internal `role="tablist"` has its own Tab semantics (left/right arrows cycle tabs). Make sure the focus trap doesn't swallow the arrow keys.
- **Scope creep.** This is a re-audit, not a redesign. If axe flags something structural (e.g. a heading-level mismatch), fix at the smallest level that passes the check; don't rework the page.

## Handoff notes

- Hand-off to T-072: README gets a "Keyboard & accessibility" subsection that references overlay-stack + the Esc-routing contract.
- `overlay-stack.js` is the long-term home for any future overlay. Modals, drawers, slide-overs, palettes all go through it.
- Commit shape: `feat(T-071): a11y re-audit — overlay stack + focus restoration + reduced-motion + contrast`.
