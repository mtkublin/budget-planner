# T-011 — Core Schema Migration

> Phase 1 — Data Layer. Status: pending.

## Purpose

Create every persistence table required by v1 in a single numbered migration, with CHECK constraints, foreign keys, indexes, and partial unique indexes compatible with soft delete. This is the data contract Phase 2 and 3 build on.

## Inputs / prerequisites

- Upstream task: [`T-010-migration-framework.md`](T-010-migration-framework.md) — migration runner + `0001_schema_meta.sql`.
- ADRs:
  - [`../../adr/0003-database-sqlite-only-v1.md`](../../adr/0003-database-sqlite-only-v1.md) — SQLite only.
  - [`../../adr/0005-single-user-no-auth-user-id-scaffold.md`](../../adr/0005-single-user-no-auth-user-id-scaffold.md) — every user-owned table has `user_id` scaffolded.
  - [`../../adr/0006-multi-currency-model.md`](../../adr/0006-multi-currency-model.md) — account owns currency; transactions do not.
  - [`../../adr/0007-timezone-handling.md`](../../adr/0007-timezone-handling.md) — `TIMESTAMP` UTC, `operation_date` as `DATE`.
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — amounts positive integer minor units, direction drives sign, `adjustment` is the signed exception.
  - [`../../adr/0009-transit-single-row-model.md`](../../adr/0009-transit-single-row-model.md) — single row with `dest_account_id`.
  - [`../../adr/0010-account-model-free-text-type.md`](../../adr/0010-account-model-free-text-type.md) — free-text `type`.
  - [`../../adr/0011-derived-balance-snapshots-reconciliation.md`](../../adr/0011-derived-balance-snapshots-reconciliation.md) — snapshots are additive-only.
  - [`../../adr/0013-recurring-virtual-occurrences-and-overrides.md`](../../adr/0013-recurring-virtual-occurrences-and-overrides.md) — overrides table shape.
  - [`../../adr/0014-budget-flat-no-rollover-three-tier.md`](../../adr/0014-budget-flat-no-rollover-three-tier.md) — three-tier tables.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md) — soft-delete + polymorphic `audit_log`.

## Deliverables

```
migrations/0002_core_schema.sql
tests/unit/db/test_core_schema.py
```

Tables created in `0002_core_schema.sql`:

| # | Table | Notes |
|---|-------|-------|
| 1 | `users` | Single-user scaffold. |
| 2 | `accounts` | Immutable `currency`; soft-delete; partial-unique name. |
| 3 | `categories` | Direction CHECK; `is_system` flag; partial-unique name. |
| 4 | `transactions` | Positive `amount` except direction=`adjustment`; `dest_account_id` nullable. |
| 5 | `planned_transactions` | Mirrors `transactions` + `recurring_rule_id`, `occurrence_date`, `promoted_to_txn_id`. |
| 6 | `recurring_rules` | Cadence CHECK; defaults for amount/description/accounts/category. |
| 7 | `recurring_rule_overrides` | Keyed by `(rule_id, occurrence_date)` with state CHECK. |
| 8 | `budget_defaults` | `category_id` partial-unique. |
| 9 | `budget_recurring_overrides` | `(category_id, month)` partial-unique. |
| 10 | `budget_one_off_overrides` | `(category_id, year, month)` partial-unique. |
| 11 | `account_snapshots` | Append-only; no soft-delete. |
| 12 | `fx_rates` | Append-only; no soft-delete; `(date, from_ccy, to_ccy)` unique. |
| 13 | `audit_log` | Append-only; no soft-delete; stores JSON text blobs. |

## Step-by-step

1. **Create `migrations/0002_core_schema.sql` with the DDL below.** All timestamps default to UTC via `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`. All amounts are `INTEGER` minor units.

