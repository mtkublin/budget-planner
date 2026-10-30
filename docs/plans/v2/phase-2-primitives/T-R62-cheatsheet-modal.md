# T-R62 — `?` cheatsheet modal

- **Phase**: 2 — Primitives
- **Parallel-safe**: yes.
- **Depends on**: T-R10, T-R64 (triggers it on `?`).
- **References**: ADR-0056 §9, handoff §Keyboard, ADR-0051 §1.

## Context

A keyboard-first app needs a discoverable shortcut reference. `?` opens a modal listing every active shortcut. On mobile, the modal is reachable from Settings (no `?` keybinding at touch).

## Deliverables

- `src/budget_planner/web/templates/_partials/components/_cheatsheet.html`:
  - Modal shell (uses existing `partials/_slideover.html` or a new `_modal.html` depending on existing primitives).
  - Grouped shortcut list: Navigation · Ledger tabs · Actions · Overlays.
  - Each row: label + `<kbd>` glyphs.
- `GET /cheatsheet` returns the modal fragment; HTMX swaps into `#modal-root`.
- Constants export in `static/js/shortcuts-constants.js` imported by both `shortcuts.js` (T-R64) and the template helper so the printed labels never drift from the dispatch table.
- Settings mobile link ("Keyboard shortcuts") added to T-R55 scope.
- Visual-regression baseline for `/dev/components#cheatsheet`.

## Acceptance criteria

- `?` from any desktop route opens the modal with focus trapped and Esc dismissing it.
- Modal lists every chord + single-key shortcut currently handled by `shortcuts.js`.
- Drift between `shortcuts.js` dispatch table and modal content is impossible — both consume the constants export (test asserts).
- Mobile Settings page has a "Keyboard shortcuts" row that opens the same modal.

## Validation hook

```sh
pytest tests/e2e/test_cheatsheet.py && \
  curl -sS http://localhost:8000/cheatsheet | grep -c "<kbd>" | awk '{ exit $1 < 10 }'
```

## Risks & gotchas

- Modal must not render over the top of the toast root; `z-index` ordering: toast > modal > drawer.
- Chord shortcuts render as two `<kbd>` elements with a space (e.g. `<kbd>g</kbd> <kbd>o</kbd>`).

## Handoff notes

- T-R64 fires the open event; this task owns the content + render.
- The constants export becomes the single source for both the dispatch and the help display; keep it tested.
