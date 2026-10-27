# T-090 [S] Shell + rail layout fit

**Phase:** 8 — Post-redesign UX fixes
**Group:** G1
**Depends on:** T-061 (shell), T-062 (rail)
**Size:** S
**Status:** planned

## Scope

Fix two layout defects introduced by the Phase 6 shell:

1. Page-level horizontal scrollbar appears when a child surface (wide ledger / budget rules table) is naturally wider than the grid column. Root cause: `.app-shell__main` is a grid cell with `max-width: 1200px` but no `min-width: 0`, so wide descendants push the whole column.
2. Rail (`.app-shell__rail`) is `height: 100dvh` with `overflow-y: auto`, but internal rhythm (`gap: var(--space-5)`, `padding: var(--space-6) var(--space-4)`) overflows on short viewports (720 px high) and the Settings footer disappears below the fold.

Both are CSS-only.

## Changes

- `src/budget_planner/web/static/app.css`:
  - `.app-shell__main` — add `min-width: 0`.
  - `.app-shell__content` already has `min-width: 0`; leave it.
  - Wrap known-wide tables with `overflow-x: auto` **inside** the surface, not on `main`. Reuses the existing `table.ledger` block: add `.ledger-scroll { overflow-x: auto; }` and wrap in the two templates that render tables wider than 900 px (ledger `_table.html`, budget `index.html` rules section).
  - `.rail-nav` — reduce `gap` to `--space-4`, `padding` to `--space-5 var(--space-4)`. Verify Settings footer visible at 720 px.
  - `.app-shell__rail` — change `height: 100dvh` to `max-height: 100dvh; min-height: 0;` so sticky positioning still works but rail collapses to its intrinsic height on tall viewports.

## Non-goals

- No markup changes to `base.html`.
- No new breakpoint. Mobile stack (`max-width: 768px`) stays as-is.
- Do not add `overflow: hidden` to `body` — real overflow should remain discoverable.

## Test plan

- Add a Playwright or integration check at 1280×720 and 1024×768 asserting `document.documentElement.scrollWidth === window.innerWidth`.
- Add a check that the Settings nav item is in viewport without scrolling the rail at 720 px.
- Visual verification on Overview, Ledger, Budget, Accounts.

## Docs

- `docs/CHANGELOG.md` — one dated line.
- `docs/plans/v1/tasks.md` — mark `✅ T-090` on completion.
- No ADR, no requirements change (pure visual-fit fix).