```sql
-- migrations/0002_core_schema.sql

-------------------------------------------------------------------------------
-- 1. users (single-user scaffold)
-------------------------------------------------------------------------------
CREATE TABLE users (
    id           INTEGER     PRIMARY KEY,
    name         TEXT        NOT NULL,
    created_at   TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-------------------------------------------------------------------------------
-- 2. accounts
-------------------------------------------------------------------------------
CREATE TABLE accounts (
    id                INTEGER     PRIMARY KEY,
    user_id           INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    name              TEXT        NOT NULL,
    type              TEXT,                                   -- free-text (ADR-0010)
    currency          TEXT        NOT NULL CHECK (length(currency) = 3),
    opening_balance   INTEGER     NOT NULL DEFAULT 0,
    created_at        TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at        TIMESTAMP
);
-- Soft-delete-aware uniqueness: two accounts named "ING" can coexist iff one is deleted.
CREATE UNIQUE INDEX ux_accounts_user_name_live
    ON accounts(user_id, name) WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 3. categories
-------------------------------------------------------------------------------
CREATE TABLE categories (
    id           INTEGER     PRIMARY KEY,
    user_id      INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    name         TEXT        NOT NULL,
    direction    TEXT        NOT NULL
                             CHECK (direction IN ('income', 'expense', 'transit', 'adjustment')),
    is_system    INTEGER     NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    created_at   TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at   TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at   TIMESTAMP
);
CREATE UNIQUE INDEX ux_categories_user_name_live
    ON categories(user_id, name) WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 4. transactions
-------------------------------------------------------------------------------
CREATE TABLE transactions (
    id                        INTEGER     PRIMARY KEY,
    user_id                   INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    operation_date            DATE        NOT NULL,
    category_id               INTEGER     NOT NULL REFERENCES categories(id),
    account_id                INTEGER     NOT NULL REFERENCES accounts(id),
    dest_account_id           INTEGER              REFERENCES accounts(id),
    amount                    INTEGER     NOT NULL,                 -- minor units
    description               TEXT        NOT NULL DEFAULT '',
    promoted_from_planned_id  INTEGER              REFERENCES planned_transactions(id)
                                                   DEFERRABLE INITIALLY DEFERRED,
    created_at                TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at                TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at                TIMESTAMP,
    CHECK (amount <> 0),
    CHECK (account_id <> dest_account_id OR dest_account_id IS NULL)
);
CREATE INDEX ix_transactions_operation_date ON transactions(operation_date);
CREATE INDEX ix_transactions_account        ON transactions(account_id);
CREATE INDEX ix_transactions_dest_account   ON transactions(dest_account_id);
CREATE INDEX ix_transactions_category       ON transactions(category_id);
CREATE INDEX ix_transactions_live
    ON transactions(operation_date) WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 5. planned_transactions
-------------------------------------------------------------------------------
CREATE TABLE planned_transactions (
    id                       INTEGER     PRIMARY KEY,
    user_id                  INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    operation_date           DATE        NOT NULL,
    category_id              INTEGER     NOT NULL REFERENCES categories(id),
    account_id               INTEGER     NOT NULL REFERENCES accounts(id),
    dest_account_id          INTEGER              REFERENCES accounts(id),
    amount                   INTEGER     NOT NULL,
    description              TEXT        NOT NULL DEFAULT '',
    recurring_rule_id        INTEGER              REFERENCES recurring_rules(id)
                                                  DEFERRABLE INITIALLY DEFERRED,
    occurrence_date          DATE,                                 -- when materialised from a rule
    promoted_to_txn_id       INTEGER              REFERENCES transactions(id),
    created_at               TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at               TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at               TIMESTAMP,
    CHECK (amount <> 0),
    CHECK (account_id <> dest_account_id OR dest_account_id IS NULL)
);
CREATE INDEX ix_planned_operation_date ON planned_transactions(operation_date);
CREATE INDEX ix_planned_rule           ON planned_transactions(recurring_rule_id);

-------------------------------------------------------------------------------
-- 6. recurring_rules
-------------------------------------------------------------------------------
CREATE TABLE recurring_rules (
    id                     INTEGER     PRIMARY KEY,
    user_id                INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    cadence                TEXT        NOT NULL
                                       CHECK (cadence IN ('monthly', 'quarterly', 'yearly')),
    start_date             DATE        NOT NULL,
    end_date               DATE,
    category_id            INTEGER     NOT NULL REFERENCES categories(id),
    account_id             INTEGER     NOT NULL REFERENCES accounts(id),
    dest_account_id        INTEGER              REFERENCES accounts(id),
    default_amount         INTEGER     NOT NULL CHECK (default_amount <> 0),
    default_description    TEXT        NOT NULL DEFAULT '',
    day_of_month           INTEGER              CHECK (day_of_month BETWEEN 1 AND 31),
    month_of_year          INTEGER              CHECK (month_of_year BETWEEN 1 AND 12),
    active                 INTEGER     NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at             TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at             TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at             TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE INDEX ix_recurring_active ON recurring_rules(active) WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 7. recurring_rule_overrides
-------------------------------------------------------------------------------
CREATE TABLE recurring_rule_overrides (
    id                     INTEGER     PRIMARY KEY,
    rule_id                INTEGER     NOT NULL REFERENCES recurring_rules(id),
    occurrence_date        DATE        NOT NULL,
    state                  TEXT        NOT NULL CHECK (state IN ('skipped', 'overridden')),
    amount_override        INTEGER,
    description_override   TEXT,
    date_override          DATE,
    created_at             TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (rule_id, occurrence_date)
);

-------------------------------------------------------------------------------
-- 8. budget_defaults
-------------------------------------------------------------------------------
CREATE TABLE budget_defaults (
    id            INTEGER     PRIMARY KEY,
    user_id       INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    category_id   INTEGER     NOT NULL REFERENCES categories(id),
    amount        INTEGER     NOT NULL CHECK (amount >= 0),
    created_at    TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at    TIMESTAMP
);
CREATE UNIQUE INDEX ux_budget_defaults_cat_live
    ON budget_defaults(category_id) WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 9. budget_recurring_overrides
-------------------------------------------------------------------------------
CREATE TABLE budget_recurring_overrides (
    id            INTEGER     PRIMARY KEY,
    user_id       INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    category_id   INTEGER     NOT NULL REFERENCES categories(id),
    month         INTEGER     NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount        INTEGER     NOT NULL CHECK (amount >= 0),
    created_at    TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at    TIMESTAMP
);
CREATE UNIQUE INDEX ux_budget_recurring_cat_month_live
    ON budget_recurring_overrides(category_id, month) WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 10. budget_one_off_overrides
-------------------------------------------------------------------------------
CREATE TABLE budget_one_off_overrides (
    id            INTEGER     PRIMARY KEY,
    user_id       INTEGER     NOT NULL DEFAULT 1 REFERENCES users(id),
    category_id   INTEGER     NOT NULL REFERENCES categories(id),
    year          INTEGER     NOT NULL CHECK (year BETWEEN 1900 AND 9999),
    month         INTEGER     NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount        INTEGER     NOT NULL CHECK (amount >= 0),
    created_at    TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at    TIMESTAMP
);
CREATE UNIQUE INDEX ux_budget_one_off_cat_year_month_live
    ON budget_one_off_overrides(category_id, year, month) WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 11. account_snapshots
-------------------------------------------------------------------------------
CREATE TABLE account_snapshots (
    id           INTEGER     PRIMARY KEY,
    account_id   INTEGER     NOT NULL REFERENCES accounts(id),
    taken_at     TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    balance      INTEGER     NOT NULL,                   -- minor units, signed
    note         TEXT        NOT NULL DEFAULT ''
);
CREATE INDEX ix_snapshots_account_taken_at ON account_snapshots(account_id, taken_at);

-------------------------------------------------------------------------------
-- 12. fx_rates
-------------------------------------------------------------------------------
CREATE TABLE fx_rates (
    id          INTEGER     PRIMARY KEY,
    date        DATE        NOT NULL,
    from_ccy    TEXT        NOT NULL CHECK (length(from_ccy) = 3),
    to_ccy      TEXT        NOT NULL CHECK (length(to_ccy) = 3),
    rate        TEXT        NOT NULL,                    -- Decimal stored as TEXT
    fetched_at  TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE UNIQUE INDEX ux_fx_rates_date_pair ON fx_rates(date, from_ccy, to_ccy);
CREATE INDEX ix_fx_rates_pair_date ON fx_rates(from_ccy, to_ccy, date);

-------------------------------------------------------------------------------
-- 13. audit_log
-------------------------------------------------------------------------------
CREATE TABLE audit_log (
    id            INTEGER     PRIMARY KEY,
    entity_type   TEXT        NOT NULL,
    entity_id     INTEGER     NOT NULL,
    changed_at    TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    operation     TEXT        NOT NULL
                              CHECK (operation IN ('create', 'update', 'delete', 'undelete')),
    prev_json     TEXT,
    new_json      TEXT
);
CREATE INDEX ix_audit_entity ON audit_log(entity_type, entity_id, changed_at);
```

