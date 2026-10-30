# T-R51 — Mobile tab bar

- **Phase**: 6 — Responsive
- **Sequential**: first mobile task.
- **Depends on**: Phase 3 screens green.
- **References**: ADR-0055 §2, handoff mobile screens 1o–1t.

## Context

At ≤ 640 px the sidebar collapses and primary navigation moves to a bottom tab bar with four tabs plus a centre `+ Add` button. Settings is reached from the Today page header on mobile (gear icon, top-right) — the tab bar does not expand to accommodate a fifth slot.

## Deliverables

- `templates/_partials/_tab_bar.html` rendered inside the `base.html` footer slot (added as a stub in T-R04):
  - Four `<a>` tabs: Today · Ledger · Plan · Accounts.
  - Centre `<button>` for `+ Add` opens the bottom sheet (T-R52).
  - Each tab shows an eyebrow label (uppercase 10 px).
- `static/css/components/tab-bar.css`:
  - `position: fixed; bottom: 0;` with hairline top border.
  - Grid with five equal columns; centre column (Add) raised 2 px via transform.
  - Hidden at `width >= 641px`.
  - Tap targets ≥ 44 px (ADR-0055 §2).
- Settings gear icon in the Today page header, visible only at ≤ 640 px (`.icon-only-sm` utility).
- Visual-regression baselines at 375 px covering every v2 route render the tab bar; sidebar is hidden.

## Acceptance criteria

- At 375 px, every v2 route shows the tab bar; sidebar not rendered.
- At 1024 px (tablet), the top bar is shown; tab bar hidden.
- At 1440 px (desktop), the sidebar is shown; tab bar hidden.
- `getComputedStyle(tabBar).height >= 56` px at 375 px (44 px tap + padding).
- Settings reachable via gear icon on Today header at ≤ 640 px.
- `frontend-visual-audit` on `/today` at 375 px returns zero `horizontalScroll`.

## Validation hook

```sh
just test-visual --filter tab-bar && \
  invoke frontend-visual-audit at 375 against /today /ledger /plan /accounts
```

## Risks & gotchas

- Fixed-bottom bars can occlude content when the on-screen keyboard appears. Add `env(safe-area-inset-bottom)` padding so iOS devices do not clip the Add button.
- The `+ Add` button must *not* submit a form; it opens the sheet. Mark it `type="button"`.
- Ensure `main` content has bottom padding equal to the tab bar height so no content is hidden under the bar.

## Handoff notes

- T-R52 wires the `+ Add` button to the bottom sheet shell.
- T-R55 (Settings mobile) picks up the gear icon routing + Settings tab scroll behaviour at narrow widths.
