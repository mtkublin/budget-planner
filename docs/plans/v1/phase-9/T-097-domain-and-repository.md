# T-097 — Domain + Repository for User Preferences

> Phase 9 — Left Daily Spend. Status: pending.

## Purpose

Add the domain types (`UserPreference` + `NewUserPreference` + the first known-key constant) and a small pure-function repository (`get`, `upsert`, `delete`) for the `user_preferences` table introduced by T-096. Repository runs inside an explicit `BEGIN`/`COMMIT` for atomicity but deliberately **does not** write to `audit_log` — preferences are UI state, not domain mutations, per ADR-0025.

## Inputs / prerequisites

- Upstream tasks: T-096 (table landed).
- Binding standards: [`ADR-0025`](../../../adr/0025-user-preferences-and-income-anchor.md) § Decision 5, [`ADR-0022`](../../../adr/0022-repository-layer-soft-delete-audit-discipline.md) (repository transaction discipline — this ADR carves out a settings-only audit exception).
- Adjacent precedents:
  - `src/budget_planner/domain/accounts.py` — frozen `slots=True, kw_only=True` dataclass shape.
  - `src/budget_planner/repositories/budgets.py` — simple-table repository (no soft-delete / no audit) is the closest existing analogue; T-097 extends the pattern.
  - `src/budget_planner/repositories/_shared.py` — `transaction()` context manager used verbatim; `mutate(...)` / `write_audit(...)` are explicitly **not** called from the new module.

## Deliverables

New files:

- `src/budget_planner/domain/preferences.py`:
  - `@dataclass(frozen=True, slots=True, kw_only=True) class UserPreference` with fields `id: int`, `user_id: int`, `key: str`, `value: str`, `created_at: datetime`, `updated_at: datetime`.
  - `@dataclass(frozen=True, slots=True, kw_only=True) class NewUserPreference` with fields `user_id: int`, `key: str`, `value: str`.
  - Known-key constant: `PREF_INCOME_ANCHOR_CATEGORY_ID: Final[str] = "income_anchor_category_id"`.
- `src/budget_planner/repositories/preferences.py`:
  - `get(conn: Connection, user_id: int, key: str) -> UserPreference | None`.
  - `upsert(conn: Connection, user_id: int, key: str, value: str) -> UserPreference` (INSERT OR REPLACE semantics preserving `created_at` on update).
  - `delete(conn: Connection, user_id: int, key: str) -> None` (no-op if absent).
  - Shared row hydrator mirroring `repositories.accounts._hydrate` style.

New tests:

- `tests/unit/repositories/test_preferences.py`:
  - `test_get_returns_none_when_absent`
  - `test_upsert_insert_round_trip`
  - `test_upsert_update_preserves_created_at_and_bumps_updated_at`
  - `test_delete_is_idempotent`
  - `test_unique_user_id_key_enforced` — second insert of the same (user_id, key) via raw SQL raises (defence in depth; `upsert` must not hit this path).
  - `test_no_audit_log_row_written` — snapshot `audit_log` count before and after each mutation.

## Step-by-step

1. **Domain.** Mirror `domain/accounts.py` for formatting and dataclass options. Export `UserPreference`, `NewUserPreference`, and `PREF_INCOME_ANCHOR_CATEGORY_ID` from the module `__all__`.
2. **Hydrator.** Private `_hydrate(row)` that parses `created_at` / `updated_at` with `datetime.fromisoformat` to match the Phase 1 pattern (`detect_types` disabled per T-013).
3. **`get`.** Simple `SELECT ... WHERE user_id = ? AND key = ?`. Return `None` if not found.
4. **`upsert`.** Use `INSERT INTO user_preferences (...) VALUES (...) ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP`. Preserves `created_at` by not touching it; the row id stays stable. Fetch and return the resulting row.
5. **`delete`.** `DELETE FROM user_preferences WHERE user_id = ? AND key = ?`. No return value; `rowcount` is ignored — delete is idempotent.
6. **Transaction discipline.** Wrap each mutation in `_shared.transaction(conn)` (BEGIN/COMMIT) but **do not** call `write_audit`. Add a short code comment pointing at ADR-0025 § Decision 1 so future maintainers see the exemption rationale.
7. **Tests.** Follow the existing `tests/unit/repositories/` style (temp SQLite via `conn` fixture, builder helpers from `tests/integration/conftest.py` if adopted — otherwise local setup).

## Validation / acceptance

- `pytest tests/unit/repositories/test_preferences.py -q` — all tests pass.
- `pytest --cov=src/budget_planner/repositories/preferences --cov-fail-under=90 tests/unit/repositories/test_preferences.py` — coverage ≥ 90% on the new module (ideally 100%).
- `grep -nE "audit_log|write_audit" src/budget_planner/repositories/preferences.py` returns no match (defensive).
- `grep -nE "write_audit\\(" tests/unit/repositories/test_preferences.py` returns no match.
- `just lint` + `just typecheck` green.

## Risks & gotchas

- **`ON CONFLICT ... DO UPDATE` requires SQLite 3.24+.** Shipping Python 3.12 brings sqlite3 ≥ 3.31. Safe.
- **`created_at` on update.** `ON CONFLICT ... DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP` leaves `created_at` untouched. If you accidentally include `created_at = excluded.created_at`, the test `test_upsert_update_preserves_created_at_and_bumps_updated_at` will fail — do not add it.
- **Transaction nesting.** Service layer wrappers (T-098) call these repository functions inside their own transactions. `_shared.transaction()` already supports SAVEPOINT nesting (see T-023 upgrade). Reuse — do not reinvent.
- **No soft-delete.** Deleting a preference literally removes the row. If a historical audit of preference changes is ever requested, this is a v2 enhancement (bump to `user_preferences_v2` with a tombstone column).

## Handoff notes

- Hand-off to T-098: the service layer imports `get`, `upsert`, `delete` and the `PREF_INCOME_ANCHOR_CATEGORY_ID` constant.
- Hand-off to T-101: a dropdown on `/budget/manage` uses `upsert` for set and `delete` for clear; the empty-string body on the POST endpoint maps to `delete`.
- Commit shape: `feat(T-097): user_preferences repository + domain (ADR-0025)`.