2. **Tests** (`tests/unit/db/test_core_schema.py`), applied against a temp DB after `apply_migrations`:
   - All 13 tables listed above exist in `sqlite_master`.
   - All indexes above exist.
   - `PRAGMA foreign_keys` is on; attempting an insert with a bad `category_id` raises `IntegrityError`.
   - `categories.direction = 'elephant'` raises `IntegrityError`.
   - `recurring_rules.cadence = 'daily'` raises `IntegrityError`.
   - `transactions.amount = 0` raises.
   - `transactions.account_id = dest_account_id` with a non-null dest raises.
   - Inserting two live accounts with the same name raises; after soft-deleting the first, inserting the second succeeds; a third live insert then raises again.
   - `fx_rates(2026-01-15, EUR, PLN)` can be inserted twice only after deleting the first (unique on `(date, from_ccy, to_ccy)`).
   - `audit_log.operation = 'other'` raises.

## Interfaces / contracts

Final table names Phase 2 and 3 depend on:

```
users
accounts (id, user_id, name, type, currency, opening_balance, created_at, updated_at, deleted_at)
categories (id, user_id, name, direction, is_system, created_at, updated_at, deleted_at)
transactions (id, user_id, operation_date, category_id, account_id, dest_account_id,
              amount, description, promoted_from_planned_id,
              created_at, updated_at, deleted_at)
planned_transactions (id, user_id, operation_date, category_id, account_id, dest_account_id,
                      amount, description, recurring_rule_id, occurrence_date,
                      promoted_to_txn_id, created_at, updated_at, deleted_at)
recurring_rules (id, user_id, cadence, start_date, end_date, category_id, account_id,
                 dest_account_id, default_amount, default_description,
                 day_of_month, month_of_year, active, created_at, updated_at, deleted_at)
recurring_rule_overrides (id, rule_id, occurrence_date, state,
                          amount_override, description_override, date_override, created_at)
budget_defaults (id, user_id, category_id, amount, created_at, updated_at, deleted_at)
budget_recurring_overrides (id, user_id, category_id, month, amount,
                            created_at, updated_at, deleted_at)
budget_one_off_overrides (id, user_id, category_id, year, month, amount,
                          created_at, updated_at, deleted_at)
account_snapshots (id, account_id, taken_at, balance, note)
fx_rates (id, date, from_ccy, to_ccy, rate, fetched_at)
audit_log (id, entity_type, entity_id, changed_at, operation, prev_json, new_json)
```

