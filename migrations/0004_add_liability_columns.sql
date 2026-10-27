-- migrations/0004_add_liability_columns.sql
-- Add behavioural classification + credit limit to accounts (ADR-0024).

ALTER TABLE accounts
ADD COLUMN is_liability INTEGER NOT NULL DEFAULT 0
CHECK (is_liability IN (0, 1));

ALTER TABLE accounts
ADD COLUMN credit_limit_minor INTEGER
CHECK (credit_limit_minor IS NULL OR credit_limit_minor > 0);
