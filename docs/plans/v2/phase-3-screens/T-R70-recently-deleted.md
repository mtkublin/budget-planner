# T-R70 — "Recently deleted" surface

- **Phase**: 3 — Screens
- **Sequential**: after T-R26.
- **Depends on**: T-R26, ADR-0019 (soft delete + audit).
- **References**: handoff §Ledger · Actual "Deleted = archived; restorable from ⋯ or 'Recently deleted'".

## Context

Soft-delete is already in place for every mutable table (ADR-0019). The redesign makes recovery discoverable: a dedicated panel lists recently archived rows with Restore buttons.

## Deliverables

- `GET /ledger/recently-deleted` returns a panel listing:
  - Transactions: deleted within 90 days, grouped by day of deletion, with Restore button → `POST /transactions/{id}/restore` (new endpoint if missing).
  - Planned: same shape.
  - Categories: deleted within 90 days (archived — see T-R71 decision); Restore → `POST /categories/{id}/restore` (added by T-R44).
- Entry points:
  - Row ⋯ menu on Ledger surfaces "View recently deleted" alongside Delete.
  - Settings · Categories gets an "Archived (N)" chip linking to the Categories section of this panel.
- Panel renders inline on `/ledger?view=recently-deleted` as a fifth segmented-control value (hidden until something is deleted; always reachable via menu).
- Restore endpoints clear `deleted_at` + write an `audit_log` entry.

## Acceptance criteria

- A deleted transaction appears in Recently deleted within one refresh; Restore button returns it to the live Ledger.
- 90-day cutoff enforced at the service layer; older rows do not appear.
- Restoring a category whose direction has drifted (per ADR-0023 scope) fails with a clear error; the panel surfaces the error inline.
- `frontend-visual-audit` on the panel returns zero findings at D/T/M.

## Validation hook

```sh
pytest tests/integration/web/test_recently_deleted.py && \
  curl -sS http://localhost:8000/ledger/recently-deleted | grep -q "restore"
```

## Risks & gotchas

- Restoring a category used by a soft-deleted transaction raises an ambiguity: the txn should probably also restore. Pick a rule (recommended: restore category only; txns stay soft-deleted; user restores them separately) and document in the task PR body.
- Audit log already supports restore operations; verify the audit entry carries `operation="restore"`.

## Handoff notes

- T-R71 (archived categories on recurring rules) feeds the "can archived category be a source" question; this panel is where the user flips state back.
