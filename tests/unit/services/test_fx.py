"""Tests for the FX service (T-020)."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest

from budget_planner.domain.fx import NewFxRate
from budget_planner.repositories import fx as fx_repo
from budget_planner.services import fx as fx_service
from budget_planner.services.fx import FxUnavailableError

_API = "https://api.frankfurter.app"


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url=_API)


def _ok_rate(to_ccy: str, rate: Decimal | str) -> Callable[[httpx.Request], httpx.Response]:
    def _h(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rates": {to_ccy: str(rate)}})

    return _h


def test_identity_short_circuits(conn: sqlite3.Connection) -> None:
    calls: list[httpx.Request] = []

    def _h(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(500)

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "PLN", "PLN")
    assert rate == Decimal("1")
    assert calls == []


def test_cache_hit_skips_http(conn: sqlite3.Connection) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 15), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.3100")),
    )
    calls: list[httpx.Request] = []

    def _h(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(500)

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert rate == Decimal("4.3100")
    assert calls == []


def test_cache_miss_fetches_and_persists(conn: sqlite3.Connection) -> None:
    captured: list[str] = []

    def _h(req: httpx.Request) -> httpx.Response:
        captured.append(str(req.url))
        return httpx.Response(200, json={"rates": {"PLN": "4.3200"}})

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")

    assert rate == Decimal("4.3200")
    assert captured  # http hit
    # Second call must come from cache, no http.
    calls_before = len(captured)
    with _mock_client(_h) as http2:
        rate2 = fx_service.get_rate(conn, http2, date(2026, 1, 15), "EUR", "PLN")
    assert rate2 == Decimal("4.3200")
    assert len(captured) == calls_before  # same handler, not called again by second client


def test_url_uses_iso_date_and_params(conn: sqlite3.Connection) -> None:
    seen: dict[str, Any] = {}

    def _h(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rates": {"PLN": "4.0"}})

    with _mock_client(_h) as http:
        fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert seen["path"].endswith("/2026-01-15")
    assert seen["params"] == {"from": "EUR", "to": "PLN"}


def test_api_error_falls_back_to_latest(
    conn: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 10), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.2000")),
    )

    def _h(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with (
        _mock_client(_h) as http,
        caplog.at_level(logging.WARNING, logger="budget_planner.services.fx"),
    ):
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert rate == Decimal("4.2000")
    assert any("fallback" in r.message for r in caplog.records)
    # Stale rate must NOT be persisted under the requested date.
    assert fx_repo.find_rate(conn, date(2026, 1, 15), "EUR", "PLN") is None


def test_api_error_with_empty_cache_raises(conn: sqlite3.Connection) -> None:
    def _h(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with _mock_client(_h) as http, pytest.raises(FxUnavailableError):
        fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")


def test_http_500_triggers_fallback(conn: sqlite3.Connection) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 10), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.2000")),
    )

    def _h(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert rate == Decimal("4.2000")
    assert fx_repo.find_rate(conn, date(2026, 1, 15), "EUR", "PLN") is None


def test_missing_key_in_response_triggers_fallback(conn: sqlite3.Connection) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 10), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.2000")),
    )

    def _h(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rates": {}})

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert rate == Decimal("4.2000")


def test_convert_identity(conn: sqlite3.Connection) -> None:
    with _mock_client(_ok_rate("EUR", "1")) as http:
        out = fx_service.convert(conn, http, 123, date(2026, 1, 15), "EUR", "EUR")
    assert out == 123


def test_convert_rounds_half_even(conn: sqlite3.Connection) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 15), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.31")),
    )
    with _mock_client(_ok_rate("PLN", "4.31")) as http:
        out = fx_service.convert(conn, http, 10050, date(2026, 1, 15), "EUR", "PLN")
    # 10050 * 4.31 = 43315.5 → ROUND_HALF_EVEN → 43316
    assert out == 43316


def test_convert_preserves_sign(conn: sqlite3.Connection) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 15), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.3100")),
    )
    with _mock_client(_ok_rate("PLN", "4.31")) as http:
        out = fx_service.convert(conn, http, -10000, date(2026, 1, 15), "EUR", "PLN")
    assert out == -43100


def test_convert_zero_decimals_currency(conn: sqlite3.Connection) -> None:
    # EUR→JPY: destination has 0 minor decimals. 100 EUR minor = €1.00; at
    # rate 150 the user receives ¥150, i.e. 150 JPY minor units (JPY has 0
    # decimals so minor == major).
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 15), from_ccy="EUR", to_ccy="JPY", rate=Decimal("150")),
    )
    with _mock_client(_ok_rate("JPY", "150")) as http:
        out = fx_service.convert(conn, http, 100, date(2026, 1, 15), "EUR", "JPY")
    assert out == 150


def test_non_object_payload_triggers_fallback(conn: sqlite3.Connection) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 10), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.1")),
    )

    def _h(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json="plain string")

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert rate == Decimal("4.1")


def test_rates_not_dict_triggers_fallback(conn: sqlite3.Connection) -> None:
    fx_repo.upsert_rate(
        conn,
        NewFxRate(date=date(2026, 1, 10), from_ccy="EUR", to_ccy="PLN", rate=Decimal("4.1")),
    )

    def _h(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rates": "not a dict"})

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert rate == Decimal("4.1")


def test_remote_response_decimal_precision(conn: sqlite3.Connection) -> None:
    # Guard: parse via str(), not float — long decimals round-trip.
    def _h(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rates": {"PLN": "4.123456789"}})

    with _mock_client(_h) as http:
        rate = fx_service.get_rate(conn, http, date(2026, 1, 15), "EUR", "PLN")
    assert rate == Decimal("4.123456789")
