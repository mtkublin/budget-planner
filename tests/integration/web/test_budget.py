"""T-036 budget router."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup, Tag
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.budgets import NewBudgetDefault
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Direction
from budget_planner.repositories import (
    budgets as budgets_repo,
    categories as categories_repo,
)


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


def test_manage_page_redirects_to_budget_rules(client: TestClient, cat_id: int) -> None:
    """T-070: ``/budget/manage`` returns 302 to ``/budget#budget-rules``."""
    r = client.get("/budget/manage", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/budget#budget-rules"


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


# ---------------------------------------------------------------------------
# T-066 — three-section consolidation
# ---------------------------------------------------------------------------


def test_budget_three_sections(client: TestClient, cat_id: int) -> None:
    """Page exposes the three section anchors in order."""
    r = client.get("/budget")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    summary = soup.find(id="budget-summary")
    rules = soup.find(id="budget-rules")
    breakdown = soup.find(id="budget-breakdown")
    assert isinstance(summary, Tag)
    assert isinstance(rules, Tag)
    assert isinstance(breakdown, Tag)
    # Visual order matches the section narrative.
    order = [s.get("id") for s in soup.find_all("section") if isinstance(s, Tag)]
    assert (
        order.index("budget-summary")
        < order.index("budget-rules")
        < order.index("budget-breakdown")
    )


def test_budget_month_selector_swaps(client: TestClient, _migrated: Settings) -> None:
    """Changing the ``?month=`` query swaps the per-category planned amounts."""
    conn = get_connection(_migrated)
    try:
        cat = categories_repo.create(
            conn, NewCategory(name="Groceries", direction=Direction.EXPENSE)
        )
        # Set a default so the planned column shows a concrete number.
        budgets_repo.set_default(conn, NewBudgetDefault(category_id=cat.id, amount=12345))
    finally:
        conn.close()

    r_oct = client.get("/budget?year=2026&month=10")
    r_nov = client.get("/budget?year=2026&month=11")
    assert r_oct.status_code == 200
    assert r_nov.status_code == 200
    assert "2026-10" in r_oct.text
    assert "2026-11" in r_nov.text
    # The month selector mentions the queried month inside the one-off column
    # header, so the HTML must differ between the two requests.
    assert r_oct.text != r_nov.text


def test_budget_breakdown_has_three_charts(client: TestClient, cat_id: int) -> None:
    """The Breakdown section renders three Plotly placeholders."""
    r = client.get("/budget")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    breakdown = soup.find(id="budget-breakdown")
    assert isinstance(breakdown, Tag)
    charts = breakdown.select("[data-plotly]")
    ids = {c.get("id") for c in charts if isinstance(c, Tag)}
    assert ids == {"chart-spend", "chart-cashflow", "chart-monthly"}


def test_budget_manage_lands_on_rules_section(client: TestClient, cat_id: int) -> None:
    """``/budget/manage`` follows to ``/budget`` and the Rules section is present."""
    r = client.get("/budget/manage")  # follow_redirects=True by default
    assert r.status_code == 200
    assert "Rules" in r.text
