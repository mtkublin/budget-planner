# T-R45 — Batch promote-due

- **Phase**: 4 — Backend
- **Parallel-safe**: yes.
- **Depends on**: T-R10.
- **References**: ADR-0056 §6, ADR-0038 (recurring promote shape), ADR-0012 (planned promote).

## Context

`⇧↵` on Today's Upcoming panel promotes every rule and planned row due today or overdue. One DB transaction. Returns a summary that drives the Undo toast; Undo soft-deletes the created transactions + rolls back `next_due` advancements.

## Deliverables

- `src/budget_planner/services/recurring.py` gains:
  ```python
  @dataclass(frozen=True)
  class BatchPromoteResult:
      promoted_txn_ids: tuple[int, ...]
      advanced_rule_ids: tuple[int, ...]
      skipped: tuple[SkipReason, ...]

  def batch_promote_due(conn: Connection, today: date, *, request_ctx: RequestCtx) -> BatchPromoteResult: ...
  ```
- `src/budget_planner/services/planned.py` gains an equivalent `batch_promote_due`.
- Both run inside a single `BEGIN/COMMIT`; on any exception every write rolls back.
- Routers:
  - `POST /recurring/batch/promote-due` → returns the Jinja toast fragment with Undo URL `/batch/undo?token=<id>`.
  - `POST /planned/batch/promote-due` → same shape.
- Undo endpoint `POST /batch/undo?token=…`:
  - Looks up a short-lived (10 min) `batch_promote_log(id, kind, promoted_txn_ids, advanced_rule_ids, created_at)` row.
  - Soft-deletes the promoted transactions.
  - Reverts `recurring_rules.next_due` for the advanced rules (using the pre-advance values recorded on the batch).
  - Writes `audit_log` entries for each reversal.
- Short-lived `batch_promote_log` table added via a new migration **only if** no equivalent surface exists — otherwise piggyback on existing audit entries.
  - *Prefer the audit-based reversal path to avoid a schema change.* Reconstruct the state from the audit log entries written during the batch promote.
- Unit + integration tests cover: batch with 0 items (noop), batch with 3 recurring + 2 planned (one of which is a formula), one rule fails validation (whole batch rolls back), undo after 2 min (succeeds), undo after 15 min (expired — 410).

## Acceptance criteria

- Coverage ≥ 90 % on both service modules.
- The batch is atomic: a formula-resolves-to-non-positive error inside the batch rolls back every write.
- Undo restores identical pre-batch state: same `next_due` on rules, same `deleted_at IS NULL` state on no transactions, same audit log entries + reversal entries.
- Expired Undo token returns 410 Gone (not 404) so the UI can surface a specific message.
- `request_ctx` is threaded through all audit entries.

## Validation hook

```sh
pytest tests/unit/services/test_batch_promote.py tests/integration/web/test_batch_promote.py
```

## Risks & gotchas

- Zero-schema-change constraint is non-negotiable per v2 scope. The audit-based reversal path is the only acceptable implementation.
- Rules advancing to `active=0` (end-of-rule) must reverse to `active=1` on Undo.
- Non-anchor timezone: `today` must come from `now_in(settings.display_timezone)` not `date.today()`.

## Handoff notes

- T-R25 Today page keyboard handler fires `POST /recurring/batch/promote-due` + `POST /planned/batch/promote-due` on `⇧↵` and combines the two toasts into one with a single Undo covering both.
- T-R61 toast macro renders the Undo; the Undo URL points at `/batch/undo?token=…`.
