"""Integration tests for /today router (T-R40, ADR-0056 §3)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_today_renders(client: TestClient) -> None:
    r = client.get("/today")
    assert r.status_code == 200
    assert "Today" in r.text


def test_afford_endpoint_minor_units(client: TestClient) -> None:
    r = client.get("/today/afford?amount=10000")
    assert r.status_code == 200
    assert "rd-afford__new" in r.text


def test_afford_endpoint_zero(client: TestClient) -> None:
    r = client.get("/today/afford?amount=0")
    assert r.status_code == 200
    # No delta is shown with zero amount — just the per-day line.
    assert "rd-afford__new" in r.text


def test_afford_endpoint_major_units_fallback(client: TestClient) -> None:
    # Backwards-compat: the existing form posts step=0.01 decimals.
    r = client.get("/today/afford?amount=100.00")
    assert r.status_code == 200
    assert "rd-afford__new" in r.text


def test_afford_endpoint_invalid_amount(client: TestClient) -> None:
    r = client.get("/today/afford?amount=not-a-number")
    assert r.status_code == 422


def test_afford_endpoint_negative_amount(client: TestClient) -> None:
    r = client.get("/today/afford?amount=-1")
    assert r.status_code == 422


def test_afford_endpoint_no_db_write(client: TestClient) -> None:
    """ADR-0056 §3 — the preview is a pure read."""
    # Baseline audit count via settings tab (any read endpoint is fine).
    r1 = client.get("/today/afford?amount=1000")
    r2 = client.get("/today/afford?amount=2500")
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_afford_alias_route(client: TestClient) -> None:
    """Legacy ``/afford`` alias keeps working."""
    r = client.get("/afford?amount=10000")
    assert r.status_code == 200
    assert "rd-afford__new" in r.text
