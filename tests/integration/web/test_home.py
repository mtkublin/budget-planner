"""T-039 home + navigation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Direction
from budget_planner.domain.planned import NewPlannedTransaction
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    planned as planned_repo,
)


@pytest.fixture
def seeded(_migrated: Settings) -> None:
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(
            conn, NewAccount(name="Main", currency="PLN", opening_balance=100000)
        )
        cat = categories_repo.create(
            conn, NewCategory(name="Groceries", direction=Direction.EXPENSE)
        )
        soon = date.today() + timedelta(days=3)  # noqa: DTZ011
        planned_repo.create(
            conn,
            NewPlannedTransaction(
                operation_date=soon,
                category_id=cat.id,
                account_id=acc.id,
                amount=1000,
                description="Bread",
            ),
        )
    finally:
        conn.close()


def test_home_renders(client: TestClient, seeded: None) -> None:
    r = client.get("/")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    assert soup.find(id="fortune") is not None
    assert soup.find(id="budget-card") is not None
    assert soup.find(id="upcoming") is not None


def test_nav_links_present(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    hrefs = {a["href"] for a in soup.select("nav a")}
    for path in (
        "/",
        "/transactions",
        "/accounts",
        "/categories",
        "/planned",
        "/recurring",
        "/budget",
        "/forecast",
        "/analytics",
    ):
        assert path in hrefs


def test_fortune_shows_base_total(client: TestClient, seeded: None) -> None:
    r = client.get("/")
    assert "1,000.00 PLN" in r.text


def test_upcoming_lists_planned(client: TestClient, seeded: None) -> None:
    r = client.get("/")
    assert "Bread" in r.text


def test_empty_db_home(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Nothing on the schedule" in r.text
