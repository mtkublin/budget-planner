# T-013 — Repository Layer

> Phase 1 — Data Layer. Status: pending.

## Purpose

Provide the one and only path between services and SQL. Pure-function modules per entity, every mutation wrapped by a shared helper that writes `audit_log` and bumps `updated_at` in the same DB transaction. Every reader filters `deleted_at IS NULL` by default and accepts `include_deleted: bool = False` for admin paths.

## Inputs / prerequisites

- Upstream tasks:
  - [`T-011-core-schema-migration.md`](T-011-core-schema-migration.md) — tables exist.
  - [`T-012-seed-data-migration.md`](T-012-seed-data-migration.md) — system categories exist for integration tests.
  - [`T-014-domain-types.md`](T-014-domain-types.md) — dataclasses and DTOs this module returns and accepts.
- ADRs:
  - [`../../adr/0005-single-user-no-auth-user-id-scaffold.md`](../../adr/0005-single-user-no-auth-user-id-scaffold.md) — `user_id = 1` default.
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — amount sign rules; `adjustment` exception.
  - [`../../adr/0009-transit-single-row-model.md`](../../adr/0009-transit-single-row-model.md) — transit = single row with `dest_account_id`.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md) — soft-delete default + polymorphic audit.
  - [`../../adr/0021-functional-style-no-oop.md`](../../adr/0021-functional-style-no-oop.md) — no classes beyond frozen dataclasses.

## Deliverables

```
src/budget_planner/repositories/__init__.py
src/budget_planner/repositories/_shared.py          # audit helper, row->DTO, mutation wrapper
src/budget_planner/repositories/accounts.py
src/budget_planner/repositories/categories.py
src/budget_planner/repositories/transactions.py
src/budget_planner/repositories/planned.py
src/budget_planner/repositories/recurring.py        # rules + overrides
src/budget_planner/repositories/budgets.py          # defaults + recurring_overrides + one_off_overrides
src/budget_planner/repositories/snapshots.py
src/budget_planner/repositories/fx.py
src/budget_planner/repositories/audit.py            # read helpers over audit_log

tests/unit/repositories/test_accounts.py
tests/unit/repositories/test_categories.py
tests/unit/repositories/test_transactions.py
tests/unit/repositories/test_planned.py
tests/unit/repositories/test_recurring.py
tests/unit/repositories/test_budgets.py
tests/unit/repositories/test_snapshots.py
tests/unit/repositories/test_fx.py
tests/unit/repositories/test_shared.py              # audit + soft-delete + updated_at semantics
```

### Public function signatures (per module)

Each module exposes the same CRUD surface. Shapes referenced below (`Account`, `NewAccount`, …) are defined in T-014.

