-- migrations/0003_seed_system_rows.sql
-- Idempotent seed: single user + system categories (Transit, Reconciliation).
-- Enforcement of the "undeletable" invariant lives in the service layer via
-- `categories.is_system = 1`. Seed inserts bypass `audit_log` by design.

INSERT INTO users (id, name)
VALUES (1, 'default')
ON CONFLICT (id) DO NOTHING;

INSERT INTO categories (user_id, name, direction, is_system)
VALUES (1, 'Transit', 'transit', 1)
ON CONFLICT (user_id, name) WHERE deleted_at IS NULL DO NOTHING;

INSERT INTO categories (user_id, name, direction, is_system)
VALUES (1, 'Reconciliation', 'adjustment', 1)
ON CONFLICT (user_id, name) WHERE deleted_at IS NULL DO NOTHING;
