# T-R44 — Category archive / restore

- **Phase**: 4 — Backend
- **Parallel-safe**: yes.
- **Depends on**: T-R10, T-R71 (archived-categories decision).
- **References**: ADR-0056 §6, ADR-0022 (soft delete), ADR-0019 (audit).

## Context

v1 soft-deletes transactions; categories do not currently expose a soft-delete surface. v2 Settings · Categories (T-R35) needs Archive + Restore. Behaviour depends on T-R71 outcome (block vs. warn when live recurring rules reference the category).

## Deliverables

- `src/budget_planner/services/categories.py` gains:
  ```python
  def archive(conn: Connection, category_id: int, *, request_ctx: RequestCtx) -> None: ...
  def restore(conn: Connection, category_id: int, *, request_ctx: RequestCtx) -> None: ...
  ```
  - `archive` sets `deleted_at = CURRENT_TIMESTAMP` via `_shared.mutate(...)` so the audit entry lands in the same transaction.
  - Pre-check per T-R71: raise `CategoryHasLiveRulesError` (422) if block-mode; log a warning entry if warn-mode.
  - System categories (`is_system=1`) raise 403.
  - `restore` clears `deleted_at`; audits.
- Routers:
  - `POST /categories/{id}/archive` → 204 + `HX-Trigger: {"toast": {"variant":"success","message":"Category archived","undo_url":"/categories/{id}/restore"}, "settings-categories-stale": true}`.
  - `POST /categories/{id}/restore` → 204 + inverse toast + stale event.
- Unit tests cover: archive OK, archive system-category 403, archive-with-live-rules in both T-R71 modes, restore after archive, restore of non-archived 404.
- Integration tests cover: HTTP shape, HX-Trigger payload.

## Acceptance criteria

- Coverage ≥ 90 % on the new service module.
- Audit log entries carry `operation="archive"` / `operation="restore"` and the request context (ip, user id, user agent).
- Restore of a category that was referenced by a live rule at archive time restores to the exact same shape — no orphan state.
- Archive of a deleted category 404s (not idempotent — explicit error signals a stale UI).

## Validation hook

```sh
pytest tests/unit/services/test_categories_archive.py tests/integration/web/test_categories.py -k "archive or restore"
```

## Risks & gotchas

- `_shared.mutate` with `write_audit` must receive `prev_json` and `new_json` with the full category row for a clean audit replay path.
- Archive and restore must be idempotent-safe on retry: a double-POST of archive on an already-archived row 404s (safe; the UI already showed the archived state).
- Categories referenced by soft-deleted transactions must still archive — history is immutable.

## Handoff notes

- T-R35 Settings · Categories consumes both endpoints.
- T-R70 Recently-deleted lists archived categories with Restore buttons; same `restore` endpoint.
- T-R71 decision outcome determines the archive precondition behaviour; test fixtures parametrise both.