```python
# accounts.py
def find_by_id(conn: Connection, account_id: int, *, include_deleted: bool = False) -> Account | None: ...
def find_by_name(conn: Connection, name: str, *, include_deleted: bool = False) -> Account | None: ...
def list_all(conn: Connection, *, include_deleted: bool = False) -> list[Account]: ...
def create(conn: Connection, data: NewAccount) -> Account: ...
def update(conn: Connection, account_id: int, data: PatchAccount) -> Account: ...
def soft_delete(conn: Connection, account_id: int) -> None: ...
def undelete(conn: Connection, account_id: int) -> Account: ...

# categories.py
def find_by_id(conn, category_id, *, include_deleted=False) -> Category | None: ...
def find_by_name(conn, name, *, include_deleted=False) -> Category | None: ...
def list_all(conn, *, include_deleted=False) -> list[Category]: ...
def create(conn, data: NewCategory) -> Category: ...
def update(conn, category_id, data: PatchCategory) -> Category: ...
def soft_delete(conn, category_id) -> None: ...
def undelete(conn, category_id) -> Category: ...

# transactions.py
def find_by_id(conn, txn_id, *, include_deleted=False) -> Transaction | None: ...
def list_filtered(conn, filters: TransactionFilter, *, include_deleted=False) -> list[Transaction]: ...
def create(conn, data: NewTransaction) -> Transaction: ...
def update(conn, txn_id, data: PatchTransaction) -> Transaction: ...
def soft_delete(conn, txn_id) -> None: ...
def undelete(conn, txn_id) -> Transaction: ...

# planned.py
def find_by_id(conn, planned_id, *, include_deleted=False) -> PlannedTransaction | None: ...
def list_filtered(conn, filters: PlannedFilter, *, include_deleted=False) -> list[PlannedTransaction]: ...
def create(conn, data: NewPlannedTransaction) -> PlannedTransaction: ...
def update(conn, planned_id, data: PatchPlannedTransaction) -> PlannedTransaction: ...
def soft_delete(conn, planned_id) -> None: ...
def undelete(conn, planned_id) -> PlannedTransaction: ...
def stamp_promotion(conn, planned_id: int, txn_id: int) -> PlannedTransaction: ...

# recurring.py
def find_rule(conn, rule_id, *, include_deleted=False) -> RecurringRule | None: ...
def list_rules(conn, *, active_only: bool = False, include_deleted=False) -> list[RecurringRule]: ...
def create_rule(conn, data: NewRecurringRule) -> RecurringRule: ...
def update_rule(conn, rule_id, data: PatchRecurringRule) -> RecurringRule: ...
def deactivate_rule(conn, rule_id) -> RecurringRule: ...
def soft_delete_rule(conn, rule_id) -> None: ...
def list_overrides(conn, rule_id: int) -> list[RecurringOverride]: ...
def upsert_override(conn, data: NewRecurringOverride) -> RecurringOverride: ...
def delete_override(conn, rule_id: int, occurrence_date: date) -> None: ...

# budgets.py
def get_default(conn, category_id, *, include_deleted=False) -> BudgetDefault | None: ...
def set_default(conn, data: NewBudgetDefault) -> BudgetDefault: ...
def list_defaults(conn, *, include_deleted=False) -> list[BudgetDefault]: ...
def clear_default(conn, category_id) -> None: ...

def get_recurring(conn, category_id, month, *, include_deleted=False) -> BudgetRecurringOverride | None: ...
def set_recurring(conn, data: NewBudgetRecurringOverride) -> BudgetRecurringOverride: ...
def list_recurring(conn, *, include_deleted=False) -> list[BudgetRecurringOverride]: ...
def clear_recurring(conn, category_id, month) -> None: ...

def get_one_off(conn, category_id, year, month, *, include_deleted=False) -> BudgetOneOffOverride | None: ...
def set_one_off(conn, data: NewBudgetOneOffOverride) -> BudgetOneOffOverride: ...
def list_one_off(conn, *, year: int | None = None, include_deleted=False) -> list[BudgetOneOffOverride]: ...
def clear_one_off(conn, category_id, year, month) -> None: ...

# snapshots.py
def list_for_account(conn, account_id: int) -> list[AccountSnapshot]: ...
def create(conn, data: NewAccountSnapshot) -> AccountSnapshot: ...   # append-only; no update/delete

# fx.py
def find_rate(conn, date: date, from_ccy: str, to_ccy: str) -> FxRate | None: ...
def latest_rate(conn, from_ccy: str, to_ccy: str) -> FxRate | None: ...
def upsert_rate(conn, data: NewFxRate) -> FxRate: ...                 # append-only logically; UNIQUE((date,pair))

# audit.py
def list_entries(conn, entity_type: str, entity_id: int) -> list[AuditEntry]: ...
def recent(conn, limit: int = 100) -> list[AuditEntry]: ...
```

## Step-by-step

