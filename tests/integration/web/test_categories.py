"""T-033 categories router."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
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
    r = client.get("/categories")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    assert soup.find(id=f"category-{cat_id}") is not None
    # system categories should show
    assert "Transit" in r.text


def test_new_form(client: TestClient) -> None:
    r = client.get("/categories/new")
    assert r.status_code == 200
    assert 'name="direction"' in r.text


def test_create(client: TestClient) -> None:
    r = client.post("/categories", data={"name": "Rent", "direction": "expense"})
    assert r.status_code == 200
    assert "Rent" in r.text
    assert "budget-stale" in r.headers["HX-Trigger"]


def test_create_bad_direction(client: TestClient) -> None:
    r = client.post("/categories", data={"name": "X", "direction": "bogus"})
    assert r.status_code == 422


def test_create_blank_name(client: TestClient) -> None:
    r = client.post("/categories", data={"name": "   ", "direction": "expense"})
    assert r.status_code == 422


def test_edit(client: TestClient, cat_id: int) -> None:
    r = client.get(f"/categories/{cat_id}/edit")
    assert r.status_code == 200


def test_edit_404(client: TestClient) -> None:
    assert client.get("/categories/9999/edit").status_code == 404


def test_update(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/categories/{cat_id}", data={"name": "Food"})
    assert r.status_code == 200
    assert "Food" in r.text


def test_update_404(client: TestClient) -> None:
    assert client.post("/categories/9999", data={"name": "X"}).status_code == 404


def test_update_blank(client: TestClient, cat_id: int) -> None:
    assert client.post(f"/categories/{cat_id}", data={"name": "  "}).status_code == 422


def test_delete(client: TestClient, cat_id: int) -> None:
    r = client.post(f"/categories/{cat_id}/delete")
    assert r.status_code == 200
    assert "budget-stale" in r.headers["HX-Trigger"]


def test_delete_404(client: TestClient) -> None:
    assert client.post("/categories/9999/delete").status_code == 404


def test_delete_system_blocked(client: TestClient, _migrated: Settings) -> None:
    conn = get_connection(_migrated)
    try:
        transit = next(c for c in categories_repo.list_all(conn) if c.is_system)
    finally:
        conn.close()
    r = client.post(f"/categories/{transit.id}/delete")
    assert r.status_code == 409
