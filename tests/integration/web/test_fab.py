"""T-069 — Quick-add FAB + slide-over form.

Template-level assertions only: the FAB ships on every primary surface,
its ``hx-get`` target is context-aware against the current path + ledger
``view`` query param, and the slide-over wrapper still carries the raw
form fragment (so legacy submit flows continue to work).
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag
from fastapi.testclient import TestClient


def _fab(client: TestClient, path: str) -> Tag:
    response = client.get(path)
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    fab = soup.find("button", class_="fab")
    assert isinstance(fab, Tag), f"FAB missing on {path}"
    return fab


def test_fab_present_on_overview(client: TestClient) -> None:
    fab = _fab(client, "/")
    assert fab.get("aria-label") == "Add transaction"
    assert fab.get("data-shortcut") == "n"
    assert fab.get("hx-get") == "/transactions/new"
    assert fab.get("hx-target") == "#modal-root"


def test_fab_present_on_ledger_actual(client: TestClient) -> None:
    fab = _fab(client, "/ledger")
    assert fab.get("hx-get") == "/transactions/new"


def test_fab_present_on_ledger_planned(client: TestClient) -> None:
    fab = _fab(client, "/ledger?view=planned")
    assert fab.get("hx-get") == "/planned/new"


def test_fab_present_on_ledger_recurring(client: TestClient) -> None:
    fab = _fab(client, "/ledger?view=recurring")
    assert fab.get("hx-get") == "/recurring/new"


def test_fab_present_on_accounts(client: TestClient) -> None:
    fab = _fab(client, "/accounts")
    assert fab.get("hx-get") == "/transactions/new"


def test_fab_present_on_budget(client: TestClient) -> None:
    fab = _fab(client, "/budget")
    assert fab.get("hx-get") == "/transactions/new"


def test_new_transaction_returns_slideover(client: TestClient) -> None:
    response = client.get("/transactions/new")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", attrs={"data-slideover": True})
    assert isinstance(container, Tag)
    assert container.get("role") == "dialog"
    assert container.get("aria-modal") == "true"
    # Form still mounts the legacy hx-post target so submit flow is intact.
    assert 'hx-post="/transactions"' in response.text


def test_new_planned_returns_slideover(client: TestClient) -> None:
    response = client.get("/planned/new")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", attrs={"data-slideover": True})
    assert isinstance(container, Tag)
    assert 'hx-post="/planned"' in response.text


def test_new_recurring_returns_slideover(client: TestClient) -> None:
    response = client.get("/recurring/new")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", attrs={"data-slideover": True})
    assert isinstance(container, Tag)
    assert 'hx-post="/recurring"' in response.text
