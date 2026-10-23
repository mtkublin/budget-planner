# T-020 — FX Service

> Phase 2 — Services. Status: pending.

## Purpose

Resolve a historical FX rate between two ISO 4217 currencies for a given date, with local SQLite caching, remote fetch from `frankfurter.app` on cache miss, and a stale-fallback to the most recent known rate when the API is unreachable. All multi-currency aggregates (fortune, budget, forecast, analytics) go through this service. Rates are cached per `(date, from_ccy, to_ccy)` and never overwritten once persisted — ECB rates are immutable for a past date.

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-013 Repositories](../phase-1/T-013-repository-layer.md) — specifically `repositories/fx.py`.
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `FxRate`, `Currency` alias.
- ADRs:
  - [ADR-0006 Multi-currency model](../../adr/0006-multi-currency-model.md) — historical rates, fallback contract.
  - [ADR-0008 Transaction amount sign & direction](../../adr/0008-transaction-amount-sign-and-direction.md) — minor-unit integer invariant.
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md) — pass `conn` and `http` as function args.
- Repository functions consumed:
  - `repositories.fx.find_rate(conn, date, from_ccy, to_ccy) -> FxRate | None`
  - `repositories.fx.find_latest_rate(conn, from_ccy, to_ccy, on_or_before: date | None) -> FxRate | None`
  - `repositories.fx.insert_rate(conn, FxRate) -> FxRate`
- External:
  - `httpx.Client` passed in as an argument (never constructed inside the service).
  - `frankfurter.app` endpoint URL from `config.fx_api_url` (e.g. `https://api.frankfurter.app`).

## Deliverables

- Module path: `src/budget_planner/services/fx.py`
- Test module path: `tests/unit/services/test_fx.py`
- Public function signatures:

```python
from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from decimal import Decimal

import httpx

from budget_planner.domain.money import Currency

logger = logging.getLogger(__name__)


def get_rate(
    conn: sqlite3.Connection,
    http: httpx.Client,
    on_date: dt.date,
    from_ccy: Currency,
    to_ccy: Currency,
) -> Decimal: ...


def convert(
    conn: sqlite3.Connection,
    http: httpx.Client,
    amount_minor: int,
    on_date: dt.date,
    from_ccy: Currency,
    to_ccy: Currency,
) -> int: ...
```

Both functions are pure in the mathematical-reasoning sense (same inputs → same outputs given the DB + remote state) and free of hidden singletons.

## Algorithm / step-by-step

### `get_rate`

1. **Short-circuit identity.** `if from_ccy == to_ccy: return Decimal("1")`.
2. **Cache hit.** Call `repositories.fx.find_rate(conn, on_date, from_ccy, to_ccy)`; if non-null, return `row.rate`.
3. **Remote fetch.** `GET {fx_api_url}/{on_date:%Y-%m-%d}?from={from_ccy}&to={to_ccy}` via `http`. Timeout e.g. 5 s. On HTTP 200:
   - Parse `response.json()["rates"][to_ccy]` as `Decimal` (never `float`).
   - Persist via `repositories.fx.insert_rate(conn, FxRate(date=on_date, from_ccy=from_ccy, to_ccy=to_ccy, rate=rate))`.
   - Commit at the service boundary (or defer to the caller; the plan standardises on committing in the service to keep the fetch idempotent across worker crashes — document this in the module docstring).
   - Return the rate.
4. **Fallback.** On any `httpx.HTTPError`, non-200 status, missing-key JSON, or `ValueError` during parse:
   - `latest = repositories.fx.find_latest_rate(conn, from_ccy, to_ccy, on_or_before=on_date)`.
   - If `latest is None`: raise `FxUnavailableError` (defined in the module). This is the only failure mode visible to callers; routers map it to a user-facing error.
   - Else: `logger.warning("fx fallback: %s→%s on %s uses stale rate from %s", from_ccy, to_ccy, on_date, latest.date)` and return `latest.rate`. Do **not** persist a stale rate under the requested date (would pollute the cache).

### `convert`

1. `rate = get_rate(conn, http, on_date, from_ccy, to_ccy)` as `Decimal`.
2. Compute `converted = Decimal(amount_minor) * rate`.
3. Quantize using the destination currency's minor-unit scale (default 2 decimals; the real decimals table lives in `domain.money.minor_unit_scale(ccy)`). Round `ROUND_HALF_EVEN` to match standard accounting rounding.
4. Return `int(converted)` (minor units of `to_ccy`).

### Caching invariant

- The `(date, from_ccy, to_ccy)` row is write-once. If a race inserts twice, the SQLite `UNIQUE` constraint from the Phase 1 schema is caught and the service re-reads.

## Interfaces / contracts

```python
class FxUnavailableError(RuntimeError):
    """Raised when neither remote nor local cache can produce a rate."""


def get_rate(
    conn: sqlite3.Connection,
    http: httpx.Client,
    on_date: dt.date,
    from_ccy: Currency,
    to_ccy: Currency,
) -> Decimal:
    """
    Return the FX rate from `from_ccy` to `to_ccy` for `on_date`.

    Invariants:
      - get_rate(..., ccy, ccy) == Decimal("1").
      - Successful remote fetches are cached and never overwritten.
      - On remote failure, falls back to the most recent cached rate with a
        logged warning; raises FxUnavailableError only when the cache is empty
        for the requested pair.
    """
```

