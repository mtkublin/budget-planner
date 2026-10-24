"""T-037 forecast router."""

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


def test_horizon_param(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_days=7")
    assert r.status_code == 200
    assert "Horizon 7" in r.text


def test_horizon_bad_input_falls_back(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_days=notanumber")
    assert r.status_code == 200


def test_horizon_clamped(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_days=99999")
    assert r.status_code == 200
    # clamp applies to 365
    assert "Horizon 365" in r.text


def test_horizon_min(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast?horizon_days=0")
    assert r.status_code == 200
    assert "Horizon 1" in r.text


def test_chart_fragment(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast/chart?horizon_days=5")
    assert r.status_code == 200
    assert "<html" not in r.text
    assert "forecast-chart" in r.text


def test_plotly_json_shape(client: TestClient, seeded: int) -> None:
    r = client.get("/forecast/chart")
    # Extract the data-plotly attribute payload
    start = r.text.find('data-plotly="') + len('data-plotly="')
    end = r.text.find('"', start)
    payload = html.unescape(r.text[start:end])
    spec = json.loads(payload)
    assert "data" in spec and isinstance(spec["data"], list)
    assert spec["data"][0]["type"] == "scatter"
