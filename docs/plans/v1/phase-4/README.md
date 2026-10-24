# Phase 4 — Testing Plans

> Phase 4 locks the testing pyramid and the 90% coverage gate before polish (Phase 5). All four tasks are planned-only here; no code written yet.

## Scope

| Task | Title | Status |
|------|-------|--------|
| [T-040](T-040-unit-tests.md) | Unit tests for services + repositories | pending |
| [T-041](T-041-integration-tests.md) | Integration tests for cross-layer flows | pending |
| [T-042](T-042-e2e-smoke-tests.md) | E2E smoke tests for four critical flows | pending |
| [T-043](T-043-coverage-gate.md) | Coverage gate at 90% in `just test` + CI | pending |

## Testing Pyramid

```
                     ┌─────────┐
                     │  E2E 4  │   ~4 flows, httpx + Jinja; Playwright optional
                     └─────────┘
                  ┌───────────────┐
                  │ Integration ~18 │  cross-layer flows against temp SQLite
                  └───────────────┘
            ┌─────────────────────────┐
            │       Unit ~140+        │  pure fns per service + repo module
            └─────────────────────────┘
```

Target proportions (count-wise, roughly): **unit ≥ 80%**, **integration ~15%**, **e2e ~5%**. Coverage attribution lives mostly in unit; integration raises confidence on real DB + audit; e2e catches wiring/router bugs.

### Per-layer targets

| Layer | Dir | Count target | Coverage contribution |
|-------|-----|--------------|-----------------------|
| Unit | `tests/unit/` | 140+ tests across ~18 modules | drives most of the 90% gate |
| Integration | `tests/integration/` | ~18 tests across 6 flow files | audit assertions, repo+service wiring |
| E2E | `tests/e2e/` | 4 smoke flows | router + template wiring only |

Hard gate: `pytest --cov=src/budget_planner --cov-fail-under=90`. See [T-043](T-043-coverage-gate.md).

## Fixtures

Shared fixtures live in:

- `tests/conftest.py` — `tmp_db_path` (xdist-safe), `conn` (per-test SQLite connection with foreign keys on), `migrated_conn` (schema + seed), `frozen_time`, `fx_http_mock`, `app_client` (FastAPI `TestClient`), `playwright_page` (optional).
- `tests/fixtures/seed.py` — a `seeded_conn` fixture + composable builders (`make_account`, `make_category`, `make_transaction`, `make_rule`, `make_fx_rate`). Deterministic ids, UTC-aware timestamps, PLN as base currency.

Extending fixtures:

1. Add a new builder to `tests/fixtures/seed.py`.
2. Keep builders pure: they take `conn` + kwargs, return the inserted DTO, and never read module-level mutable state.
3. New shared fixture → declare in `tests/conftest.py`, scope `function` by default. `session`-scoped only when the fixture is pure read-only data (e.g. a canned FX JSON blob loaded from a file).
4. Document the fixture by name at the top of the new test file.

## Risks (recap)

- SQLite file contention under `pytest-xdist` — every test uses a `tmp_path`-scoped DB file; no shared paths.
- HTMX fragment assertions must be **structural** (BeautifulSoup selectors), never full-string snapshots.
- Playwright flakiness — if adopted, run headless with 2 retries in CI; headed only locally.
- Template coverage — target is `src/budget_planner` only; Jinja is not instrumented.

## Conventions

- Arrange-Act-Assert layout per test.
- Test names describe behaviour (`promote_marks_planned_as_promoted_and_writes_audit_row`).
- Audit assertions in every integration mutation test (ADR-0019 is not optional).
- No business logic in test helpers — if a helper grows a branch, extract into `src/`.
