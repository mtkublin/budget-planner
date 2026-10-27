# T-096 — Migration `0005_user_preferences.sql`

> Phase 9 — Left Daily Spend. Status: pending.

## Purpose

Create the `user_preferences` table so Phase 9 (and every future per-user preference) has a home. One migration file, idempotent, no seed row.

## Inputs / prerequisites

- Upstream tasks: T-095 (ADR + requirements + task scaffolding).
- Binding standard: [`ADR-0025`](../../../adr/0025-user-preferences-and-income-anchor.md).
- Adjacent precedent: `migrations/0004_add_liability_columns.sql` (Phase 7 — idempotent pattern) and `migrations/0001_schema_meta.sql` through `migrations/0003_seed_system_rows.sql` for formatting conventions.
- Framework: hand-rolled numbered `.sql` files + runner in `src/budget_planner/db/migrate.py` (ADR-0003, T-010).

## Deliverables

New file: `migrations/0005_user_preferences.sql`.

Schema (ADR-0025 § Decision 1):

```sql
CREATE TABLE IF NOT EXISTS user_preferences (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    key         TEXT    NOT NULL,
    value       TEXT    NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);
```

Not deliverables:

- No seed row — v1 ships with the anchor unset by default; the UI handles the "no preference" path via its F4.6 fallback.
- No `deleted_at` column, no soft-delete support, no `audit_log` entry on mutation. Deliberately out of scope per ADR-0025.
- No index beyond the `UNIQUE(user_id, key)` constraint — v1 single-user workloads do not need a secondary index.

## Step-by-step

1. Create `migrations/0005_user_preferences.sql` with the `CREATE TABLE IF NOT EXISTS` statement above plus a short SQL comment header `-- 0005: user_preferences (ADR-0025)` on line 1.
2. Keep the file under 20 lines; one statement, trailing newline. `sqlfluff` config in `pyproject.toml` governs style.
3. Verify the migration file is picked up by the runner: `python -m budget_planner.db.migrate --dry-run` lists `0005_user_preferences.sql` as pending on a DB without it, applied on a DB that already has it.

## Validation / acceptance

- `just migrate` applies cleanly on a fresh DB (`just db-reset && just migrate`).
- `just migrate` re-run on an already-migrated DB is a no-op (`schema_migrations` ledger shows one row for `0005`, checksum stable).
- `sqlite3 data/budget.sqlite ".schema user_preferences"` returns the exact DDL.
- `sqlite3 data/budget.sqlite "INSERT INTO user_preferences(user_id, key, value) VALUES (1, 'x', 'a'); INSERT INTO user_preferences(user_id, key, value) VALUES (1, 'x', 'b');"` fails with the `UNIQUE constraint failed: user_preferences.user_id, user_preferences.key` error.
- `pytest tests/unit/db/test_core_schema.py` (if present) still passes; add a new test under `tests/unit/db/` only if it is cheap — otherwise defer to the integration migration test added by T-097.
- `just lint` — `sqlfluff` is happy.

## Risks & gotchas

- **FK to `users(id)`.** `users` is seeded via `migrations/0003_seed_system_rows.sql`; the FK is declared but SQLite enforces it only if `PRAGMA foreign_keys = ON`. The runtime connection enables this (`src/budget_planner/db/connection.py`), so the FK is live for every real use. CLI direct SQLite shells need `PRAGMA foreign_keys = ON;` to see enforcement.
- **`CURRENT_TIMESTAMP` default.** Matches `accounts.created_at` / `categories.created_at` convention. All timestamps stay UTC per ADR-0007.
- **Column order matters for the checksum.** Do not reorder after the first apply or the migrate runner's checksum guard will refuse the second run.
- **No `ON UPDATE` trigger for `updated_at`.** Mutations go through the repository layer (T-097), which sets `updated_at = CURRENT_TIMESTAMP` explicitly. Avoid trigger magic to keep the write path visible.

## Handoff notes

- Hand-off to T-097: the hydrator in `repositories/preferences.py` reads `(id, user_id, key, value, created_at, updated_at)` in that order. Preserve column order.
- Commit shape: `feat(T-096): user_preferences table (ADR-0025)`.
