# T-028 — Audit Helper

> Phase 2 — Services. Status: pending.

## Purpose

Single shared `write_audit(...)` function called from every mutating repository function in Phase 1, inside the same DB transaction as the mutation. All `audit_log` writes go through this function; no SQL `INSERT INTO audit_log` lives anywhere else. The shape is a polymorphic row keyed by `(entity_type, entity_id, changed_at, operation)` with JSON blobs for before/after (ADR-0019).

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-011 Core schema migration](../phase-1/T-011-core-schema-migration.md) — defines the `audit_log` table.
  - [T-013 Repository layer](../phase-1/T-013-repository-layer.md) — the physical caller of this helper. Phase 1's T-013 plan already references a shared mutate helper; this plan formalises its contract.
- ADRs:
  - [ADR-0019 Soft delete + audit log](../../adr/0019-soft-delete-and-audit-log.md).
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
  - *(tasks.md cites ADR-0022 for T-028; the ADR index tops out at ADR-0021. A new ADR for the repository/audit pattern was flagged in the Phase 1 T-013 plan and will be written there; this plan defers to that follow-up and uses ADR-0019 as the canonical reference until that ADR lands.)*

## Deliverables

- Module path: `src/budget_planner/services/audit.py`
- Test module path: `tests/unit/services/test_audit.py`
- Public function signatures:

```python
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from collections.abc import Mapping
from typing import Any, Literal

AuditOperation = Literal["create", "update", "delete", "undelete"]


def write_audit(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: int,
    operation: AuditOperation,
    prev: Mapping[str, Any] | None,
    new: Mapping[str, Any] | None,
    changed_at: dt.datetime | None = None,
) -> int:
    """
    Insert an audit_log row and return its id. Must be called inside the
    same DB transaction as the mutation it describes.

    Invariants:
      - operation='create' → prev is None, new is not None.
      - operation='delete' → new is None, prev is not None.
      - operation='update' → both not None.
      - operation='undelete' → prev is None (soft-deleted state is terminal
        for prev_json; the row returning is the new_json).
      - changed_at defaults to datetime.now(timezone.utc). Caller may
        override for deterministic tests.
    """
```

## Algorithm / step-by-step

```
1. Validate operation precondition pairs (see table below).
   On mismatch: raise AuditShapeError (programmer error, not user).

2. changed_at = changed_at or datetime.now(timezone.utc)
   # Always UTC per ADR-0007.

3. prev_json = json.dumps(prev, default=_json_default, sort_keys=True) if prev else None
   new_json  = json.dumps(new,  default=_json_default, sort_keys=True) if new  else None

4. Execute parameterised INSERT. Return conn.execute(...).lastrowid.
```

`sort_keys=True` makes the stored JSON byte-stable, which simplifies test assertions and future diffing.

`_json_default` handles types stdlib `json` cannot serialise:

| Python type | Serialised as |
|-------------|---------------|
| `datetime.date` | `isoformat()` → `"YYYY-MM-DD"` |
| `datetime.datetime` | `isoformat()` with offset |
| `decimal.Decimal` | `str(value)` to preserve precision |
| `enum.Enum` | `value.value` |
| frozen dataclass | `dataclasses.asdict(value)` recursively |
| anything else | `TypeError` |

### Operation shape rules

| `operation` | `prev` | `new` |
|-------------|--------|-------|
| `create` | `None` | required |
| `update` | required | required |
| `delete` | required | `None` |
| `undelete` | `None` | required |

Enforced in-code. A violation is a repository bug.

### Transactional contract

- The helper runs on the caller's `sqlite3.Connection`. SQLite's `with conn:` context opens a BEGIN DEFERRED by default; the repository function that calls `write_audit` must wrap both the mutation and the audit insert within one `with conn:` block.
- `write_audit` never commits. It only inserts and relies on the caller's context manager to commit/rollback.

## Interfaces / contracts

Already covered in the signature above. Explicit non-contracts:

- `write_audit` does **not** read the previous entity state from the DB. The caller supplies `prev`. This keeps the helper fast and lets the caller choose the shape (frequently `dataclasses.asdict(old_entity)`).
- `write_audit` does **not** validate that `entity_type` matches a known table. The field is a free string documented in ADR-0019 (`'transaction' | 'planned_transaction' | 'recurring_rule' | 'recurring_rule_override' | 'account' | 'category' | 'budget_default' | 'budget_recurring_override' | 'budget_one_off_override' | 'account_snapshot'`). A new entity added later just picks a new string; no code change here.
- Not thread-safe. SQLite + single connection is single-threaded anyway in v1.

```python
class AuditShapeError(ValueError): ...
```

## Test strategy

Fixtures:

- `audit_conn`: temp SQLite with the `audit_log` table from migration.
- `frozen_dt`: a fixed `datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)` for determinism.