1. **Shared helpers in `repositories/_shared.py`:**

   ```python
   from __future__ import annotations

   import json
   import sqlite3
   from collections.abc import Callable
   from contextlib import contextmanager
   from dataclasses import asdict
   from datetime import datetime, timezone
   from typing import Any, Iterator, TypeVar

   T = TypeVar("T")


   def _utc_now_iso() -> str:
       return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


   def _dumps(value: Any) -> str | None:
       if value is None:
           return None
       if hasattr(value, "__dataclass_fields__"):
           value = asdict(value)
       return json.dumps(value, default=str, sort_keys=True)


   def write_audit(
       conn: sqlite3.Connection,
       *,
       entity_type: str,
       entity_id: int,
       operation: str,                      # 'create' | 'update' | 'delete' | 'undelete'
       prev: Any | None,
       new: Any | None,
   ) -> None:
       conn.execute(
           "INSERT INTO audit_log(entity_type, entity_id, operation, prev_json, new_json) "
           "VALUES (?, ?, ?, ?, ?)",
           (entity_type, entity_id, operation, _dumps(prev), _dumps(new)),
       )


   @contextmanager
   def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
       """Explicit transaction context; works with `isolation_level=None`."""
       conn.execute("BEGIN")
       try:
           yield conn
           conn.execute("COMMIT")
       except Exception:
           conn.execute("ROLLBACK")
           raise


   def mutate(
       conn: sqlite3.Connection,
       *,
       entity_type: str,
       entity_id: int | None,                      # None for 'create' before INSERT
       operation: str,
       prev: Any | None,
       action: Callable[[sqlite3.Connection], tuple[int, Any]],
   ) -> Any:
       """
       Execute `action` inside a transaction, then write a matching audit row.

       `action(conn)` returns `(entity_id, new_value)` where:
         - entity_id is the row id after the mutation (useful for create)
         - new_value is the hydrated DTO (or None for delete)
       """
       with transaction(conn):
           new_id, new_value = action(conn)
           write_audit(
               conn,
               entity_type=entity_type,
               entity_id=new_id,
               operation=operation,
               prev=prev,
               new=new_value,
           )
           return new_value
   ```

   `mutate(...)` is the only path to the DB for mutations. Every repository `create` / `update` / `soft_delete` / `undelete` goes through it, which guarantees:
   - Mutation + audit row in the same transaction.
   - `prev` snapshot is captured before the write.
   - `updated_at = now()` is bumped by the `UPDATE` statement inside `action`.

2. **Row → dataclass hydration.** Each repository module has a private `_row_to_X(row: sqlite3.Row) -> X` function. Example:

   ```python
   # repositories/accounts.py
   from __future__ import annotations

   import sqlite3
   from datetime import datetime

   from budget_planner.domain.accounts import Account, NewAccount, PatchAccount
   from budget_planner.repositories._shared import mutate

   _COLUMNS = (
       "id, user_id, name, type, currency, opening_balance, "
       "created_at, updated_at, deleted_at"
   )


   def _row_to_account(row: sqlite3.Row) -> Account:
       return Account(
           id=row["id"],
           user_id=row["user_id"],
           name=row["name"],
           type=row["type"],
           currency=row["currency"],
           opening_balance=row["opening_balance"],
           created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
           updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
           deleted_at=(
               datetime.fromisoformat(row["deleted_at"].replace("Z", "+00:00"))
               if row["deleted_at"] is not None else None
           ),
       )


   def find_by_id(
       conn: sqlite3.Connection,
       account_id: int,
       *,
       include_deleted: bool = False,
   ) -> Account | None:
       sql = f"SELECT {_COLUMNS} FROM accounts WHERE id = ?"
       if not include_deleted:
           sql += " AND deleted_at IS NULL"
       row = conn.execute(sql, (account_id,)).fetchone()
       return _row_to_account(row) if row is not None else None


   def list_all(
       conn: sqlite3.Connection,
       *,
       include_deleted: bool = False,
   ) -> list[Account]:
       sql = f"SELECT {_COLUMNS} FROM accounts"
       if not include_deleted:
           sql += " WHERE deleted_at IS NULL"
       sql += " ORDER BY name ASC"
       return [_row_to_account(r) for r in conn.execute(sql).fetchall()]


   def create(conn: sqlite3.Connection, data: NewAccount) -> Account:
       def _action(c: sqlite3.Connection) -> tuple[int, Account]:
           cursor = c.execute(
               "INSERT INTO accounts(user_id, name, type, currency, opening_balance) "
               "VALUES (?, ?, ?, ?, ?)",
               (data.user_id, data.name, data.type, data.currency, data.opening_balance),
           )
           new_id = int(cursor.lastrowid)
           created = find_by_id(c, new_id)
           assert created is not None
           return new_id, created

       return mutate(
           conn,
           entity_type="account",
           entity_id=0,                         # overwritten by _action
           operation="create",
           prev=None,
           action=_action,
       )


   def update(
       conn: sqlite3.Connection,
       account_id: int,
       data: PatchAccount,
   ) -> Account:
       prev = find_by_id(conn, account_id, include_deleted=True)
       if prev is None:
           raise LookupError(f"account {account_id} not found")

       def _action(c: sqlite3.Connection) -> tuple[int, Account]:
           # Only patch set fields; currency is immutable per ADR-0006 — rejected in the service.
           sets, params = [], []
           for field, value in data.as_dict().items():
               sets.append(f"{field} = ?")
               params.append(value)
           sets.append("updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")
           c.execute(
               f"UPDATE accounts SET {', '.join(sets)} WHERE id = ?",
               (*params, account_id),
           )
           updated = find_by_id(c, account_id)
           assert updated is not None
           return account_id, updated

       return mutate(
           conn,
           entity_type="account",
           entity_id=account_id,
           operation="update",
           prev=prev,
           action=_action,
       )


   def soft_delete(conn: sqlite3.Connection, account_id: int) -> None:
       prev = find_by_id(conn, account_id)
       if prev is None:
           return

       def _action(c: sqlite3.Connection) -> tuple[int, None]:
           c.execute(
               "UPDATE accounts "
               "SET deleted_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "
               "    updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
               "WHERE id = ? AND deleted_at IS NULL",
               (account_id,),
           )
           return account_id, None

       mutate(
           conn,
           entity_type="account",
           entity_id=account_id,
           operation="delete",
           prev=prev,
           action=_action,
       )


   def undelete(conn: sqlite3.Connection, account_id: int) -> Account:
       prev = find_by_id(conn, account_id, include_deleted=True)
       if prev is None:
           raise LookupError(f"account {account_id} not found")

       def _action(c: sqlite3.Connection) -> tuple[int, Account]:
           c.execute(
               "UPDATE accounts "
               "SET deleted_at = NULL, "
               "    updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
               "WHERE id = ?",
               (account_id,),
           )
           restored = find_by_id(c, account_id)
           assert restored is not None
           return account_id, restored

       return mutate(
           conn,
           entity_type="account",
           entity_id=account_id,
           operation="undelete",
           prev=prev,
           action=_action,
       )
   ```

   This exact pattern repeats for every other module. Deviations:
   - `snapshots.py` is append-only; it only has `list_for_account` and `create`. `create` still goes through `mutate` with `entity_type="snapshot"`.
   - `fx.py` is append-only; `upsert_rate` goes through `mutate` with `entity_type="fx_rate"`.
   - `recurring.py` has both rule and override surfaces; overrides are keyed `(rule_id, occurrence_date)` and audited with `entity_type="recurring_override"`, `entity_id = <override id>`.
   - `audit.py` is read-only.

