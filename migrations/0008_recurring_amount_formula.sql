-- migrations/0008_recurring_amount_formula.sql
-- ADR-0045: formula-derived recurring amount.
-- Adds a nullable `amount_formula TEXT` column storing a JSON blob of
-- `{coefficient_bps, source_category_ids}` and relaxes the `default_amount`
-- CHECK so formula rules may snapshot `default_amount = 0` when their
-- source rules sum to zero at save time.
--
-- Fixed rules (`amount_formula IS NULL`) still require `default_amount <> 0`.
-- Live callers (expand / promote / render) always recompute from the formula;
-- `default_amount` on a formula rule is a last-computed snapshot.
--
-- Uses SQLite's 12-step table rebuild because CHECK constraints can only be
-- altered by rebuilding. FK pragma toggle is registered in `db.migrate` so
-- the pragma flips outside this file's BEGIN/COMMIT.

CREATE TABLE recurring_rules_new (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users (id),
    cadence TEXT NOT NULL CHECK (cadence IN ('monthly', 'quarterly', 'yearly')),
    start_date DATE NOT NULL,
    end_date DATE,
    category_id INTEGER NOT NULL REFERENCES categories (id),
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    dest_account_id INTEGER REFERENCES accounts (id),
    default_amount INTEGER NOT NULL,
    default_description TEXT NOT NULL DEFAULT '',
    day_of_month INTEGER CHECK (day_of_month BETWEEN 1 AND 31),
    month_of_year INTEGER CHECK (month_of_year BETWEEN 1 AND 12),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    next_due DATE NOT NULL,
    last_promoted_date DATE,
    amount_formula TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date),
    CHECK (amount_formula IS NOT NULL OR default_amount <> 0)
);

INSERT INTO recurring_rules_new (
    id, user_id, cadence, start_date, end_date, category_id, account_id,
    dest_account_id, default_amount, default_description, day_of_month,
    month_of_year, active, next_due, last_promoted_date, amount_formula,
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
    NULL AS amount_formula,
    created_at,
    updated_at,
    deleted_at
FROM recurring_rules;

DROP INDEX IF EXISTS ix_recurring_active;

DROP TABLE recurring_rules;

ALTER TABLE recurring_rules_new RENAME TO recurring_rules;

CREATE INDEX ix_recurring_active ON recurring_rules (active)
WHERE deleted_at IS NULL;
