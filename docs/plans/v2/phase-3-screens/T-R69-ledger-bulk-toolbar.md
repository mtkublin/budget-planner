# T-R69 — Ledger bulk-select toolbar

- **Phase**: 3 — Screens
- **Sequential**: after T-R26, T-R27.
- **Depends on**: T-R26 (Ledger · Actual), T-R27 (Ledger · Planned).
- **References**: handoff §Ledger · Actual "Bulk actions and export appear as a toolbar when rows are selected."

## Context

Ledger · Actual + Ledger · Planned gain a row-select checkbox. When any row is selected, a sticky toolbar replaces the filter chip row with: selection count, Export CSV, Export Parquet, Bulk delete. Export uses the current filter + selected row ids. Bulk delete soft-deletes with a single Undo toast.

## Deliverables

- `templates/ledger/_row.html` — row prefix cell with `<input type="checkbox" name="row_ids" value="{{ txn.id }}">`.
- `templates/ledger/_bulk_toolbar.html` — sticky toolbar inside `#ledger-filters` slot, shown when `selection.count > 0`.
- `static/js/bulk-select.js` — tracks selected ids, swaps the filter chip row for the toolbar, drives Shift-click range selection.
- Routes:
  - `POST /ledger/export?view=actual|planned&format=csv|parquet` reuses existing export logic + accepts optional `row_ids[]` constraint.
  - `POST /ledger/batch/delete?view=actual|planned` soft-deletes selected ids in one transaction; returns a toast via `HX-Trigger`.
- Recurring tab does **not** get bulk delete (handoff reserves bulk actions for Actual + Planned); checkbox omitted.
- Integration tests cover select-all, Shift-click, export with selection, bulk delete + Undo via toast.

## Acceptance criteria

- Selecting any row swaps the chip row for the toolbar with a smooth transition.
- Shift-click selects the range.
- Export with 3 rows selected returns a file containing exactly those 3 rows (plus current filter still applied — e.g. only expense direction).
- Bulk delete fires one audit entry per row and one toast with Undo that restores all rows atomically.
- Visual-regression baseline captured with toolbar visible at D/T/M.

## Validation hook

```sh
pytest tests/integration/web/test_ledger_bulk.py && \
  just test-visual --filter ledger-bulk
```

## Risks & gotchas

- Export already supports the current filter; the row-id constraint must be an intersection, not a replacement.
- Undo of a bulk delete must restore every row in a single `BEGIN/COMMIT` so partial state is impossible on failure.
- Mobile layout: the toolbar replaces the chip row at the top; at 375 px it may need to wrap. Visual-regression captures mobile explicitly.

## Handoff notes

- Recurring tab's row actions stay per-row (Promote / Edit / Skip / Delete via ⋯) — no bulk affordance.
- Phase 7 cleanup prunes any orphaned filter-chip CSS classes if the toolbar replaces them in the DOM.
