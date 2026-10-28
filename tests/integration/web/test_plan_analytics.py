"""Integration tests for GET /plan/analytics (T-R43, ADR-0056 §6)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_plan_analytics_default_period(client: TestClient) -> None:
    r = client.get("/plan/analytics")
    assert r.status_code == 200
    assert 'data-period="month"' in r.text


def test_plan_analytics_year_period(client: TestClient) -> None:
    r = client.get("/plan/analytics?period=year")
    assert r.status_code == 200
    assert 'data-period="year"' in r.text


def test_plan_analytics_trailing_period(client: TestClient) -> None:
    r = client.get("/plan/analytics?period=trailing-12")
    assert r.status_code == 200
    assert 'data-period="trailing-12"' in r.text


def test_plan_analytics_invalid_period_falls_back_to_month(client: TestClient) -> None:
    r = client.get("/plan/analytics?period=nope")
    assert r.status_code == 200
    assert 'data-period="month"' in r.text


def test_plan_tab_analytics_renders(client: TestClient) -> None:
    """Legacy /plan?tab=analytics still works and now carries a real bundle."""
    r = client.get("/plan?tab=analytics")
    assert r.status_code == 200
