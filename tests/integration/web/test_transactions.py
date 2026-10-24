"""T-031 transactions router — structural + mutation tests."""

from __future__ import annotations

import io
import json
from datetime import date

import pyarrow.parquet as pq
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
def seeded(_migrated: Settings) -> dict[str, int]:
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(conn, NewAccount(name="Main", currency="PLN", opening_balance=0))
        acc2 = accounts_repo.create(
            conn, NewAccount(name="Savings", currency="PLN", opening_balance=0)
        )
        groc = categories_repo.create(
            conn, NewCategory(name="Groceries", direction=Direction.EXPENSE)
        )
        salary = categories_repo.create(
            conn, NewCategory(name="Salary", direction=Direction.INCOME)
        )
        return {"acc": acc.id, "acc2": acc2.id, "groc": groc.id, "salary": salary.id}
    finally:
        conn.close()


def _create_txn(
    settings: Settings, acc_id: int, cat_id: int, *, amount: int = 100, desc: str = "x"
) -> int:
    conn = get_connection(settings)
    try:
        txn = transactions_repo.create(
            conn,
            NewTransaction(
                operation_date=date(2026, 10, 1),
                category_id=cat_id,
                account_id=acc_id,
                amount=amount,
                description=desc,
            ),
        )
        return txn.id
    finally:
        conn.close()


