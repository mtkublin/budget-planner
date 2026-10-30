# T-D18 — Password change (`/settings/password`)

- **Phase**: 1 — App Prerequisites
- **Parallel-safe**: yes
- **Depends on**: T-D02
- **Blocks**: T-D43 (prod smoke)
- **References**: [ADR-0061](../../../adr/0061-v3-multi-user-admin-bootstrap-and-data-isolation.md) §4

## Context

Every user — admin and non-admin alike — rotates their own password here. First-login flow forces rotation when `must_change_password = 1` via `MustChangePasswordMiddleware` (T-D02). This route is the only exit from that forced redirect.

## Deliverables

1. **Service** `src/budget_planner/services/users.py::change_own_password(conn, user_id, current_plaintext, new_plaintext)`:
   - Verify current password via bcrypt against `users.password_hash`.
   - Hash new password; update `users.password_hash` and clear `must_change_password`.
   - In the same transaction, revoke all **other** sessions of the same user (keep the current session live so the user is not kicked out mid-flow).
   - Write audit row (`entity_type='users'`, `entity_id=user_id`, `operation='update'`, `prev_json` + `new_json` redact the hash and only record "password rotated").
   - On verify failure, write an audit row with `operation='update_failed'` + IP/user-agent (via T-D14 context); increment the rate-limit counter via `auth_rate_limit`.
2. **Router** `src/budget_planner/web/routers/settings_password.py`:
   - `GET /settings/password` — form (current, new, confirm). Available to any logged-in user.
   - `POST /settings/password` — validate (new == confirm, min length 12, server-side only — no "strength" theatre), call service, redirect to origin page (or `/` for admin after bootstrap flow).
   - Rate limited by `slowapi` same way as `/auth/login` (ADR-0033 §2) to blunt credential-stuffing against a logged-in session.
3. **Template** `templates/settings/password.html` — three inputs, submit button, inline error area. Reuses the shared form-primitives from ADR-0030.
4. **Middleware integration**: `MustChangePasswordMiddleware` from T-D02 exempts `/settings/password` + `/auth/*` + `/health` + `/ready` so the user can actually reach the rotation form. All other routes 302 to `/settings/password?next=<original>` while the flag is set.
5. **Settings sidebar**: a "Password" tab visible to every logged-in user. Admin sees both "Users" and "Password".

## Acceptance criteria

- `pytest tests/unit/services/test_users.py::test_change_own_password_*` covers: happy path (hash updated, flag cleared, other sessions revoked, current session preserved); wrong current (verify fails, rate-limit counter increments, no mutation); new == old (allowed; policy decision — enforcing "different from previous" needs a password-history table and is deferred); new != confirm → 422.
- `pytest tests/integration/web/test_settings_password.py` covers: `MustChangePasswordMiddleware` redirects any other authenticated route to `/settings/password` when the flag is set; after a successful change, the flag is cleared and the next request is served normally.
- Audit log carries one row for each attempt — success and failure.
- Rate limit kicks in after 3 failed attempts in 15 min (shared counter with `/auth/login`).

## Validation hook

```sh
just test tests/unit/services/test_users.py -k change_own_password
just test tests/integration/web/test_settings_password.py
just test-prod-stack
# admin logs in → forced to /settings/password → rotates → navigates freely.
```