3. **Filter DTOs.** `TransactionFilter`, `PlannedFilter` carry: date range, account ids, category ids, direction set, amount range, text search. Each is a frozen dataclass (T-014). `list_filtered` builds its WHERE clause from the DTO; soft-delete filter is appended last.

4. **Soft-delete toggle.** Every reader supports `include_deleted=False` (default) via `AND deleted_at IS NULL` conditional append. For joined queries involving `categories` or `accounts`, filter their `deleted_at` too — e.g. a transaction's `account_id` may still exist as a soft-deleted row; the transaction itself is still visible, but a joined view that renders the account name should load through the account repository with `include_deleted=True`.

5. **Error handling.** Repositories raise `LookupError` for unknown ids on `update`/`undelete`. They do **not** translate SQLite `IntegrityError` — bubble it up so services can decide how to render it.

6. **Tests (per module, pytest fixture pattern):**

   ```python
   @pytest.fixture
   def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
       settings = Settings(database_url=f"sqlite:///{tmp_path/'t.db'}")
       with get_connection(settings) as c:
           apply_migrations(c)
           yield c
   ```

   Required test coverage per module:
   - Round-trip: `create → find_by_id` returns the same DTO.
   - `list_*` default-filters soft-deleted rows; `include_deleted=True` returns them.
   - `update` bumps `updated_at` strictly later than `created_at`.
   - Every mutation inserts exactly one `audit_log` row with matching `entity_type`, `entity_id`, and `operation`.
   - `soft_delete` sets `deleted_at`; `undelete` clears it; both appear in `audit_log`.
   - `test_shared.py` asserts audit JSON structure (fields in `prev_json` / `new_json`, `null` on create/delete).

## Interfaces / contracts

Canonical repository function surface downstream phases will call:

```python
# Readers (all accept include_deleted: bool = False)
find_by_id(conn, id)                 -> DTO | None
find_by_name(conn, name)             -> DTO | None   # where applicable
list_all(conn)                       -> list[DTO]
list_filtered(conn, filters)         -> list[DTO]    # transactions / planned

# Mutators (all go through _shared.mutate; all write audit)
create(conn, data: NewX)             -> DTO
update(conn, id, data: PatchX)       -> DTO
soft_delete(conn, id)                -> None
undelete(conn, id)                   -> DTO

# Append-only
snapshots.create(conn, data)         -> AccountSnapshot
fx.upsert_rate(conn, data)           -> FxRate

# Audit reader
audit.list_entries(conn, entity_type, entity_id) -> list[AuditEntry]
audit.recent(conn, limit=100)                     -> list[AuditEntry]
```

