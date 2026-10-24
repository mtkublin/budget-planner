"""T-032 accounts router."""

from __future__ import annotations

import json
from datetime import date

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Direction
from budget_planner.domain.transactions import NewTransaction
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    transactions as transactions_repo,
)


@pytest.fixture
def acc_id(_migrated: Settings) -> int:
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(conn, NewAccount(name="Main", currency="PLN", opening_balance=0))
        return acc.id
    finally:
        conn.close()


def test_index_renders_with_grid(client: TestClient, acc_id: int) -> None:
    r = client.get("/accounts")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    assert soup.find(id="accounts-grid") is not None
    assert soup.find(id=f"account-{acc_id}") is not None


def test_new_form_fragment(client: TestClient) -> None:
    r = client.get("/accounts/new")
    assert r.status_code == 200
    assert 'name="currency"' in r.text


def test_create_account(client: TestClient) -> None:
    r = client.post(
        "/accounts",
        data={"name": "Travel", "currency": "EUR", "opening_balance": "100.00"},
    )
    assert r.status_code == 200
    assert "Travel" in r.text
    assert "balance-stale" in r.headers["HX-Trigger"]


def test_create_rejects_bad_currency(client: TestClient) -> None:
    r = client.post(
        "/accounts",
        data={"name": "X", "currency": "EURO", "opening_balance": "0"},
    )
    assert r.status_code == 422
    assert "currency" in r.text


def test_create_rejects_blank_name(client: TestClient) -> None:
    r = client.post(
        "/accounts",
        data={"name": "   ", "currency": "PLN", "opening_balance": "0"},
    )
    assert r.status_code == 422


def test_create_rejects_bad_opening(client: TestClient) -> None:
    r = client.post(
        "/accounts",
        data={"name": "A", "currency": "PLN", "opening_balance": "nan!"},
    )
    assert r.status_code == 422


def test_edit_and_update(client: TestClient, acc_id: int) -> None:
    r = client.get(f"/accounts/{acc_id}/edit")
    assert r.status_code == 200
    r2 = client.post(f"/accounts/{acc_id}", data={"name": "Renamed", "type": "checking"})
    assert r2.status_code == 200
    assert "Renamed" in r2.text


def test_edit_404(client: TestClient) -> None:
    assert client.get("/accounts/9999/edit").status_code == 404


def test_update_404(client: TestClient) -> None:
    assert client.post("/accounts/9999", data={"name": "X"}).status_code == 404


def test_update_blank_name(client: TestClient, acc_id: int) -> None:
    r = client.post(f"/accounts/{acc_id}", data={"name": "   "})
    assert r.status_code == 422


def test_delete(client: TestClient, acc_id: int, _migrated: Settings) -> None:
    r = client.post(f"/accounts/{acc_id}/delete")
    assert r.status_code == 200
    assert r.text == ""
    hx = json.loads(r.headers["HX-Trigger"])
    assert hx == {"balance-stale": True, "forecast-stale": True}


def test_snapshot(client: TestClient, acc_id: int, _migrated: Settings) -> None:
    conn = get_connection(_migrated)
    try:
        cat = categories_repo.create(conn, NewCategory(name="X", direction=Direction.EXPENSE))
        transactions_repo.create(
            conn,
            NewTransaction(
                operation_date=date(2026, 10, 1),
                category_id=cat.id,
                account_id=acc_id,
                amount=1000,
            ),
        )
    finally:
        conn.close()
    r = client.post(f"/accounts/{acc_id}/snapshot")
    assert r.status_code == 200
    assert "<li>" in r.text


def test_snapshot_404(client: TestClient) -> None:
    assert client.post("/accounts/9999/snapshot").status_code == 404


def test_reconcile_form_renders(client: TestClient, acc_id: int) -> None:
    r = client.get(f"/accounts/{acc_id}/reconcile")
    assert r.status_code == 200
    assert "actual_balance" in r.text


def test_reconcile_form_404(client: TestClient) -> None:
    assert client.get("/accounts/9999/reconcile").status_code == 404


def test_reconcile_submit(client: TestClient, acc_id: int) -> None:
    r = client.post(f"/accounts/{acc_id}/reconcile", data={"actual_balance": "123.45"})
    assert r.status_code == 200
    hx = json.loads(r.headers["HX-Trigger"])
    assert hx == {"balance-stale": True, "forecast-stale": True}


def test_reconcile_submit_bad_number(client: TestClient, acc_id: int) -> None:
    r = client.post(f"/accounts/{acc_id}/reconcile", data={"actual_balance": "notnum"})
    assert r.status_code == 422


def test_reconcile_submit_404(client: TestClient) -> None:
    assert client.post("/accounts/9999/reconcile", data={"actual_balance": "1"}).status_code == 404


def test_reconcile_zero_delta_still_200(client: TestClient, acc_id: int) -> None:
    # Opening balance 0 - submitting 0 means no delta; the service raises
    # NoAdjustmentNeededError which the router swallows.
    r = client.post(f"/accounts/{acc_id}/reconcile", data={"actual_balance": "0"})
    assert r.status_code == 200
