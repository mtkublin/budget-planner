# T-D19 — Admin bootstrap on startup

- **Phase**: 1 — App Prerequisites
- **Parallel-safe**: no — depends on migration + auth
- **Depends on**: T-D02, T-D16a
- **Blocks**: T-D23 (cloud-init needs the env-var contract), T-D25 (first drill apply), T-D27 (first prod apply), T-D43 (smoke)
- **References**: [ADR-0061](../../../adr/0061-v3-multi-user-admin-bootstrap-and-data-isolation.md) §3

## Context

The admin is created idempotently at process startup from two environment variables injected by cloud-init: `BUDGET_PLANNER_ADMIN_EMAIL` and `BUDGET_PLANNER_ADMIN_INITIAL_PASSWORD`. The password is generated once by Terraform (`random_password`) and surfaced as a sensitive output for the operator to capture into a password manager. The app does **not** continuously reconcile — rotating the Terraform variable does not change an existing admin's password; recovery is "set env + rebuild DB" per the disaster-recovery runbook.

## Deliverables

1. **Service** `src/budget_planner/services/users.py::bootstrap_admin(conn, env)`:
   - If any `is_admin = 1 AND deleted_at IS NULL` user exists → no-op; log `event="admin_bootstrap", action="noop"`.
   - Else read `env.admin_email` + `env.admin_initial_password`:
     - If either is missing → raise `BootstrapAdminMissingEnv` with a clear message. Startup catches it and exits non-zero after logging.
     - If a user with that email already exists but is not admin → set `is_admin = 1`, update `password_hash`, set `must_change_password = 1`; log `action="promoted"`.
     - Else insert a new user with those values + seed per-user system categories (`Transit`, `Reconciliation`) in the same transaction; log `action="created"`.
   - Audit log row with `entity_type='users'`, `operation='create'|'update'`, `actor_user_id=NULL`, `new_json={...redacted...}` (password hash and plaintext are **never** in `new_json`).
2. **Lifespan hook** in `src/budget_planner/web/app.py`:
   - On startup (after migrations), open a DB connection and call `bootstrap_admin(conn, settings)`.
   - If the service raises `BootstrapAdminMissingEnv` and no admin exists → `sys.exit(1)` after logging. If an admin exists, missing env is a no-op (continue startup).
3. **Config** `src/budget_planner/config.py`:
   - Add `admin_email: EmailStr | None` and `admin_initial_password: SecretStr | None` (pydantic-settings). Both default to `None`; validation only fires inside `bootstrap_admin`.
   - `.env.example` grows the two keys with doc strings.
4. **Dev fixture** `src/budget_planner/db/dev_fixtures.py`:
   - When `settings.env == "dev"`, seed admin `admin@local.test` / `admin` with `must_change_password = 0` so local Playwright journeys do not have to rotate on every run (toggle a `dev_force_password_rotation` setting for the T-D18 integration test).
5. **Operator doc** `docs/plans/v3/runbooks/user-admin.md` (seeded here, extended by T-D46):
   - "Admin bootstrap" section documents the env-var contract and the "lost admin" recovery path: `terraform taint random_password.admin_initial_password && terraform apply` + redeploy, then log in with the new one-time password.

## Acceptance criteria

- `pytest tests/unit/services/test_users.py::test_bootstrap_admin_*` covers: fresh DB with env set → admin created + flagged + system categories seeded; existing non-admin with the same email → promoted; existing admin → no-op; missing env + no admin → raises `BootstrapAdminMissingEnv`; existing admin + missing env → no-op (no exception).
- `pytest tests/integration/startup/test_lifespan.py` covers: lifespan calls bootstrap exactly once; raises `SystemExit(1)` when `BootstrapAdminMissingEnv` is raised and no admin exists.
- No log line in `tests/integration` contains the plaintext password or the bcrypt hash (`grep` assertion against captured logs).
- A `just dev` run with no env vars but an existing admin starts cleanly.

## Validation hook

```sh
just test tests/unit/services/test_users.py -k bootstrap_admin
just test tests/integration/startup/test_lifespan.py
# full flow:
BUDGET_PLANNER_ADMIN_EMAIL=admin@example.com \
BUDGET_PLANNER_ADMIN_INITIAL_PASSWORD="$(openssl rand -base64 20)" \
just dev
# admin logs in with the generated password → forced to /settings/password → rotates.
```
