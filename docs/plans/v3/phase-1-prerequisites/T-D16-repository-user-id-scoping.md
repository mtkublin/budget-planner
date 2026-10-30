# T-D16 — Repository `user_id` scoping sweep + static-analysis test

- **Phase**: 1 — App Prerequisites
- **Parallel-safe**: no — mechanical change touching every repository module
- **Depends on**: T-D16a
- **Blocks**: T-D17 (admin panel), T-D43 (prod smoke data-isolation assertion)
- **References**: [ADR-0022](../../../adr/0022-repository-layer-soft-delete-audit-discipline.md) (amended), [ADR-0061](../../../adr/0061-v3-multi-user-admin-bootstrap-and-data-isolation.md) §5

## Context

Repositories currently ignore `user_id` because every row carries `user_id = 1`. Multi-user turns that convenience into a bug class: a missing filter leaks another user's data. The fix is twofold — a mechanical signature change (every function takes `user_id`), and a static-analysis test that fails CI if a repository SQL statement is missing the predicate.

## Deliverables

1. **Signature sweep**. For every module under `src/budget_planner/repositories/` that queries a user-owned table, prepend `user_id: int` as the first positional argument after `conn` on every public function. User-owned tables (ADR-0061 §2):
   - `accounts`, `categories`, `transactions`, `planned_transactions`, `recurring_rules`, `budget_defaults`, `budget_recurring_overrides`, `budget_one_off_overrides`, `user_preferences`
   - `account_snapshots` — scoped via `accounts.user_id` join; function signatures still take `user_id` for symmetry and the join is enforced in SQL.
   - `recurring_rule_overrides` — scoped via `recurring_rules.user_id` join; same.
   - `webauthn_credentials`, `sessions` — new tables from T-D02, already keyed by `user_id`.
2. **SQL update**. Every SELECT/UPDATE/DELETE against a user-owned table gains `WHERE user_id = :user_id` (or an equivalent join predicate for the two FK-scoped tables). Every INSERT into a user-owned table binds `user_id = :user_id` explicitly (the migration from T-D16a dropped the `DEFAULT 1` sentinel; silent inserts would now error).
3. **Service + router thread-through**. Every service function that calls a repository takes `user_id` (or receives a `User` DTO and reads `.id` from it). Every router handler reads `request.state.user.id` and passes it in. The `user_id = 1` constant is deleted from the codebase.
4. **Audit discipline**. Every `write_audit` call in a mutation path carries `user_id = <acting_user_id>` and (for admin mutations against user rows) `actor_user_id = <admin_user_id>`.
5. **Static-analysis test** `tests/architecture/test_user_id_filter.py`:
   - Discovers every module in `src/budget_planner/repositories/` and parses the SQL literals inside each function body (`libcst` for AST + `sqlglot` for SQL parsing).
   - For every SELECT/UPDATE/DELETE whose primary table is in the user-owned-table allow-list, asserts a `user_id = ?` predicate exists in the WHERE clause (or a transitive join predicate for `account_snapshots` + `recurring_rule_overrides`).
   - For every INSERT into a user-owned table, asserts `user_id` is in the column list.
   - Explicitly whitelisted tables: `fx_rates`, `audit_log`, `schema_meta`, `migrations` (not user-owned).
   - Fails CI with a line-numbered error pointing at the offending SQL.
6. **Documentation**. Add a `## User-scoping discipline` section to the repository module docstrings (one line each) explaining the convention — "every function takes `user_id`; every SQL carries the predicate; the static test backstops the rule".

## Acceptance criteria

- `pytest tests/architecture/test_user_id_filter.py` passes against every repository module.
- Every existing repository unit test is updated to pass `user_id=1` explicitly; tests continue to pass.
- A deliberate regression test (`tests/architecture/test_user_id_filter_regression.py`) creates a tempdir repo module missing the predicate and asserts the static test fails against it.
- `just test` passes; coverage on the touched modules does not regress.
- `grep -r "user_id = 1" src/budget_planner/` returns zero application-code hits (migration/seed files allowed; a `.user-id-filter-allowlist` file lists any intentional exceptions).

## Validation hook

```sh
just test tests/architecture/test_user_id_filter.py
just test tests/architecture/test_user_id_filter_regression.py
just test  # full suite — every repository test now passes user_id explicitly
```
