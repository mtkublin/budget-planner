"""FX fetch integration test with mocked HTTP (ADR-0006).

Cache miss → fetch → persist; cache hit → no HTTP; API error → stale
fallback; identity short-circuits.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest

from budget_planner.services import fx as fx_service

pytestmark = pytest.mark.integration


def test_fx_cache_miss_fetches_persists_and_returns(
    conn: sqlite3.Connection,
    frankfurter_mock_factory: Callable[[dict[str, object]], httpx.Client],
) -> None:
    client = frankfurter_mock_factory({"/2026-02-01": {"rates": {"PLN": "4.42"}}})

    rate = fx_service.get_rate(conn, client, date(2026, 2, 1), "EUR", "PLN")
    assert rate == Decimal("4.42")

    # Second call must hit cache — swap mock to a raising transport, cache should still serve it.
    def _boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected network call to {request.url}")

    cached_client = httpx.Client(
        transport=httpx.MockTransport(_boom),
        base_url="https://api.frankfurter.app",
    )
    cached_rate = fx_service.get_rate(conn, cached_client, date(2026, 2, 1), "EUR", "PLN")
    assert cached_rate == Decimal("4.42")


def test_fx_same_currency_returns_one_without_io(conn: sqlite3.Connection) -> None:
    def _boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("identity path must not touch HTTP")

    client = httpx.Client(transport=httpx.MockTransport(_boom))
    assert fx_service.get_rate(conn, client, date(2026, 2, 1), "PLN", "PLN") == Decimal("1")


def test_fx_api_error_falls_back_to_last_known_rate(
    conn: sqlite3.Connection,
    make_fx_rate: Callable[..., None],
    frankfurter_error_client: httpx.Client,
) -> None:
    make_fx_rate(on_date=date(2026, 1, 15), from_ccy="EUR", to_ccy="PLN", rate="4.28")

    rate = fx_service.get_rate(conn, frankfurter_error_client, date(2026, 2, 1), "EUR", "PLN")
    assert rate == Decimal("4.28")

    # Stale fallback must NOT persist a new row under on_date=2026-02-01.
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM fx_rates WHERE date=? AND from_ccy=? AND to_ccy=?",
        ("2026-02-01", "EUR", "PLN"),
    ).fetchone()
    assert row["n"] == 0


def test_fx_api_error_without_cache_raises(
    conn: sqlite3.Connection,
    frankfurter_error_client: httpx.Client,
) -> None:
    with pytest.raises(fx_service.FxUnavailableError):
        fx_service.get_rate(conn, frankfurter_error_client, date(2026, 2, 1), "EUR", "PLN")


def test_convert_uses_historical_rate(
    conn: sqlite3.Connection,
    frankfurter_mock_factory: Callable[[dict[str, object]], httpx.Client],
) -> None:
    client = frankfurter_mock_factory({"/2026-02-01": {"rates": {"PLN": "4.40"}}})
    # 100.00 EUR @ 4.40 → 440.00 PLN.
    converted = fx_service.convert(
        conn,
        client,
        amount_minor=10000,
        on_date=date(2026, 2, 1),
        from_ccy="EUR",
        to_ccy="PLN",
    )
    assert converted == 44000