## Validation / acceptance

- `just migrate` from empty DB → `just test tests/unit/repositories/` green.
- For every repository test case, assert the paired `audit_log` row exists (shared fixture utility).
- Soft-delete round-trip: `create` → `soft_delete` → `list_all` returns `[]` → `list_all(include_deleted=True)` returns 1 row → `undelete` → `list_all` returns 1 row again. Four `audit_log` rows written.
- `transactions.list_filtered` with a date range filter matches a hand-built SQL expectation on a 20-row fixture.
- `_shared.mutate` test: if `action` raises, the DB state is unchanged **and** no audit row is written (full rollback).
- Phase-1 exit criteria from `docs/implementation_plan.md` all green:
  - Repository functions pass unit tests against a temp DB.
  - Audit log receives entries from every mutation.
  - Soft-delete filter default-on; `include_deleted=True` round-trips.

## Risks & gotchas

- **ADR-0022 does NOT exist.** `docs/tasks.md` Phase 1 (T-013) and Phase 2 (T-028) both cite "ADR-0022", but the ADR index ([`../../adr/README.md`](../../adr/README.md)) stops at ADR-0021. The repository-layer discipline here (soft-delete default + audit-in-same-tx + no-service-can-bypass) is architecturally significant and worth capturing. **Propose** writing a new ADR titled "Repository layer: soft-delete + audit discipline" as part of this task's doc-first step, which would land as **ADR-0022**. Do not author it in this plan — flag only, per CLAUDE.md change policy.
- **SQLite integer FK pragma is per-connection.** The `get_connection` helper (T-010) enables `PRAGMA foreign_keys = ON`; every test must use it.
- **Partial unique indexes on `name` with `deleted_at IS NULL`.** `create` on a name that already exists for a live row raises `IntegrityError` (bubbled up). After `soft_delete`, the same name becomes available. Tests must cover this round-trip.
- **JSON columns in audit.** `prev_json` / `new_json` are TEXT. Timestamps are serialised via `json.dumps(..., default=str)` which produces ISO strings — services decoding audit must parse them back.
- **DECIMAL vs integer minor units.** The money fields (`amount`, `opening_balance`, `default_amount`, budget amounts, snapshot `balance`) are all `INTEGER`. Repositories never see `Decimal`. Conversion happens in T-014 helpers at service boundary.
- **Timezone of `created_at` / `updated_at` vs `operation_date`.** Both metadata columns are UTC ISO strings; `operation_date` is a plain `DATE`. Hydration must not mix them (see `_row_to_account` above).
- **`updated_at` default is INSERT-time.** SQLite does not auto-bump on UPDATE. The `update` path explicitly sets `updated_at = strftime(...)` in the same UPDATE.
- **Non-atomic audit = bug.** Any `UPDATE` or `INSERT` executed outside `_shared.mutate` is a lint violation. Add a repository test that greps the module for raw `conn.execute("UPDATE accounts ...")` outside of `_action` closures (or enforce via code review checklist).
- **`isolation_level=None` + explicit `BEGIN`.** Required by the chosen pattern. Never call `conn.commit()` or `conn.rollback()` directly from a repository — go through `_shared.transaction`.

## Handoff notes

- Phase 2 services never execute raw SQL. They import repository functions and compose. Example:
  - `services.balance.derive_balance` reads `transactions.list_filtered(TransactionFilter(account_or_dest=account_id, up_to_date=as_of))`.
  - `services.reconciliation.reconcile` reads `balance.derive_balance`, builds a `NewTransaction` with the Reconciliation category id, calls `transactions.create`.
  - `services.audit.write_audit` of the implementation plan is **this** `_shared.write_audit` function; T-028 should re-export rather than re-implement.
- Phase 2 FX service: calls `fx.find_rate` → if `None`, HTTP fetch → `fx.upsert_rate`; falls back to `fx.latest_rate` on API error.
- Phase 2 recurring service calls `recurring.list_rules(active_only=True)` and `recurring.list_overrides(rule_id)` to generate virtual occurrences; it never materialises them.
