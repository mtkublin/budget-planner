# T-081 — Migration `0004_add_liability_columns.sql`

> Phase 7 — Liability Accounts. Status: pending.

## Purpose

Add the two new columns on `accounts` that encode liability classification and the credit limit. The migration is additive and idempotent; existing rows take the column defaults with no backfill required.

## Inputs / prerequisites

- Upstream tasks: T-080 (docs round establishes ADR-0024, F2.1a, phase scaffolding).
- Binding standards:
  - [`ADR-0024`](../../../adr/0024-liability-accounts-and-credit-limit.md) — the shape of the two new columns.
  - [`ADR-0010`](../../../adr/0010-account-model-free-text-type.md) — descriptive `type` stays as-is.
  - [`ADR-0019`](../../../adr/0019-soft-delete-and-audit-log.md) — mutable tables carry `deleted_at`; this migration does not touch soft-delete columns.
  - Prior migration precedent: `migrations/0003_seed_system_rows.sql` (idempotency pattern, SQL style, sqlfluff config).

## Deliverables

New file: `migrations/0004_add_liability_columns.sql`.

Contents:

```sql
-- migrations/0004_add_liability_columns.sql
-- Add behavioural classification + credit limit to accounts (ADR-0024).

ALTER TABLE accounts
    ADD COLUMN is_liability INTEGER NOT NULL DEFAULT 0
    CHECK (is_liability IN (0, 1));

ALTER TABLE accounts
    ADD COLUMN credit_limit_minor INTEGER
    CHECK (credit_limit_minor IS NULL OR credit_limit_minor > 0);
```

- SQLite accepts `ADD COLUMN` idempotently through the `schema_migrations` ledger (T-010 runner skips already-applied versions by checksum). No `IF NOT EXISTS` is needed on the column itself.
- The `CHECK (is_liability IN (0, 1))` + `NOT NULL DEFAULT 0` combination mirrors `categories.is_system` (migration `0002_core_schema.sql:40`).
- The `credit_limit_minor` constraint intentionally stays permissive — only `is_liability = 1` rows will carry a value; the UI enforces presence (T-084).

New tests under `tests/unit/db/test_core_schema.py` (append to the existing module):

- `test_is_liability_default_zero_on_insert` — insert an account without specifying `is_liability`, assert the stored value is `0`.
- `test_is_liability_check_rejects_two` — insert with `is_liability = 2` raises `sqlite3.IntegrityError`.
- `test_credit_limit_check_rejects_zero` — insert with `credit_limit_minor = 0` raises; `-1` raises; `NULL` is accepted; `1` is accepted.
- `test_existing_rows_backfill_to_defaults` — apply the migration against a DB with pre-existing accounts, assert each row has `is_liability = 0` and `credit_limit_minor IS NULL`.
- `test_migration_is_idempotent_via_ledger` — run `apply_migrations` twice, assert the second run is a no-op (`schema_migrations` row count unchanged).

## Step-by-step

1. **Author the SQL file.** Keep statements standalone (no `BEGIN`/`COMMIT` — the runner wraps each file in a transaction). Follow the heading-comment style from migrations `0002`/`0003`.
2. **sqlfluff.** Run `uv run sqlfluff lint migrations/0004_add_liability_columns.sql` locally; `.sqlfluff` config already excludes `RF04`. No new rule exclusions required.
3. **Checksum stability.** The runner records a sha256 of the file bytes. Do not reformat the file after it has been applied on anyone's dev DB.
4. **Append tests** to `tests/unit/db/test_core_schema.py` next to the T-011 schema assertions. Keep tests parametrised where it tightens the matrix.
5. **No seed change.** `migrations/0003_seed_system_rows.sql` is unaffected; the demo credit-card account lands later via T-086.

## Validation / acceptance

- `just migrate` on a fresh DB applies all four migrations in order and reports `0004_add_liability_columns.sql` as applied.
- `just migrate` on a DB already at `0003` applies only `0004`.
- `just migrate` on a DB already at `0004` is a no-op.
- `uv run sqlfluff lint migrations/0004_add_liability_columns.sql` is clean.
- `pytest tests/unit/db/test_core_schema.py -q` is green with the new cases.
- `just ci` is green.

## Risks & gotchas

- **SQLite `ALTER TABLE` constraints.** SQLite applies `CHECK` constraints added via `ADD COLUMN` to new writes only; existing rows are not re-validated. That is the correct behaviour here (existing rows have `is_liability = 0` and `credit_limit_minor IS NULL`, both legal).
- **Audit log on schema change.** Schema migrations do **not** write to `audit_log` (that ledger is per-entity-row mutations, ADR-0019). Do not add inserts.
- **No backfill required.** Every existing account is implicitly an asset (`is_liability = 0`); any user-driven conversion to a liability happens through the account form (T-084), which also validates `credit_limit_minor`.
- **File ordering.** The runner sorts migrations by numeric prefix; keep `0004` strictly ascending. Do not reuse the filename for a different change.

## Handoff notes

- Hand-off to T-082: Python domain + repository modules bind to the new columns next. Field names: `is_liability: bool`, `credit_limit_minor: int | None`. Hydrator maps SQLite `0`/`1` → `bool` and `NULL` → `None`.
- Commit shape: `feat(T-081): add is_liability + credit_limit_minor on accounts (ADR-0024)`.
