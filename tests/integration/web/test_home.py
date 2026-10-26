"""T-039 home + navigation + T-063 overview composition."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.budgets import NewBudgetDefault
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Direction
from budget_planner.domain.planned import NewPlannedTransaction
from budget_planner.domain.transactions import NewTransaction
from budget_planner.repositories import (
    accounts as accounts_repo,
    budgets as budgets_repo,
    categories as categories_repo,
    planned as planned_repo,
    transactions as transactions_repo,
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
    assert "No planned payments in this window." in r.text


def test_overview_three_panels(client: TestClient, _migrated: Settings) -> None:
    """Three panels are present with the asserted IDs + the sum closure line matches."""
    conn = get_connection(_migrated)
    try:
        acc_a = accounts_repo.create(
            conn, NewAccount(name="Alpha", currency="PLN", opening_balance=250000)
        )
        acc_b = accounts_repo.create(
            conn, NewAccount(name="Beta", currency="PLN", opening_balance=150000)
        )
        cat = categories_repo.create(conn, NewCategory(name="Food", direction=Direction.EXPENSE))
        budgets_repo.set_default(conn, NewBudgetDefault(category_id=cat.id, amount=100000))
        transactions_repo.create(
            conn,
            NewTransaction(
                operation_date=date.today(),  # noqa: DTZ011
                category_id=cat.id,
                account_id=acc_a.id,
                amount=200000,  # 2000.00 > 1000.00 budgeted → over_budget
                description="Groceries",
            ),
        )
        assert acc_b.id  # keep ref alive for mypy
    finally:
        conn.close()

    r = client.get("/")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    assert soup.select_one('[data-panel="accounts"]') is not None
    assert soup.select_one('[data-panel="month"]') is not None
    assert soup.select_one('[data-panel="upcoming"]') is not None
    assert soup.find(id="fortune") is not None
    assert soup.find(id="budget-card") is not None
    assert soup.find(id="upcoming") is not None

    # Fortune hero + closure line should both render the same total (minus any txn impact).
    # Opening: 2500 + 1500 = 4000.  Expense txn: -2000.  Expected fortune: 2000.00 PLN.
    closure = soup.select_one(".account-list__closure")
    assert closure is not None
    assert "2,000.00 PLN" in closure.get_text()

    # Pace tag should be "over budget" given spent 2000 > budgeted 1000.
    pace = soup.select_one(".pace-tag")
    assert pace is not None
    assert pace.get("data-pace") == "over_budget"
    assert "over budget" in pace.get_text()


def test_overview_upcoming_fragment(client: TestClient, seeded: None) -> None:
    r = client.get("/overview/upcoming?window=7")
    assert r.status_code == 200
    # Fragment: no <html> wrapper, but the list body renders.
    assert "<html" not in r.text.lower()
    assert "Bread" in r.text


def test_overview_overdue_muted(client: TestClient, _migrated: Settings) -> None:
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(conn, NewAccount(name="Main", currency="PLN", opening_balance=0))
        cat = categories_repo.create(conn, NewCategory(name="Rent", direction=Direction.EXPENSE))
        past = date.today() - timedelta(days=3)  # noqa: DTZ011
        future = date.today() + timedelta(days=3)  # noqa: DTZ011
        planned_repo.create(
            conn,
            NewPlannedTransaction(
                operation_date=past,
                category_id=cat.id,
                account_id=acc.id,
                amount=5000,
                description="Overdue bill",
            ),
        )
        planned_repo.create(
            conn,
            NewPlannedTransaction(
                operation_date=future,
                category_id=cat.id,
                account_id=acc.id,
                amount=6000,
                description="Future bill",
            ),
        )
    finally:
        conn.close()

    r = client.get("/")
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select(".upcoming-row")
    assert len(rows) == 2
    overdue = [r for r in rows if "Overdue bill" in r.get_text()]
    future_rows = [r for r in rows if "Future bill" in r.get_text()]
    assert overdue and "upcoming-row--overdue" in (overdue[0].get("class") or [])
    assert future_rows and "upcoming-row--overdue" not in (future_rows[0].get("class") or [])
    assert "overdue" in overdue[0].get_text().lower()


def test_overview_promoted_hidden(client: TestClient, _migrated: Settings) -> None:
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(conn, NewAccount(name="Main", currency="PLN", opening_balance=0))
        cat = categories_repo.create(conn, NewCategory(name="Rent", direction=Direction.EXPENSE))
        soon = date.today() + timedelta(days=2)  # noqa: DTZ011
        planned_row = planned_repo.create(
            conn,
            NewPlannedTransaction(
                operation_date=soon,
                category_id=cat.id,
                account_id=acc.id,
                amount=4200,
                description="Already promoted",
            ),
        )
        # Create a transaction to attach then stamp promotion.
        txn = transactions_repo.create(
            conn,
            NewTransaction(
                operation_date=soon,
                category_id=cat.id,
                account_id=acc.id,
                amount=4200,
                description="Already promoted",
                promoted_from_planned_id=planned_row.id,
            ),
        )
        planned_repo.stamp_promotion(conn, planned_row.id, txn.id)
    finally:
        conn.close()

    r = client.get("/overview/upcoming?window=30")
    assert r.status_code == 200
    assert "Already promoted" not in r.text
    assert "No planned payments in this window." in r.text
