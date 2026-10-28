# T-D01 — Health & readiness endpoints

- **Phase**: 1 — App Prerequisites
- **Parallel-safe**: yes
- **Depends on**: nothing
- **Blocks**: Phase 2 cloud-init health probe (T-D23), Phase 3 deploy post-probe (T-D31), Phase 4 uptime monitor (T-D44)
- **References**: ADR-0032 §8, ADR-0036 §7

## Context

Caddy, the deploy pipeline, and the external uptime monitor need a cheap liveness signal (`/health`) and a slightly richer readiness signal (`/ready`) that also exercises the DB. Both must be reachable without auth (ADR-0033 §5 lists them as exempt routes).

## Deliverables

1. New router module: `src/budget_planner/web/routers/health.py`.
2. Two routes:
   - `GET /health` → `200 {"status": "ok"}`. Does not touch the DB. No logging on success (keeps `uvicorn` access log quiet when the uptime monitor pings every 5 min — see T-D06).
   - `GET /ready` → `200 {"status": "ready", "db": "ok"}` when `PRAGMA integrity_check` on `/data/budget.db` returns `ok`; `503 {"status": "not-ready", "db": "<reason>"}` otherwise with a 2 s budget on the DB check.
3. Both routes registered before `AuthRequiredMiddleware` so unauthenticated requests pass through.
4. Caddy forwards them without rate limiting (ADR-0036 §7).

## Acceptance criteria

- Unit test: `tests/unit/web/test_health.py` asserts status + body shape for both endpoints.
- Integration test: `tests/integration/web/test_health.py::test_ready_returns_503_when_db_corrupt` corrupts a temp DB and asserts the 503 shape.
- `GET /health` returns within 10 ms on a cold request against a freshly started app (measured with `httpx` + perf_counter).
- `GET /ready` does not write anything to the audit log.
- No logging on `/health` 200s (verified by capturing the structured log stream during a request).

## Validation hook

```sh
just test-prod-stack
curl -fsS https://localhost/health -k | jq .
curl -fsS https://localhost/ready  -k | jq .
```

Both return 200. Readiness JSON includes `"db": "ok"`.
