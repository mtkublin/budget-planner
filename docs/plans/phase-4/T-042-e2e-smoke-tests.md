# T-042 — E2E smoke tests

> Phase 4 — Testing. Status: pending.

## Purpose

Verify the four critical user flows end-to-end through the FastAPI app and rendered Jinja/HTMX fragments. These tests prove the full stack is wired — routers, services, repositories, SQLite, templates, HTMX swaps — not that any individual component is correct (that's T-040/T-041). Smoke only; four flows total.

## Inputs / prerequisites

- Upstream code:
  - FastAPI app: [`src/budget_planner/web/app.py`](../../../src/budget_planner/web/app.py) (T-030).
  - Routers under [`src/budget_planner/web/routers/`](../../../src/budget_planner/web/routers/) (T-031..T-038).
  - Templates under [`src/budget_planner/web/templates/`](../../../src/budget_planner/web/templates/) with HTMX partials (T-039).
- ADRs: [ADR-0002](../../adr/0002-web-stack-fastapi-htmx-jinja.md), [ADR-0011](../../adr/0011-derived-balance-snapshots-reconciliation.md), [ADR-0012](../../adr/0012-planned-manual-promotion.md), [ADR-0013](../../adr/0013-recurring-virtual-occurrences-and-overrides.md), [ADR-0014](../../adr/0014-budget-flat-no-rollover-three-tier.md), [ADR-0018](../../adr/0018-ci-single-matrix-row.md), [ADR-0019](../../adr/0019-soft-delete-and-audit-log.md).
- Testing stack already provisioned in T-001: `pytest`, `pytest-asyncio`, `httpx` (ships with FastAPI's `TestClient`), **`beautifulsoup4`** (add to dev deps during T-042; required for structural fragment assertions), **Playwright** (optional, dev-only).

## Deliverables

Test files under `tests/e2e/`:

```
tests/e2e/
├── conftest.py                       # app_client fixture, migrated-and-seeded test DB
├── test_add_transaction_flow.py
├── test_set_budget_flow.py
├── test_recurring_promote_flow.py
└── test_reconcile_flow.py
```

Shared fixtures:

- `tests/e2e/conftest.py` — `app_client` (FastAPI `TestClient` pointed at a per-test migrated+seeded SQLite file via dependency override), `fx_http_mock` (yields `respx` router), `playwright_page` **only if** the Playwright track is adopted.
- Reuses `tests/fixtures/seed.py` builders from T-040 to pre-arrange database state before the `TestClient` request.

Config diffs:

- Marker already registered in T-040: `e2e`.
- Add `[tool.pytest.ini_options]` filter: `filterwarnings = ["error::DeprecationWarning:budget_planner.*"]` (optional, keeps the suite honest).
- **If Playwright is adopted (decision below):** `playwright.config.py` or inline fixture; CI step `uv run playwright install --with-deps chromium`.

### Playwright vs `TestClient` decision

Default **`TestClient` + BeautifulSoup** for all four flows. Playwright is optional and only added if a flow genuinely needs JS execution (HTMX itself is handled by response-header + swap assertions; it does not require a browser to verify). Rationale: fastest, deterministic, xdist-safe, no browser deps in CI. If a future flow needs browser JS (e.g. Plotly interaction), add Playwright behind the `@pytest.mark.e2e_browser` sub-marker, headless with 2 retries in CI, headed locally.

## Scope & test matrix

Four flows, one file each. All four assertions follow the pattern: seed state → POST the mutation → GET the view → parse with BeautifulSoup → assert structural selectors.

| Flow | Test file | Request sequence | Structural assertions |
|------|-----------|------------------|-----------------------|
| Add transaction → balance updates | `test_add_transaction_flow.py` | 1. Seed 1 account `Checking` (PLN, opening=100_00). 2. `POST /transactions` with amount=20_00, category=Groceries (expense). 3. `GET /accounts`. | HTMX swap target `#transactions-table` present on POST response; `GET /accounts` row for `Checking` shows balance `80.00 zł` (selector `tr[data-account-name="Checking"] td[data-field="balance"]`); audit row written. |
| Set budget → see remaining | `test_set_budget_flow.py` | 1. Seed category `Groceries`, default budget=500_00. 2. Add a transaction amount=120_00 against Groceries. 3. `GET /budget`. | Row `tr[data-category="Groceries"]` has `data-budgeted="500.00"`, `data-spent="120.00"`, `data-remaining="380.00"`. |
| Recurring rule → see virtual occurrences → promote one | `test_recurring_promote_flow.py` | 1. `POST /recurring` with monthly rule start=2026-01-15, amount=50_00. 2. `GET /planned?from=2026-01-01&to=2026-03-31` → 3 virtual rows. 3. `POST /planned/{virtual_id}/promote` with edited amount=55_00. 4. `GET /transactions` → the promoted row present. | Virtual rows appear with `data-virtual="true"`; after promote, `GET /transactions` has 1 row with amount `55.00`; original planned row shows `data-promoted="true"`; audit rows on both `transactions.create` and `planned_transactions.update`. |
| Reconcile → adjustment txn created | `test_reconcile_flow.py` | 1. Seed account opening=100_00; add transactions summing -40_00 → derived=60_00. 2. `POST /accounts/{id}/reconcile` with actual=70_00. 3. `GET /transactions`. | A new transaction with category=`Reconciliation`, amount `10.00` present; `GET /accounts` shows balance `70.00 zł`; audit row for the adjustment transaction. |

HTMX-specific assertions (shared across all flows):

- Response `Content-Type` is `text/html; charset=utf-8` for fragment endpoints.
- Response contains the expected HTMX swap wrapper (e.g. `<tbody id="transactions-tbody">`).
- Where applicable, response header `HX-Trigger` contains `forecast-stale` (per T-037) — assert via `response.headers.get("hx-trigger")`.

## Fixtures / seed data

- `app_client` fixture:
  1. Creates a `tmp_db_path` SQLite file.
  2. Runs migrations + system seed.
  3. Overrides the FastAPI DB dependency (`Depends(get_conn)`) to point at this file.
  4. Yields a `TestClient(app)`.
  5. Closes connections, discards file.
- All HTTP calls to `frankfurter.app` are intercepted with `respx`; the fixture asserts no unexpected URLs are called.
- Builders from `tests/fixtures/seed.py` are used **before** the `TestClient` request to arrange state; **after**, the test uses only HTTP requests. This mirrors real browser usage.
- Playwright (if adopted): `playwright_page` fixture starts `uvicorn` on an ephemeral port against the same temp DB, yields a page object, tears down.

## Validation / acceptance

Command:

```sh
pytest tests/e2e -m e2e -q
```

Full gate (coverage from e2e supplements, does not substitute, unit/integration):

```sh
pytest --cov=src/budget_planner --cov-branch --cov-fail-under=90 tests/unit tests/integration tests/e2e
```

- All four flows green.
- Each flow asserts the required audit rows exist (ADR-0019).
- Each flow asserts at least one HTMX structural selector (BeautifulSoup `soup.select_one(...)` returns non-None).
- No full-page string snapshots. If a snapshot sneaks in, the test fails review.

## Risks & gotchas

- **BeautifulSoup selectors, not full-string snapshots.** Templates change often during polish; structural selectors on `data-*` attributes survive polish, HTML strings don't.
- **Playwright flakiness** — if used: headless in CI with `retries=2`; headed only locally. Never block CI on browser install if the smoke suite can run without it.
- **SQLite under xdist** — the `app_client` fixture must use `tmp_path` for every test. Dependency overrides must be reset in a `finally:` to avoid cross-test leakage.
- **No real HTTP** — `respx` with `assert_all_called=False, assert_all_mocked=True` so an accidental network call explodes.
- **Template coverage is not instrumented** — coverage scope is `src/budget_planner`. Jinja files are omitted (see T-040 config).
- **HTMX swap verification is structural** — look for the correct wrapper id/class the client-side `hx-target` would swap into; don't try to simulate the swap.
- **CSRF/anti-forgery** — v1 has no auth; forms POST without tokens. Keep it that way; a future auth ADR will introduce tokens.

## Handoff notes

Phase 5 polish tasks assume:

- These four flows are the regression floor. Any polish that breaks a selector must update the test in the same PR.
- `data-*` attributes used by selectors (e.g. `data-account-name`, `data-virtual`, `data-promoted`) are a **contract** — Phase 5 keeps them even when visual styling changes.
- New flows added in Phase 5 (e.g. inline validation error rendering per T-051) ship with their own structural e2e, co-located under `tests/e2e/`.
