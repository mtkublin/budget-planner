# T-R67 — Accounts ⋯ menu

- **Phase**: 3 — Screens
- **Sequential**: after T-R24, T-R34.
- **Depends on**: T-R34, T-R65 (Edit opens the Create account overlay pre-filled).
- **References**: ADR-0051 §6, handoff §Accounts "Edit, Snapshot, Delete move into a ⋯ menu (not shown)."

## Context

The Accounts table row currently has three visible buttons (Edit, Snapshot, Delete) at the right. Rising Dough collapses them into a ⋯ popover menu with the three actions. Reconcile stays as a dedicated primary action in its own column.

## Deliverables

- `templates/accounts/_row_menu.html` popover with three items:
  - **Edit** — opens the Create account overlay (T-R65) pre-filled; swaps into `#modal-root`.
  - **Snapshot** — posts to the existing `POST /accounts/{id}/snapshots`; toast confirms (T-R61).
  - **Delete** — soft-deletes via existing endpoint; `hx-confirm` guard; toast with Undo (T-R61).
- `templates/accounts/_table.html` Account row trailing cell renders `⋯` button; opens the popover.
- Popover positioning via the same primitive used for Plan · Year cell edit (Alpine or CSS Anchor Positioning fallback).

## Acceptance criteria

- Opening the menu with keyboard: Tab to ⋯, Enter opens, arrow keys cycle items, Esc closes.
- Edit → overlay opens with the row's values pre-filled; save closes overlay + refreshes the row.
- Snapshot → toast "Snapshot saved · Undo" (Undo soft-deletes the snapshot).
- Delete → confirm dialog, soft-delete, toast "Account deleted · Undo".
- Visual-regression baseline for Accounts page with menu open captured at D/T/M.

## Validation hook

```sh
pytest tests/e2e/test_accounts_row_menu.py && \
  just test-visual --filter accounts-row-menu
```

## Risks & gotchas

- Delete of an account with transactions must still fail (existing invariant) — the toast surfaces the error without destroying context.
- Snapshot action is an immutable write — Undo soft-deletes the snapshot row (ADR-0019); confirm the snapshot repo supports soft delete; if not, raise before implementation.

## Handoff notes

- Phase 7 cleanup confirms the old three-button row is removed; grep for the old classes.