def test_list_page_renders(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/transactions")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    assert soup.find(id="txn-table") is not None
    btn = soup.find("button", string=lambda s: s is not None and "+ New" in s)
    assert btn is not None
    form_names = {inp.get("name") for inp in soup.find_all(["input", "select"])}
    for n in ("date_from", "date_to", "category_id", "account_id", "min_amount", "max_amount", "q"):
        assert n in form_names


def test_table_fragment_is_not_full_page(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/transactions/table")
    assert r.status_code == 200
    assert "<html" not in r.text
    assert "txn-table" in r.text


def test_new_form_fragment(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/transactions/new")
    assert r.status_code == 200
    assert 'hx-post="/transactions"' in r.text
    for field in ("operation_date", "category_id", "account_id", "amount"):
        assert f'name="{field}"' in r.text


def test_create_valid_persists_and_triggers(
    client: TestClient, seeded: dict[str, int], _migrated: Settings
) -> None:
    r = client.post(
        "/transactions",
        data={
            "operation_date": "2026-10-20",
            "category_id": seeded["groc"],
            "account_id": seeded["acc"],
            "amount": "12.34",
            "description": "Test",
        },
    )
    assert r.status_code == 200
    assert 'id="txn-' in r.text
    hx = json.loads(r.headers["HX-Trigger"])
    assert hx == {"balance-stale": True, "forecast-stale": True}
    conn = get_connection(_migrated)
    try:
        row = conn.execute("SELECT amount, description FROM transactions").fetchone()
    finally:
        conn.close()
    assert row[0] == 1234
    assert row[1] == "Test"


def test_create_invalid_amount_returns_form(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.post(
        "/transactions",
        data={
            "operation_date": "2026-10-20",
            "category_id": seeded["groc"],
            "account_id": seeded["acc"],
            "amount": "-5",
        },
    )
    assert r.status_code == 422
    assert "amount" in r.text


def test_create_rejects_cross_currency_transit(client: TestClient, _migrated: Settings) -> None:
    conn = get_connection(_migrated)
    try:
        acc_pln = accounts_repo.create(conn, NewAccount(name="A", currency="PLN"))
        acc_eur = accounts_repo.create(conn, NewAccount(name="B", currency="EUR"))
        cat = categories_repo.create(
            conn, NewCategory(name="Transit X", direction=Direction.TRANSIT)
        )
    finally:
        conn.close()
    r = client.post(
        "/transactions",
        data={
            "operation_date": "2026-10-20",
            "category_id": cat.id,
            "account_id": acc_pln.id,
            "dest_account_id": acc_eur.id,
            "amount": "10",
        },
    )
    assert r.status_code == 422
    assert "cross-currency" in r.text


def test_edit_and_update(client: TestClient, seeded: dict[str, int], _migrated: Settings) -> None:
    txn_id = _create_txn(_migrated, seeded["acc"], seeded["groc"], amount=5000)
    r = client.get(f"/transactions/{txn_id}/edit")
    assert r.status_code == 200
    assert f'hx-post="/transactions/{txn_id}"' in r.text
    r2 = client.post(
        f"/transactions/{txn_id}",
        data={
            "operation_date": "2026-10-02",
            "category_id": seeded["groc"],
            "account_id": seeded["acc"],
            "amount": "99.99",
            "description": "new",
        },
    )
    assert r2.status_code == 200
    assert json.loads(r2.headers["HX-Trigger"]) == {
        "balance-stale": True,
        "forecast-stale": True,
    }


def test_delete_soft_deletes(
    client: TestClient, seeded: dict[str, int], _migrated: Settings
) -> None:
    txn_id = _create_txn(_migrated, seeded["acc"], seeded["groc"])
    r = client.post(f"/transactions/{txn_id}/delete")
    assert r.status_code == 200
    assert r.text == ""
    assert "balance-stale" in r.headers["HX-Trigger"]
    conn = get_connection(_migrated)
    try:
        row = conn.execute("SELECT deleted_at FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    finally:
        conn.close()
    assert row[0] is not None


def test_export_csv(client: TestClient, seeded: dict[str, int], _migrated: Settings) -> None:
    for i in range(3):
        _create_txn(_migrated, seeded["acc"], seeded["groc"], amount=100 + i, desc=f"row{i}")
    r = client.get("/transactions/export?format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert len(lines) == 4  # header + 3


def test_export_parquet(client: TestClient, seeded: dict[str, int], _migrated: Settings) -> None:
    _create_txn(_migrated, seeded["acc"], seeded["groc"])
    r = client.get("/transactions/export?format=parquet")
    assert r.status_code == 200
    tbl = pq.read_table(io.BytesIO(r.content))
    assert tbl.num_rows == 1


def test_create_rejects_unknown_account_and_category(
    client: TestClient,
) -> None:
    r = client.post(
        "/transactions",
        data={
            "operation_date": "2026-10-20",
            "category_id": 9999,
            "account_id": 9999,
            "amount": "10",
        },
    )
    assert r.status_code == 422
    assert "unknown account" in r.text


def test_create_rejects_bad_date(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.post(
        "/transactions",
        data={
            "operation_date": "not-a-date",
            "category_id": seeded["groc"],
            "account_id": seeded["acc"],
            "amount": "10",
        },
    )
    assert r.status_code == 422
    assert "operation_date" in r.text


def test_create_rejects_bad_amount_string(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.post(
        "/transactions",
        data={
            "operation_date": "2026-10-20",
            "category_id": seeded["groc"],
            "account_id": seeded["acc"],
            "amount": "abc",
        },
    )
    assert r.status_code == 422


def test_edit_404(client: TestClient) -> None:
    r = client.get("/transactions/9999/edit")
    assert r.status_code == 404


def test_update_404(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.post(
        "/transactions/9999",
        data={
            "operation_date": "2026-10-20",
            "category_id": seeded["groc"],
            "account_id": seeded["acc"],
            "amount": "10",
        },
    )
    assert r.status_code == 404


def test_update_invalid(client: TestClient, seeded: dict[str, int], _migrated: Settings) -> None:
    txn_id = _create_txn(_migrated, seeded["acc"], seeded["groc"])
    r = client.post(
        f"/transactions/{txn_id}",
        data={
            "operation_date": "bad",
            "category_id": seeded["groc"],
            "account_id": seeded["acc"],
            "amount": "-1",
        },
    )
    assert r.status_code == 422


def test_bad_query_params_tolerated(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/transactions?account_id=notanint&page=notanint&min_amount=xx")
    assert r.status_code == 200


def test_filter_by_category(
    client: TestClient, seeded: dict[str, int], _migrated: Settings
) -> None:
    _create_txn(_migrated, seeded["acc"], seeded["groc"], desc="g")
    _create_txn(_migrated, seeded["acc"], seeded["salary"], desc="s")
    r = client.get(f"/transactions/table?category_id={seeded['groc']}")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    descs = {td.text.strip() for td in soup.find_all("td", class_="text-muted")}
    assert "g" in descs
    assert "s" not in descs
