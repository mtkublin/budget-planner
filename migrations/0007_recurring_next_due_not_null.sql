-- migrations/0007_recurring_next_due_not_null.sql
-- ADR-0038 step 2: flip `recurring_rules.next_due` to NOT NULL via SQLite's
-- 12-step table rebuild. 0006 added the column nullable so the Python
-- backfill hook could populate it; by the time 0007 applies, every row has
-- `next_due` set (asserted by the integration test).
--
-- The migration runner toggles `PRAGMA foreign_keys = OFF` around this file
-- (see `db/migrate.FK_OFF_MIGRATIONS`) because other tables
-- (`planned_transactions`, `recurring_rule_overrides`, and after 0006 also
-- `transactions`) carry foreign keys pointing at `recurring_rules`. The
-- pragma must flip outside the migration's BEGIN/COMMIT, so the toggle
-- lives in Python; `PRAGMA foreign_key_check` after the rebuild lets us
-- fail fast if the rebuild corrupted a reference.

CREATE TABLE recurring_rules_new (
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
    next_due DATE NOT NULL,
    last_promoted_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

INSERT INTO recurring_rules_new (
    id, user_id, cadence, start_date, end_date, category_id, account_id,
    dest_account_id, default_amount, default_description, day_of_month,
    month_of_year, active, next_due, last_promoted_date,
    created_at, updated_at, deleted_at
)
SELECT
    id,
    user_id,
    cadence,
    start_date,
    end_date,
    category_id,
    account_id,
    dest_account_id,
    default_amount,
    default_description,
    day_of_month,
    month_of_year,
    active,
    next_due,
    last_promoted_date,
    created_at,
    updated_at,
    deleted_at
FROM recurring_rules;

DROP INDEX IF EXISTS ix_recurring_active;

DROP TABLE recurring_rules;

ALTER TABLE recurring_rules_new RENAME TO recurring_rules;

CREATE INDEX ix_recurring_active ON recurring_rules (active)
WHERE deleted_at IS NULL;
