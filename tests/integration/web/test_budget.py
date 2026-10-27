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


# ---------------------------------------------------------------------------
# T-113 / ADR-0031 — Rules Override dispatcher + Yearly budget grid
# ---------------------------------------------------------------------------


def test_yearly_fragment_renders_for_year(client: TestClient, cat_id: int) -> None:
    r = client.get("/budget/yearly?year=2026")
    assert r.status_code == 200
    assert 'id="budget-yearly"' in r.text
    assert "Groceries" in r.text


def test_rules_section_renders_override_button(client: TestClient, cat_id: int) -> None:
    r = client.get("/budget")
    assert r.status_code == 200
    assert f"/budget/rules/{cat_id}/overrides/new" in r.text


def test_rules_default_input_renders_major_decimal(client: TestClient, cat_id: int) -> None:
    """Default budget inline input renders stored minor units as major-unit
    decimal with trailing zeros (e.g. 1550 minor → "15.50"), not the raw int."""
    client.post(f"/budget/defaults/{cat_id}", data={"amount": "15.50"})
    r = client.get("/budget")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    inp = soup.find("input", {"id": f"rule-default-{cat_id}"})
    assert isinstance(inp, Tag)
    assert inp.get("value") == "15.50"


def test_yearly_cell_renders_major_decimal(client: TestClient, cat_id: int) -> None:
    """Yearly grid cells render stored minor units as major-unit decimals."""
    client.post(f"/budget/one-off/{cat_id}/2026/7", data={"amount": "22.33"})
    r = client.get("/budget/yearly?year=2026")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    inp = soup.find("input", {"id": f"y-{cat_id}-7"})
    assert isinstance(inp, Tag)
    assert inp.get("value") == "22.33"


def test_new_override_form_404_for_unknown_category(client: TestClient) -> None:
    r = client.get("/budget/rules/9999/overrides/new")
    assert r.status_code == 404


def test_new_override_form_returns_slide_over(client: TestClient, cat_id: int) -> None:
    r = client.get(f"/budget/rules/{cat_id}/overrides/new")
    assert r.status_code == 200
    assert 'name="tier"' in r.text
    assert 'name="month"' in r.text
    assert 'name="amount"' in r.text


def test_create_override_recurring(client: TestClient, cat_id: int) -> None:
    r = client.post(
        f"/budget/rules/{cat_id}/overrides",
        data={"tier": "recurring", "month": "6", "amount": "250"},
    )
    assert r.status_code == 200
    assert "budget-stale" in r.headers["HX-Trigger"]


def test_create_override_one_off(client: TestClient, cat_id: int) -> None:
    r = client.post(
        f"/budget/rules/{cat_id}/overrides",
        data={"tier": "one-off", "month": "7", "year": "2026", "amount": "99"},
    )
    assert r.status_code == 200
    assert "budget-stale" in r.headers["HX-Trigger"]


def test_create_override_404_for_unknown_category(client: TestClient) -> None:
    r = client.post(
        "/budget/rules/9999/overrides",
        data={"tier": "recurring", "month": "6", "amount": "1"},
    )
    assert r.status_code == 404


def test_create_override_rejects_bad_tier(client: TestClient, cat_id: int) -> None:
    r = client.post(
        f"/budget/rules/{cat_id}/overrides",
        data={"tier": "monthly", "month": "6", "amount": "1"},
    )
    assert r.status_code == 422


def test_create_override_rejects_bad_month(client: TestClient, cat_id: int) -> None:
    r = client.post(
        f"/budget/rules/{cat_id}/overrides",
        data={"tier": "recurring", "month": "13", "amount": "1"},
    )
    assert r.status_code == 422


def test_create_override_rejects_bad_amount(client: TestClient, cat_id: int) -> None:
    r = client.post(
        f"/budget/rules/{cat_id}/overrides",
        data={"tier": "recurring", "month": "6", "amount": "nope"},
    )
    assert r.status_code == 422


def test_create_override_one_off_rejects_bad_year(client: TestClient, cat_id: int) -> None:
    r = client.post(
        f"/budget/rules/{cat_id}/overrides",
        data={"tier": "one-off", "month": "7", "year": "bogus", "amount": "1"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# T-120 / ADR-0039 — committed sub-line beneath left-daily-spend hero.
# ---------------------------------------------------------------------------
def test_budget_hero_renders_committed_subline(client: TestClient, cat_id: int) -> None:
    """Hero carries the 'X committed (recurring + planned)' sub-line."""
    # Set a default so the LDS hero actually surfaces (zero-budget hides it).
    client.post(f"/budget/defaults/{cat_id}", data={"amount": "100"})
    r = client.get("/budget")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    hero = soup.find(id="left-daily-spend")
    assert isinstance(hero, Tag)
    committed = hero.select_one(".budget-lds__committed")
    assert isinstance(committed, Tag)
    assert "committed" in committed.get_text(" ", strip=True)
    assert "recurring + planned" in committed.get_text(" ", strip=True)


def test_budget_hero_committed_zero_renders_flat_zero(client: TestClient, cat_id: int) -> None:
    """With no recurring + no planned, committed sub-line still renders a zero."""
    client.post(f"/budget/defaults/{cat_id}", data={"amount": "100"})
    r = client.get("/budget")
    assert r.status_code == 200
    soup = BeautifulSoup(r.text, "html.parser")
    hero = soup.find(id="left-daily-spend")
    assert isinstance(hero, Tag)
    committed = hero.select_one(".budget-lds__committed")
    assert isinstance(committed, Tag)
    assert committed.get("data-committed") == "0"


def test_budget_hero_committed_subline_survives_budget_stale_rerender(
    client: TestClient, cat_id: int
) -> None:
    """After mutating a budget (which emits budget-stale) and reloading, the
    sub-line is still present — HTMX-driven re-renders don't drop it."""
    client.post(f"/budget/defaults/{cat_id}", data={"amount": "100"})
    r1 = client.post(f"/budget/defaults/{cat_id}", data={"amount": "200"})
    assert "budget-stale" in r1.headers.get("HX-Trigger", "")
    r2 = client.get("/budget")
    assert r2.status_code == 200
    soup = BeautifulSoup(r2.text, "html.parser")
    assert soup.select_one(".budget-lds__committed") is not None