Cases (≥ 90 % coverage required for a tiny module):

1. **Create**: `write_audit(conn, "transaction", 42, "create", None, {"a": 1})` inserts one row with `prev_json IS NULL`, `new_json == '{"a": 1}'`, correct `changed_at`.
2. **Update**: both JSON columns populated.
3. **Delete**: `new_json IS NULL`, `prev_json` populated.
4. **Undelete**: `prev_json IS NULL`, `new_json` populated.
5. **Shape violations**:
   - `operation="create"` with `prev != None` → `AuditShapeError`.
   - `operation="create"` with `new is None` → `AuditShapeError`.
   - `operation="update"` with `new is None` → `AuditShapeError`.
   - `operation="delete"` with `prev is None` → `AuditShapeError`.
   - `operation="undelete"` with `prev is not None` → `AuditShapeError`.
   - Unknown operation string → `AuditShapeError` (narrows Literal at runtime).
6. **`changed_at` default**: when omitted, inserted value is within a few seconds of `datetime.now(UTC)`. Use `freeze_dt` fixture (or `freezegun`) to assert equality.
7. **Sort-stable JSON**: inserting the same dict twice (keys in different insertion order) produces identical `new_json` strings.
8. **`_json_default` handles dates**: `prev={"operation_date": date(2026, 1, 15)}` serialises to `"2026-01-15"`.
9. **`_json_default` handles Decimal**: `Decimal("4.3100")` serialises to `"4.3100"` (string, not float).
10. **`_json_default` handles enums**: `Direction.income` serialises to `"income"`.
11. **`_json_default` handles dataclasses**: a frozen dataclass round-trips via `asdict`.
12. **Unserialisable type raises `TypeError`**: a plain object with no `__dict__` convertible path.
13. **No implicit commit**: wrap in a `with conn:` block that raises after `write_audit`; the row must be absent (`SELECT COUNT(*) == 0`).
14. **Return value**: assert `write_audit(...) == conn.execute("SELECT last_insert_rowid()").fetchone()[0]`.

Mocking boundaries: none. Live SQLite temp DB.

## Risks & gotchas

- **Called twice silently**: a repository that writes the audit row AND lets a transaction trigger / another helper double-write would produce duplicate rows. Convention: `write_audit` is the only path; no SQL triggers (ADR-0019 alternative explicitly rejected). Review `grep -R "INSERT INTO audit_log"` as a lint-style check in CI (optional, document).
- **JSON precision**: `float` in `new` would lose precision. All amounts flow as `int` (minor units) or `Decimal` (FX rates); `_json_default` handles both. A rogue float will serialise with `repr`-level precision — surprising but not corrupting. Tests do not assert on floats to avoid false positives, but a lint warning in the service docstring is appropriate.
- **UTC vs local time**: ADR-0007 says `changed_at` is UTC. The helper always stamps UTC; routers that render for the user convert to display timezone.
- **Caller must open a transaction**: if a repository invokes `write_audit` with autocommit mode (`conn.isolation_level is None`), each insert commits immediately. In v1 the DB connection is opened with the default deferred isolation level (as per Phase 1 T-013 plan). Document in the module docstring and add a defensive assertion in `write_audit` that `conn.in_transaction is True` is **not** required (SQLite's `in_transaction` flips to `True` on the first write within a `with conn:` block, which is after the helper runs its first query). Skipping the defensive assertion for simplicity; the rollback test (13) is the regression guard.
- **`entity_type` typos**: a typo (`"transction"`) will store silently. Phase 1 T-013's repository functions each hard-code their `entity_type` string in one place per repo, which caps blast radius.
- **No partial field diffs**: `prev_json` / `new_json` carry the full snapshot. Historical diffs are reconstructed by consumers (future "revert this edit" feature per ADR-0019 consequences). Do not try to store diffs — hurts replay.
- **PII**: free-text descriptions on transactions land in audit JSON verbatim. The system is single-user local in v1 (ADR-0005); fine. Note for v2 if the DB is ever persisted off the local machine.

## Handoff notes

Phase 2 consumers:

- **No service calls this helper directly.** Services perform mutations via repositories (T-013), and those repositories call `write_audit`. Services remain audit-free in their body, which keeps them pure and test-trivial.

Phase 1 integration point:

- Every mutating function in `repositories/*.py` wraps its SQL in a `with conn:` block, calls `write_audit` with the before/after snapshots, and returns the mutated entity. The suggested convention (from Phase 1 T-013) is a shared `_mutate(conn, entity_type, entity_id, operation, prev, do_mutation) -> new` wrapper that calls `do_mutation()` then `write_audit(...)`.

Future ADR:

- Phase 1 T-013 is expected to introduce a new ADR formalising the repository/audit pattern. When it lands, update the "ADRs" section above to reference it and remove the ADR-0022 disclaimer in `docs/plans/phase-2/README.md`.