Column semantics that other phases rely on:

- `transactions.amount`: positive integer except when the category direction is `adjustment` (ADR-0008). CHECK enforces `<> 0` only; sign validation lives in services.
- `accounts.currency`: ISO 4217; CHECK enforces length 3 only.
- `fx_rates.rate`: stored as `TEXT` to preserve `Decimal` precision; services call `Decimal(row["rate"])`.
- `recurring_rule_overrides.state ∈ {skipped, overridden}` and sparse per ADR-0013.
- `account_snapshots` is append-only (no `deleted_at`); ADR-0011.
- `audit_log` is append-only.

## Validation / acceptance

- `just db-reset && just migrate` runs 0001 + 0002 and prints both applied lines.
- `just test tests/unit/db/` green with the schema integrity assertions above.
- `sqlfluff` passes on `migrations/*.sql` (dialect = `sqlite`).
- Phase-1 exit criterion satisfied: "`just migrate` applies the schema from zero".

## Risks & gotchas

- **Forward reference between `transactions` and `planned_transactions`.** The FK is defined with `DEFERRABLE INITIALLY DEFERRED`; SQLite accepts the keyword but still resolves names in-order inside a single transaction. The circular reference is only closed when both tables exist, so ensure both `CREATE TABLE` statements run in the same `executescript` (they do — they are both inside `0002_core_schema.sql`).
- **Partial unique indexes.** `WHERE deleted_at IS NULL` is a SQLite 3.8+ feature; required by soft-delete semantics (ADR-0019). Without it, soft-deleting a row would permanently burn its name.
- **DATE vs TIMESTAMP.** `operation_date` is `DATE` (no time), `taken_at` is `TIMESTAMP` (UTC) — ADR-0007. Tests must not conflate them.
- **Decimals.** `fx_rates.rate` is stored as `TEXT` to avoid `float` drift; the domain layer parses with `Decimal`.
- **`is_system` is new.** Not listed in `docs/tasks.md`; it exists so T-012 can mark Transit and Reconciliation as undeletable without a hard-coded id lookup. Call this out in the task's PR description.
- **Amount sign enforcement.** `CHECK (amount <> 0)` only; the signed-vs-unsigned rule by direction is enforced at the service layer (ADR-0008) because SQLite CHECKs cannot peek at the joined `categories.direction`.
- **No `pragma_table_info` snapshot test.** Avoid brittle snapshot comparisons — assert on existence + specific constraints only.

## Handoff notes

- T-012 inserts the single `users` row and the two system categories into this schema.
- T-013 opens every repository against these tables. The `_mutate` helper joins `transactions` and `categories` to validate direction/sign at write time.
- T-014 mirrors the table columns as frozen dataclasses.
