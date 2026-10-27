-- migrations/0006_add_recurring_next_due.sql
-- ADR-0038: Recurring Rules Standalone Lifecycle.
--
-- Additive columns + index. `recurring_rules.next_due` lands nullable so the
-- Python post-apply hook (`db/migrate._backfill_recurring_next_due`) can
-- populate it using the pure occurrence generator. Migration 0007 flips the
-- column to NOT NULL via SQLite's 12-step table rebuild once the backfill
-- is complete.

ALTER TABLE recurring_rules ADD COLUMN next_due DATE;

ALTER TABLE recurring_rules ADD COLUMN last_promoted_date DATE;

ALTER TABLE transactions
ADD COLUMN promoted_from_recurring_rule_id INTEGER
REFERENCES recurring_rules (id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE transactions ADD COLUMN promoted_from_recurring_date DATE;

CREATE INDEX ix_transactions_promoted_from_recurring
ON transactions (promoted_from_recurring_rule_id, promoted_from_recurring_date);
