"""T-036 budget router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Direction
from budget_planner.repositories import categories as categories_repo


@pytest.fixture
def cat_id(_migrated: Settings) -> int:
    conn = get_connection(_migrated)
    try:
        cat = categories_repo.create(
            conn, NewCategory(name="Groceries", direction=Direction.EXPENSE)
        )
        return cat.id
    finally:
        conn.close()


def test_index(client: TestClient, cat_id: int) -> None:
    r = client.get("/budget")
    assert r.status_code == 200
    assert "Budget" in r.text


def test_index_with_year_month(client: TestClient, cat_id: int) -> None:
    r = client.get("/budget?year=2026&month=10")
    assert r.status_code == 200
    assert "2026-10" in r.text


def test_manage_page(client: TestClient, cat_id: int) -> None:
    r = client.get("/budget/manage")
    assert r.status_code == 200
    assert "Groceries" in r.text


def test_set_default(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/defaults/{cat_id}", data={"amount": "500"})
    assert r.status_code == 200
    assert "budget-stale" in r.headers["HX-Trigger"]


def test_set_default_404(client: TestClient) -> None:
    r = client.post("/budget/defaults/9999", data={"amount": "100"})
    assert r.status_code == 404


def test_set_default_invalid(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/defaults/{cat_id}", data={"amount": "nan"})
    assert r.status_code == 422


def test_set_default_negative(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/defaults/{cat_id}", data={"amount": "-5"})
    assert r.status_code == 422


def test_set_recurring(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/recurring/{cat_id}/5", data={"amount": "200"})
    assert r.status_code == 200


def test_set_recurring_404(client: TestClient) -> None:
    r = client.post("/budget/recurring/9999/5", data={"amount": "1"})
    assert r.status_code == 404


def test_set_recurring_bad_month(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/recurring/{cat_id}/13", data={"amount": "1"})
    assert r.status_code == 422


def test_set_recurring_bad_amount(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/recurring/{cat_id}/5", data={"amount": "nope"})
    assert r.status_code == 422


def test_set_one_off(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/one-off/{cat_id}/2026/10", data={"amount": "99"})
    assert r.status_code == 200


def test_set_one_off_404(client: TestClient) -> None:
    r = client.post("/budget/one-off/9999/2026/10", data={"amount": "1"})
    assert r.status_code == 404


def test_set_one_off_bad_month(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/one-off/{cat_id}/2026/14", data={"amount": "1"})
    assert r.status_code == 422


def test_set_one_off_bad_amount(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/budget/one-off/{cat_id}/2026/10", data={"amount": "nope"})
    assert r.status_code == 422
