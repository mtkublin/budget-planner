# T-D02 — WebAuthn + fallback password auth

- **Phase**: 1 — App Prerequisites
- **Parallel-safe**: yes
- **Depends on**: nothing (new tables; migration order is 0006)
- **Blocks**: T-D07, T-D08, T-D09, T-D14 (all need `request.state.user`); Phase 4 smoke (T-D43)
- **References**: ADR-0033

## Context

Internet exposure (ADR-0032) requires auth. ADR-0033 picks WebAuthn (passkey) as primary with a long-random fallback password for break-glass. Session cookie binds the single user_id=1 scaffold to each request.

## Deliverables

1. Migration `migrations/0006_v2_auth.sql`:
   - `webauthn_credentials(id, user_id, credential_id BLOB UNIQUE, public_key BLOB, sign_count INTEGER, transports TEXT, label TEXT, created_at, updated_at, deleted_at, last_used_at)`.
   - `auth_password(id, user_id UNIQUE, bcrypt_hash TEXT, updated_at)`.
   - `sessions(id, user_id, issued_at, expires_at, last_seen_at, user_agent, ip, revoked_at)`.
   - `auth_rate_limit(id, ip, route, hit_count, window_started_at)`.
   - All tables carry `deleted_at` where appropriate per ADR-0019; `sessions` uses `revoked_at` instead.
2. Repository layer:
   - `src/budget_planner/repositories/webauthn.py` — add/list/revoke credentials, soft-delete + audit.
   - `src/budget_planner/repositories/sessions.py` — create/get/revoke/list sessions.
   - `src/budget_planner/repositories/auth_password.py` — set/verify.
3. Service layer:
   - `src/budget_planner/services/auth.py` — ceremony orchestration (begin/complete for register and login); session issuance; bcrypt verify; replay-protection via `sign_count`.
4. Routers:
   - `src/budget_planner/web/routers/auth.py` with the eight routes from ADR-0033 §1–§3.
   - `/auth/sessions` HTML view listing active sessions with device + last-seen; revoke button per row.
5. Middleware (new module `src/budget_planner/web/middleware/auth.py`):
   - `SessionMiddleware` parses `__Host-session`, hydrates `request.state.user`.
   - `AuthRequiredMiddleware` with the exempt-route list from ADR-0033 §5.
6. HTMX extension `src/budget_planner/web/static/js/htmx-webauthn.js` (small; wraps the browser WebAuthn calls).
7. Templates:
   - `templates/auth/login.html`, `register.html`, `fallback.html`, `sessions.html`.
8. Dev fixture: seed a known fallback-password hash in `src/budget_planner/db/dev_fixtures.py` under an `if settings.env == "dev"` gate so local tests do not need Terraform.

## Acceptance criteria

- `pytest tests/unit/services/test_auth.py` covers: happy path register + login; bad fallback password (rate-limited after 3 attempts); replay attack (sign_count regressed) → credential auto-revoked.
- `pytest tests/integration/web/test_auth.py` covers: full ceremony via `TestClient` using the `py_webauthn` test authenticator; CSRF token issued on login; `__Host-session` cookie has `HttpOnly; Secure; SameSite=Strict`.
- Local prod-stack test: register a passkey end-to-end via Playwright + virtual authenticator. Journey in `tests/e2e/test_passkey_journey.py` (opt-in, not in default CI).
- Audit log row written for every login success/failure, logout, session revocation, passkey registration, passkey removal.
- `/auth/*` responses never leak whether a user exists (always generic error for login failure).

## Validation hook

```sh
just test tests/unit/services/test_auth.py tests/integration/web/test_auth.py
# then local full stack:
just test-prod-stack
# browse https://localhost, follow fallback → register passkey → logout → login via passkey.
```
