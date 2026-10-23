-- migrations/0002_core_schema.sql
-- Core persistence schema. See docs/plans/phase-1/T-011-core-schema-migration.md.

-------------------------------------------------------------------------------
-- 1. users (single-user scaffold)
-------------------------------------------------------------------------------
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-------------------------------------------------------------------------------
-- 2. accounts
-------------------------------------------------------------------------------
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    name TEXT NOT NULL,
    type TEXT,
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    opening_balance INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP
);
CREATE UNIQUE INDEX ux_accounts_user_name_live
ON accounts (user_id, name)
WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 3. categories
-------------------------------------------------------------------------------
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    name TEXT NOT NULL,
    direction TEXT NOT NULL
    CHECK (direction IN ('income', 'expense', 'transit', 'adjustment')),
    is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP
);
CREATE UNIQUE INDEX ux_categories_user_name_live
ON categories (user_id, name)
WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 4. transactions
-------------------------------------------------------------------------------
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    operation_date DATE NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories (id),
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    dest_account_id INTEGER REFERENCES accounts (id),
    amount INTEGER NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    promoted_from_planned_id INTEGER
    REFERENCES planned_transactions (id) DEFERRABLE INITIALLY DEFERRED,
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP,
    CHECK (amount <> 0),
    CHECK (account_id <> dest_account_id OR dest_account_id IS NULL)
);
CREATE INDEX ix_transactions_operation_date ON transactions (operation_date);
CREATE INDEX ix_transactions_account ON transactions (account_id);
CREATE INDEX ix_transactions_dest_account ON transactions (dest_account_id);
CREATE INDEX ix_transactions_category ON transactions (category_id);
CREATE INDEX ix_transactions_live
ON transactions (operation_date)
WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 5. planned_transactions
-------------------------------------------------------------------------------
CREATE TABLE planned_transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    operation_date DATE NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories (id),
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    dest_account_id INTEGER REFERENCES accounts (id),
    amount INTEGER NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    recurring_rule_id INTEGER
    REFERENCES recurring_rules (id) DEFERRABLE INITIALLY DEFERRED,
    occurrence_date DATE,
    promoted_to_txn_id INTEGER REFERENCES transactions (id),
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP,
    CHECK (amount <> 0),
    CHECK (account_id <> dest_account_id OR dest_account_id IS NULL)
);
CREATE INDEX ix_planned_operation_date ON planned_transactions (operation_date);
CREATE INDEX ix_planned_rule ON planned_transactions (recurring_rule_id);

-------------------------------------------------------------------------------
-- 6. recurring_rules
-------------------------------------------------------------------------------
CREATE TABLE recurring_rules (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    cadence TEXT NOT NULL CHECK (cadence IN ('monthly', 'quarterly', 'yearly')),
    start_date DATE NOT NULL,
    end_date DATE,
    category_id INTEGER NOT NULL REFERENCES categories (id),
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    dest_account_id INTEGER REFERENCES accounts (id),
    default_amount INTEGER NOT NULL CHECK (default_amount <> 0),
    default_description TEXT NOT NULL DEFAULT '',
    day_of_month INTEGER CHECK (day_of_month BETWEEN 1 AND 31),
    month_of_year INTEGER CHECK (month_of_year BETWEEN 1 AND 12),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE INDEX ix_recurring_active ON recurring_rules (active)
WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 7. recurring_rule_overrides
-------------------------------------------------------------------------------
CREATE TABLE recurring_rule_overrides (
    id INTEGER PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES recurring_rules (id),
    occurrence_date DATE NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('skipped', 'overridden')),
    amount_override INTEGER,
    description_override TEXT,
    date_override DATE,
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (rule_id, occurrence_date)
);

-------------------------------------------------------------------------------
-- 8. budget_defaults
-------------------------------------------------------------------------------
CREATE TABLE budget_defaults (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    category_id INTEGER NOT NULL REFERENCES categories (id),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP
);
CREATE UNIQUE INDEX ux_budget_defaults_cat_live
ON budget_defaults (category_id)
WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 9. budget_recurring_overrides
-------------------------------------------------------------------------------
CREATE TABLE budget_recurring_overrides (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    category_id INTEGER NOT NULL REFERENCES categories (id),
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP
);
CREATE UNIQUE INDEX ux_budget_recurring_cat_month_live
ON budget_recurring_overrides (category_id, month)
WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 10. budget_one_off_overrides
-------------------------------------------------------------------------------
CREATE TABLE budget_one_off_overrides (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    category_id INTEGER NOT NULL REFERENCES categories (id),
    year INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 9999),
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP
);
CREATE UNIQUE INDEX ux_budget_one_off_cat_year_month_live
ON budget_one_off_overrides (category_id, year, month)
WHERE deleted_at IS NULL;

-------------------------------------------------------------------------------
-- 11. account_snapshots
-------------------------------------------------------------------------------
CREATE TABLE account_snapshots (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    taken_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    balance INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX ix_snapshots_account_taken_at ON account_snapshots (account_id, taken_at);

-------------------------------------------------------------------------------
-- 12. fx_rates
-------------------------------------------------------------------------------
CREATE TABLE fx_rates (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    from_ccy TEXT NOT NULL CHECK (length(from_ccy) = 3),
    to_ccy TEXT NOT NULL CHECK (length(to_ccy) = 3),
    rate TEXT NOT NULL,
    fetched_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE UNIQUE INDEX ux_fx_rates_date_pair ON fx_rates (date, from_ccy, to_ccy);
CREATE INDEX ix_fx_rates_pair_date ON fx_rates (from_ccy, to_ccy, date);

-------------------------------------------------------------------------------
-- 13. audit_log
-------------------------------------------------------------------------------
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    operation TEXT NOT NULL
    CHECK (operation IN ('create', 'update', 'delete', 'undelete')),
    prev_json TEXT,
    new_json TEXT
);
CREATE INDEX ix_audit_entity ON audit_log (entity_type, entity_id, changed_at);
