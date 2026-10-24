# T-012 — Seed Data Migration

> Phase 1 — Data Layer. Status: pending.

## Purpose

Seed the single-user row and the two system-managed categories (`Transit`, `Reconciliation`) that services depend on. These rows are inserted via a migration so a fresh DB is immediately usable; service-layer guards prevent them from being deleted or renamed.

## Inputs / prerequisites

- Upstream task: [`T-011-core-schema-migration.md`](T-011-core-schema-migration.md) — core tables + `categories.is_system` column exist.
- ADRs:
  - [`../../adr/0005-single-user-no-auth-user-id-scaffold.md`](../../adr/0005-single-user-no-auth-user-id-scaffold.md) — default `user_id = 1`.
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — `adjustment` direction used by `Reconciliation`.
  - [`../../adr/0009-transit-single-row-model.md`](../../adr/0009-transit-single-row-model.md) — seeded `Transit` category.
  - [`../../adr/0011-derived-balance-snapshots-reconciliation.md`](../../adr/0011-derived-balance-snapshots-reconciliation.md) — `Reconciliation` category feeds the reconciliation flow.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md) — seed rows must not acquire a `deleted_at`.

## Deliverables

```
migrations/0003_seed_system_rows.sql
tests/unit/db/test_seed_data.py
src/budget_planner/domain/system_categories.py   # name constants (shared with service guards)
```

## Step-by-step

1. **Add shared constants** so services and tests do not stringly-type the system names:

   ```python
   # src/budget_planner/domain/system_categories.py
   from __future__ import annotations

   from typing import Final

   TRANSIT_CATEGORY_NAME: Final[str] = "Transit"
   RECONCILIATION_CATEGORY_NAME: Final[str] = "Reconciliation"

   SYSTEM_CATEGORY_NAMES: Final[frozenset[str]] = frozenset(
       {TRANSIT_CATEGORY_NAME, RECONCILIATION_CATEGORY_NAME}
   )
   ```

2. **Write `migrations/0003_seed_system_rows.sql`:**

   ```sql
   -- migrations/0003_seed_system_rows.sql

   -- Single-user scaffold (ADR-0005).
   INSERT INTO users (id, name) VALUES (1, 'default')
       ON CONFLICT (id) DO NOTHING;

   -- System categories (ADR-0008 / ADR-0009 / ADR-0011).
   -- These are undeletable; enforcement lives in the service layer (categories service).
   INSERT INTO categories (user_id, name, direction, is_system)
   VALUES (1, 'Transit', 'transit', 1)
       ON CONFLICT (user_id, name) WHERE deleted_at IS NULL DO NOTHING;

   INSERT INTO categories (user_id, name, direction, is_system)
   VALUES (1, 'Reconciliation', 'adjustment', 1)
       ON CONFLICT (user_id, name) WHERE deleted_at IS NULL DO NOTHING;

   -- Seed inserts bypass the audit log by design; this is a schema-level fact,
   -- not a user action, so no audit_log row is written here.
   ```

3. **Tests** (`tests/unit/db/test_seed_data.py`), applied after `apply_migrations(conn)` on a temp DB:
   - `SELECT count(*) FROM users WHERE id = 1` returns 1.
   - `SELECT direction, is_system FROM categories WHERE name = 'Transit'` returns `('transit', 1)`.
   - `SELECT direction, is_system FROM categories WHERE name = 'Reconciliation'` returns `('adjustment', 1)`.
   - Re-applying `apply_migrations` is idempotent (the `ON CONFLICT ... DO NOTHING` holds; no duplicate rows).
   - `audit_log` is empty immediately after seed (seed is schema-level, not user action).

## Interfaces / contracts

Public surface:

- `TRANSIT_CATEGORY_NAME`, `RECONCILIATION_CATEGORY_NAME`, `SYSTEM_CATEGORY_NAMES` from `budget_planner.domain.system_categories`.
- Both system categories exist with `is_system = 1` for `user_id = 1` after `apply_migrations`.
- `is_system = 1` ↔ "service layer must reject delete, rename, and direction change".

Service-layer guard contract (implemented in T-013 / Phase 2 category service, documented here so no caller is surprised):

```python
# Pseudocode of the guard; actual implementation lives in services.categories.
def delete_category(conn, category_id: int) -> None:
    row = find_by_id(conn, category_id)
    if row is None:
        raise NotFound
    if row.is_system:
        raise SystemCategoryProtected(row.name)
    soft_delete(conn, category_id)
```

## Validation / acceptance

- `just db-reset && just migrate` lands all three migrations and leaves exactly:
  - 1 row in `users`,
  - 2 rows in `categories` (both `is_system = 1`),
  - 0 rows in every other table including `audit_log`.
- `just test tests/unit/db/test_seed_data.py` green.
- Phase-1 exit criterion: seed data is present on a freshly migrated DB; soft-delete filter still default-on in `categories` reads (T-013).

## Risks & gotchas

- **`ON CONFLICT` with a partial unique index.** The conflict target must match the partial-index predicate (`ON CONFLICT (user_id, name) WHERE deleted_at IS NULL`). SQLite 3.35+ supports this; required for idempotent seed.
- **No audit entry on seed.** Seeds are schema-level facts. Services that later rename or edit the user row *do* write audit entries; the initial insert does not. Documented so Phase 4 e2e tests do not expect audit rows after `just migrate`.
- **`is_system` flag is enforcement data, not display data.** UI must still render Transit and Reconciliation like any other category; it only prevents destructive operations.
- **Future auth migration.** When multi-user auth lands (post-v1), this seed will need per-user duplication. Document the hard-coded `user_id = 1` here as a known debt.
- **No `opening_balance` here.** Accounts are user-created at runtime, not seeded. The scope guard in CLAUDE.md section 3.8 forbids adding demo accounts in v1 seeding.

## Handoff notes

- T-013 category repository exposes `is_system` on the dataclass (T-014) and refuses mutation/delete when `is_system = 1`.
- Phase 2 reconciliation service (`services.reconciliation`) looks up the category by `name = RECONCILIATION_CATEGORY_NAME` — never by hard-coded id.
- Phase 3 UI filters system categories out of "delete" affordances by reading `is_system`.
