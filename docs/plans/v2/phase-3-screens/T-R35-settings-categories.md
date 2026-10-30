# T-R35 — Settings · Categories

- **Phase**: 3 — Screens
- **Sequential**: after T-R24, T-R44, T-R71 (archived-categories decision).
- **Depends on**: T-R24 primitives, T-R44 (archive/restore endpoints), T-R71 (behaviour decision).
- **References**: handoff §Settings · Categories, ADR-0048 (colour), ADR-0051 §7, ADR-0023 (direction scope).

## Context

Settings · Categories gets room for category colour, archive/restore, and the income-anchor selector as the first control. Groups: Expense · Income · System. System rows locked.

## Deliverables

- `templates/settings/_categories.html` composing:
  - **Income anchor section** — current anchor dropdown + save; mirror link from Preferences tab (T-R37) jumps here via `#income-anchor`.
  - **Expense group** — row = category pill (via `category_pill`) + direction badge + colour source indicator + action cluster (Edit · Archive).
  - **Income group** — same shape.
  - **System group** — Transit + Reconciliation; locked state (no Edit, no Archive).
  - **Archived section** — collapsed by default; expands to show archived categories with Restore buttons (uses T-R44 restore endpoint).
- Edit opens the Create category overlay (T-R66) pre-filled.
- Archive button:
  - Shows confirm dialog.
  - Per T-R71 decision: either (a) blocked when any live recurring rule references the category (inline error with link to rule) or (b) allowed with warning banner.
  - On success, row moves to Archived section; toast with Undo (T-R61).
- Archived row restore: Restore button → `POST /categories/{id}/restore` + toast.
- Integration tests cover: archive success + undo, archive-blocked path (T-R71 outcome a), restore, income-anchor save, system-category Edit disabled.

## Acceptance criteria

- Visual-regression baseline matches handoff `desktop-1n-settings-categories.png` at D/T/M.
- Archive confirm dialog carries the category name and the T-R71 warning text.
- System categories render with a lock icon + tooltip "system category — not editable".
- Income-anchor dropdown restricted to income-direction categories (no transit, no adjustment).
- Keyboard: Tab across rows reaches every button; focus ring visible.

## Validation hook

```sh
pytest tests/integration/web/test_settings_categories.py && \
  just test-visual --filter settings-categories
```

## Risks & gotchas

- Income anchor change invalidates `budget-stale` + `today-stale`; emit both via `HX-Trigger` so Today + Plan tabs refetch.
- Archive of a category used by soft-deleted (but not purged) transactions must still succeed — history still references the category id.
- The Archived section query filters `deleted_at >= now - 90 days` to match T-R70's Recently-deleted window.

## Handoff notes

- T-R66 (Create category overlay) is the Edit target.
- T-R37 (Preferences) links to the `#income-anchor` anchor on this page.
