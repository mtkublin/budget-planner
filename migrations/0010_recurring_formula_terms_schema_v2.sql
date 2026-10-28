-- migrations/0010_recurring_formula_terms_schema_v2.sql
-- ADR-0047: transform `recurring_rules.amount_formula` JSON from v1 shape
-- (single implicit term) to v2 shape (list of signed terms + schema_version).
--
-- No SQL schema change. The data transform lives in a Python post-apply
-- hook registered in `src/budget_planner/db/migrate._POST_APPLY_HOOKS` so
-- the rewrite can use `json.loads` + `json.dumps` instead of SQLite's
-- json1 (works even if json1 is not statically linked). The hook is
-- idempotent: it checks `schema_version` and skips rows already at v2.
--
-- Without this file the hook never fires (hooks are keyed by migration
-- version). SELECT 1 keeps the file non-empty for the migration runner.

SELECT 1;
