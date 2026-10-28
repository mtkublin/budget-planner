-- migrations/0009_recurring_override_promoted_fk.sql
-- ADR-0044: soft-consume recurring overrides on promotion.
-- Adds a nullable `promoted_to_txn_id` column to `recurring_rule_overrides`
-- so the override row survives promotion (ADR-0038 §Promotion-flow step 6e
-- amended). Keeps overrides visible to historical reads so formula compute
-- (ADR-0043) continues to see B's override when materialising A's amount
-- after B's promotion.
--
-- Additive. No table rebuild, no FK pragma toggle needed.

ALTER TABLE recurring_rule_overrides
ADD COLUMN promoted_to_txn_id INTEGER
REFERENCES transactions (id) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX ix_recurring_overrides_promoted
ON recurring_rule_overrides (rule_id, promoted_to_txn_id);
