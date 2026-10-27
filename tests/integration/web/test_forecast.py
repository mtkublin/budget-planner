"""T-037 + T-127 forecast router."""

from __future__ import annotations

import html
import json

import pytest
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.accounts import NewAccount
from budget_planner.repositories import accounts as accounts_repo


@pytest.fixture
def seeded(_migrated: Settings) -> int:
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(
            conn, NewAccount(name="Main", currency="PLN", opening_balance=100000)
        )
        return acc.id
    finally:
        conn.close()


def test_index(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast")
    assert r.status_code == 200
    assert 'id="forecast-chart"' in r.text
    assert "data-plotly" in r.text
    assert 'id="forecast-monthly-table"' in r.text


def test_horizon_param(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_months=6")
    assert r.status_code == 200
    assert "Horizon 6 months" in r.text


def test_horizon_bad_input_falls_back(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_months=notanumber")
    assert r.status_code == 200
    assert "Horizon 12 months" in r.text


def test_horizon_clamped(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_months=99999")
    assert r.status_code == 200
    assert "Horizon 60 months" in r.text


def test_horizon_min(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_months=0")
    assert r.status_code == 200
    assert "Horizon 1 month" in r.text


def test_view_fragment(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast/view?horizon_months=3")
    assert r.status_code == 200
    assert "<html" not in r.text
    assert 'id="forecast-view"' in r.text
    assert 'id="forecast-chart"' in r.text
    assert 'id="forecast-monthly-table"' in r.text


def test_monthly_table_row_count(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast/view?horizon_months=5")
    assert r.status_code == 200
    assert r.text.count('data-month="') == 5


def test_plotly_json_shape(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast/view?horizon_months=1")
    start = r.text.find('data-plotly="') + len('data-plotly="')
    end = r.text.find('"', start)
    payload = html.unescape(r.text[start:end])
    spec = json.loads(payload)
    assert "data" in spec and isinstance(spec["data"], list)
    assert spec["data"][0]["type"] == "scatter"


def test_forecast_nav_link_present(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast")
    assert r.status_code == 200
    assert 'href="/forecast"' in r.text
    assert ">Forecast<" in r.text
