# T-R64 — Keyboard shortcut map

- **Phase**: 1 — Foundations
- **Parallel-safe**: after T-R06.
- **Depends on**: T-R06, T-R62 (opens the cheatsheet modal on `?`).
- **References**: ADR-0051 §1, ADR-0056 §9, handoff §Keyboard.

## Context

The handoff keyboard section promises `g o`/`g l`/`g p`/`g a`/`g s` navigation, `n` for add, `/` for filter focus, `[ ]` for Ledger tab cycle, `↵` for primary action, `Esc` for top-most overlay close, `?` for the cheatsheet, `⌘K` deferred. v1 has a partial shortcut handler; the v2 shell needs a single consistent module.

## Deliverables

- `src/budget_planner/web/static/js/shortcuts.js` — single module with:
  - Chord state machine for two-key `g {o,l,p,a,s}` sequences (250 ms window).
  - Input-guard: ignore key presses when `event.target` matches `input, textarea, [contenteditable]`.
  - Dispatch table mapping keys to navigation URLs or custom events (`htmx:open-add`, `htmx:open-cheatsheet`, `htmx:focus-filter`, etc.).
  - Esc delegated to the overlay-stack module (existing).
- `base.html` loads it with `defer`.
- `tests/e2e/test_shortcuts.py` covers the chord state machine + input-guard.
- Shortcut dispatch table documented in a comment at the top of `shortcuts.js` so the cheatsheet macro (T-R62) can mirror it.

## Acceptance criteria

- `g o` on `/plan?tab=budget` navigates to `/today`.
- Typing `g` inside an open text input does **not** trigger chord mode.
- `n` from any non-input focus opens the add modal (or the mobile sheet at narrow widths).
- `/` focuses the active page's filter input when one exists.
- `?` opens the cheatsheet modal.
- `⎋` dismisses the top-most overlay without affecting the one below.

## Validation hook

```sh
pytest tests/e2e/test_shortcuts.py
```

## Risks & gotchas

- Input-guard must also respect contenteditable regions (Jinja popover formula inputs may use them).
- `g` + any-other-key timeout must be short enough not to interfere with normal typing after Esc.
- Shortcut names printed in the cheatsheet come from a shared constants export so a drift between the two can't happen.

## Handoff notes

- T-R62 (cheatsheet modal) reads the constants export; keep the export as the single source for shortcut labels.
