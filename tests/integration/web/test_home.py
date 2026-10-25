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
    """Four-tab rail + Settings affordance (ADR-0023).

    Ledger points at /transactions until T-064 lands /ledger; Settings points
    at /categories until T-067 lands /settings. Future tasks flip these hrefs
    without changing the number of nav items.
    """
    r = client.get("/")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    hrefs = {a["href"] for a in soup.select("nav a")}
    for path in ("/", "/transactions", "/accounts", "/budget", "/categories"):
        assert path in hrefs, f"nav missing {path}"


def test_nav_has_four_primary_items_plus_settings(client: TestClient) -> None:
    r = client.get("/")
    soup = BeautifulSoup(r.text, "html.parser")
    primary = soup.select("nav ul.rail-list:not(.rail-list--footer) a")
    footer = soup.select("nav ul.rail-list--footer a")
    assert len(primary) == 4, f"expected 4 primary rail items, got {len(primary)}"
    assert len(footer) == 1, f"expected 1 footer rail item (Settings), got {len(footer)}"


def test_shell_slots_present(client: TestClient) -> None:
    """T-061: base shell exposes drawer-root + modal-root for later tasks."""
    r = client.get("/")
    soup = BeautifulSoup(r.text, "html.parser")
    assert soup.find(id="drawer-root") is not None
    assert soup.find(id="modal-root") is not None
    assert soup.select_one(".app-shell__rail") is not None
    assert soup.select_one(".app-shell__main") is not None


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
