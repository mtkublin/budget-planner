"""T-038 analytics router."""

from __future__ import annotations

import html
import json
from datetime import date
from typing import Any

import pytest
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
        acc = accounts_repo.create(conn, NewAccount(name="Main", currency="PLN"))
        groc = categories_repo.create(
            conn, NewCategory(name="Groceries", direction=Direction.EXPENSE)
        )
        salary = categories_repo.create(
            conn, NewCategory(name="Salary", direction=Direction.INCOME)
        )
        for d in (date(2026, 10, 1), date(2026, 10, 2)):
            transactions_repo.create(
                conn,
                NewTransaction(
                    operation_date=d,
                    category_id=groc.id,
                    account_id=acc.id,
                    amount=1000,
                ),
            )
        transactions_repo.create(
            conn,
            NewTransaction(
                operation_date=date(2026, 10, 10),
                category_id=salary.id,
                account_id=acc.id,
                amount=50000,
            ),
        )
        return {"acc": acc.id}
    finally:
        conn.close()


def _plotly_payload(text: str, attr_index: int = 0) -> dict[str, Any]:
    start = 0
    for _ in range(attr_index + 1):
        start = text.find('data-plotly="', start) + len('data-plotly="')
    end = text.find('"', start)
    result: dict[str, Any] = json.loads(html.unescape(text[start:end]))
    return result


def test_index_renders_three_charts(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/analytics")
    assert r.status_code == 200
    assert 'id="chart-spend"' in r.text
    assert 'id="chart-cashflow"' in r.text
    assert 'id="chart-monthly"' in r.text


def test_spend_payload_contains_groceries(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/analytics")
    payload = _plotly_payload(r.text, 0)
    labels = payload["data"][0]["x"]
    assert "Groceries" in labels


def test_cashflow_payload_shape(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/analytics")
    payload = _plotly_payload(r.text, 1)
    assert payload["data"][0]["type"] == "bar"


def test_monthly_bar_pair(client: TestClient, seeded: dict[str, int]) -> None:
    r = client.get("/analytics")
    payload = _plotly_payload(r.text, 2)
    names = {s["name"] for s in payload["data"]}
    assert names == {"income", "expense"}
