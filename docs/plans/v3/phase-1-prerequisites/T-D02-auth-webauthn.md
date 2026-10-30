# T-D02 — Per-user password + passkey auth

- **Phase**: 1 — App Prerequisites
- **Parallel-safe**: no — depends on T-D16a (multi-user migration adds `users.password_hash`)
- **Depends on**: T-D16a
- **Blocks**: T-D07, T-D08, T-D09, T-D14 (all need `request.state.user`); T-D17, T-D18, T-D19; Phase 4 smoke (T-D43)
- **References**: ADR-0033 (as amended by ADR-0061)

## Context

Internet exposure (ADR-0032) requires auth. ADR-0033 originally scoped auth as single-user passkey with a global fallback password; ADR-0061 amends it to **per-user** auth with no global fallback — each user has their own `password_hash` on `users` and can register their own passkeys after logging in. The admin is bootstrapped by Terraform (T-D19) with a one-time password that must be rotated on first login.

## Deliverables

1. Migration `migrations/0013_v2_auth.sql`:
   - `webauthn_credentials(id, user_id, credential_id BLOB UNIQUE, public_key BLOB, sign_count INTEGER, transports TEXT, label TEXT, created_at, updated_at, deleted_at, last_used_at)`.
   - `sessions(id, user_id, issued_at, expires_at, last_seen_at, user_agent, ip, revoked_at)`.
   - `auth_rate_limit(id, ip, route, hit_count, window_started_at)`.
   - The password hash lives on `users.password_hash` added by T-D16a's migration `0012`; no separate `auth_password` table.
2. Repository layer:
   - `src/budget_planner/repositories/webauthn.py` — add/list/revoke credentials, soft-delete + audit, scoped by `user_id`.
   - `src/budget_planner/repositories/sessions.py` — create/get/revoke/list sessions, scoped by `user_id`.
   - `src/budget_planner/repositories/users.py` extends with `verify_password(conn, email, plaintext) -> User | None`, `set_password_hash(conn, user_id, hash)`.
3. Service layer:
   - `src/budget_planner/services/auth.py` — password login, passkey ceremony orchestration (begin/complete for register and login), session issuance, bcrypt verify, replay-protection via `sign_count`.
4. Routers:
   - `src/budget_planner/web/routers/auth.py`:
     - `GET /auth/login` form (email + password).
     - `POST /auth/login` — password login OR triggers passkey ceremony if `passkey=1`.
     - `POST /auth/login/finish` — WebAuthn ceremony completion.
     - `GET /auth/register` + `POST /auth/register/finish` — register a passkey for the currently-logged-in user.
     - `POST /auth/logout`.
     - `GET /auth/sessions` HTML view listing active sessions; `POST /auth/sessions/<id>/revoke`.
   - The old `/auth/fallback-login` route is **removed** per ADR-0061.
5. Middleware (new module `src/budget_planner/web/middleware/auth.py`):
   - `SessionMiddleware` parses `__Host-session`, hydrates `request.state.user` as a `User` DTO (with `id`, `email`, `is_admin`, `must_change_password`).
   - `AuthRequiredMiddleware` with the exempt-route list from ADR-0033 §5.
   - `MustChangePasswordMiddleware` — if `request.state.user.must_change_password == 1`, redirect any non-`/auth/*` + non-`/settings/password` + non-`/health|/ready` request to `/settings/password`.
6. HTMX extension `src/budget_planner/web/static/js/htmx-webauthn.js` (small; wraps the browser WebAuthn calls).
7. Templates:
   - `templates/auth/login.html`, `templates/auth/sessions.html`, `templates/auth/register-passkey.html`.
8. Dev fixture: seed a known admin + bcrypt password hash in `src/budget_planner/db/dev_fixtures.py` under `if settings.env == "dev"` so local tests do not need Terraform. Admin: `admin@local.test` / `admin`.

## Acceptance criteria

- `pytest tests/unit/services/test_auth.py` covers: happy path password login + passkey register + passkey login; bad password (rate-limited after 3 attempts); replay attack (sign_count regressed) → credential auto-revoked; login for a soft-deleted user → generic error.
- `pytest tests/integration/web/test_auth.py` covers: full ceremony via `TestClient` using the `py_webauthn` test authenticator; CSRF token issued on login; `__Host-session` cookie has `HttpOnly; Secure; SameSite=Strict`; `MustChangePasswordMiddleware` redirects when flag is set and allows `/settings/password` + `/auth/*` + `/health` through.
- Local prod-stack test: admin bootstrap (via dev fixture) → login → forced password change → register a passkey end-to-end via Playwright + virtual authenticator. Journey in `tests/e2e/test_passkey_journey.py` (opt-in, not in default CI).
- Audit log row written for every login success/failure, logout, session revocation, passkey registration, passkey removal — with `user_id` populated.
- `/auth/*` responses never leak whether a user exists (always generic error for login failure).

## Validation hook

```sh
just test tests/unit/services/test_auth.py tests/integration/web/test_auth.py
# then local full stack:
just test-prod-stack
# browse https://localhost, admin login → forced password change → register passkey → logout → login via passkey.
```