```python
def convert(
    conn: sqlite3.Connection,
    http: httpx.Client,
    amount_minor: int,
    on_date: dt.date,
    from_ccy: Currency,
    to_ccy: Currency,
) -> int:
    """
    Convert `amount_minor` from `from_ccy` to `to_ccy` using the historical
    rate for `on_date`. Returns minor units of `to_ccy`.

    Rounding: ROUND_HALF_EVEN, quantized to the minor-unit scale of `to_ccy`.
    """
```

## Test strategy

Framework: `pytest`. HTTP mocked via `pytest_httpx` (or `respx`); fixtures provide a temp SQLite file + schema (`conftest.py` in `tests/unit/services/`).

Cases to cover (≥ 90% coverage required):

1. **Identity**: `get_rate(same, same)` returns `Decimal("1")` without touching cache or http.
2. **Cache hit**: pre-insert `FxRate(2026-01-15, EUR, PLN, 4.3100)`. Assert `get_rate(..., 2026-01-15, EUR, PLN) == Decimal("4.3100")` and the mocked `httpx.Client` was never called.
3. **Cache miss → fetch → persist**: no row in cache; `httpx` mock returns `{"rates": {"PLN": 4.3200}}`. Assert returned rate matches, row is now present in cache, and a subsequent call does not hit `httpx` again.
4. **API error → fallback with stale rate**: seed a row for `2026-01-10`; request `2026-01-15`; `httpx` raises `httpx.ConnectError`. Assert returned rate equals the `2026-01-10` row and a `WARNING` was emitted on the `budget_planner.services.fx` logger (use `caplog`).
5. **API error → no cache → raise `FxUnavailableError`**: empty cache; `httpx` raises; assert error.
6. **API HTTP 500 → fallback**: `httpx` mock returns 500; verify the stale-fallback path triggers (not a cache insert).
7. **Convert rounding**: `convert(10050, EUR→PLN, rate=4.31)` → `43316` (10050 * 4.31 = 43315.5; `ROUND_HALF_EVEN` → 43316 because even-nearest after .5 → 43316; verify with Decimal arithmetic in the test, not with hard-coded numbers only).
8. **Convert identity**: `convert(123, EUR, EUR)` returns `123`.
9. **Convert negative amount**: adjustment rows can be signed; verify sign preserved through conversion.
10. **Date formatting**: assert the outbound URL uses `%Y-%m-%d` not `%d-%m-%Y` (regression guard).

Fixtures:

- `fx_conn`: temp SQLite with `fx_rates` schema from migration.
- `fx_seed(conn, rows)`: helper that bulk-inserts cached rows.
- `fake_http`: `httpx.Client` wired to a `pytest_httpx` mock.

Mocking boundaries:

- Mock only the `httpx.Client`. Never patch `repositories.fx` — exercise it live against the temp DB so the test guards the integration shape.
- Do not patch `logger`; use `caplog` for assertion.

## Risks & gotchas

- **`Decimal` vs `float`**: parsing JSON with `json.loads` returns `float`. Use `Decimal(str(response.json()["rates"][to_ccy]))` to avoid binary-float drift that would compound across years of forecast conversions.
- **Minor-unit scale per currency**: not every ISO 4217 currency is 2-decimal (JPY, KRW are 0; TND is 3). `domain.money.minor_unit_scale(ccy)` is the single authority; the FX service must not hard-code `100`.
- **Stale fallback pollution**: a tempting bug is to persist the stale rate under the requested date. Do not — this would answer future queries with the wrong rate silently. Only persist what the remote actually returned.
- **Weekend / holiday rates**: `frankfurter.app` returns the previous trading day's rate when the requested date is a weekend. That is still "the correct historical rate" for a weekend-dated transaction; we persist it under the requested date and accept the duplication across adjacent dates.
- **Rate direction**: `frankfurter` uses the `from` parameter as the base. Make sure the stored row's `from_ccy` matches the request, not the API's internal base. If a future caller requests the inverse, that is a separate cache row (we never divide to invert at read time — floating-point hazard).
- **Timezones**: `on_date` is a naive `datetime.date` (ADR-0007). Never `datetime` or tz-aware. Enforce via type.
- **Transit cross-currency**: not an FX problem in v1 — blocked at validation (ADR-0006). FX service should not grow a special case for transits.

## Handoff notes

Phase 3 consumers:

- **Forecast router (T-037)** calls `convert(...)` for every per-day balance aggregation into base currency (`config.base_currency`, default PLN). Historical txns use `operation_date`; the forecast forward window uses "latest known rate" — which is a `get_rate(conn, http, today, ...)` call that resolves via today's cached row or triggers one fetch per fresh base→quote pair.
- **Analytics router (T-038)**, **Budget router (T-036)**, and the home dashboard also call `convert`.
- **Reconciliation (T-026)** does not call this service directly — reconciliation always happens in the account's own currency.

Routers must pass a shared `httpx.Client` created in the FastAPI lifespan and torn down on shutdown. Services never construct an HTTP client.
