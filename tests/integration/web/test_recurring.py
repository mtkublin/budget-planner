"""T-035 recurring router."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Cadence, Direction
from budget_planner.domain.recurring import NewRecurringRule
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    recurring as recurring_repo,
)


@pytest.fixture
def ctx(_migrated: Settings) -> dict[str, int]:
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(conn, NewAccount(name="Main", currency="PLN"))
        cat = categories_repo.create(conn, NewCategory(name="Rent", direction=Direction.EXPENSE))
        rule = recurring_repo.create_rule(
            conn,
            NewRecurringRule(
                cadence=Cadence.MONTHLY,
                start_date=date(2026, 1, 1),
                category_id=cat.id,
                account_id=acc.id,
                default_amount=50000,
            ),
        )
        return {"acc": acc.id, "cat": cat.id, "rule": rule.id}
    finally:
        conn.close()


def test_index(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.get("/recurring")
    assert r.status_code == 200
    assert f'id="recurring-{ctx["rule"]}"' in r.text


def test_new_form(client: TestClient) -> None:
    r = client.get("/recurring/new")
    assert r.status_code == 200
    assert 'name="cadence"' in r.text


def test_create(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        "/recurring",
        data={
            "cadence": "monthly",
            "start_date": "2026-02-01",
            "category_id": ctx["cat"],
            "account_id": ctx["acc"],
            "default_amount": "500",
        },
    )
    assert r.status_code == 200
    assert "forecast-stale" in r.headers["HX-Trigger"]


def test_create_invalid_cadence(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        "/recurring",
        data={
            "cadence": "bogus",
            "start_date": "2026-02-01",
            "category_id": ctx["cat"],
            "account_id": ctx["acc"],
            "default_amount": "1",
        },
    )
    assert r.status_code == 422


def test_create_invalid_date(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        "/recurring",
        data={
            "cadence": "monthly",
            "start_date": "nope",
            "category_id": ctx["cat"],
            "account_id": ctx["acc"],
            "default_amount": "1",
        },
    )
    assert r.status_code == 422


def test_create_invalid_amount(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        "/recurring",
        data={
            "cadence": "monthly",
            "start_date": "2026-02-01",
            "category_id": ctx["cat"],
            "account_id": ctx["acc"],
            "default_amount": "-5",
        },
    )
    assert r.status_code == 422


def test_create_unknown_account(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        "/recurring",
        data={
            "cadence": "monthly",
            "start_date": "2026-02-01",
            "category_id": ctx["cat"],
            "account_id": 9999,
            "default_amount": "1",
        },
    )
    assert r.status_code == 422


def test_edit(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.get(f"/recurring/{ctx['rule']}/edit")
    assert r.status_code == 200


def test_edit_404(client: TestClient) -> None:
    assert client.get("/recurring/9999/edit").status_code == 404


def test_update(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}",
        data={
            "cadence": "monthly",
            "start_date": "2026-03-01",
            "category_id": ctx["cat"],
            "account_id": ctx["acc"],
            "default_amount": "777",
        },
    )
    assert r.status_code == 200


def test_update_404(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        "/recurring/9999",
        data={
            "cadence": "monthly",
            "start_date": "2026-03-01",
            "category_id": ctx["cat"],
            "account_id": ctx["acc"],
            "default_amount": "1",
        },
    )
    assert r.status_code == 404


def test_update_invalid(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}",
        data={
            "cadence": "bogus",
            "start_date": "x",
            "category_id": ctx["cat"],
            "account_id": ctx["acc"],
            "default_amount": "-1",
        },
    )
    assert r.status_code == 422


def test_deactivate(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(f"/recurring/{ctx['rule']}/deactivate")
    assert r.status_code == 200


def test_deactivate_404(client: TestClient) -> None:
    assert client.post("/recurring/9999/deactivate").status_code == 404


def test_add_override_skipped(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/overrides",
        data={"occurrence_date": "2026-05-01", "state": "skipped"},
    )
    assert r.status_code == 200
    assert "forecast-stale" in r.headers["HX-Trigger"]


def test_add_override_overridden_amount(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/overrides",
        data={
            "occurrence_date": "2026-05-01",
            "state": "overridden",
            "amount_override": "9.99",
        },
    )
    assert r.status_code == 200


def test_override_invalid_state(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/overrides",
        data={"occurrence_date": "2026-05-01", "state": "bogus"},
    )
    assert r.status_code == 422


def test_override_invalid_date(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/overrides",
        data={"occurrence_date": "nope", "state": "skipped"},
    )
    assert r.status_code == 422


def test_override_invalid_amount(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/overrides",
        data={
            "occurrence_date": "2026-05-01",
            "state": "overridden",
            "amount_override": "nope",
        },
    )
    assert r.status_code == 422


def test_override_404_rule(client: TestClient) -> None:
    r = client.post(
        "/recurring/9999/overrides",
        data={"occurrence_date": "2026-05-01", "state": "skipped"},
    )
    assert r.status_code == 404


def test_delete_override(client: TestClient, ctx: dict[str, int]) -> None:
    client.post(
        f"/recurring/{ctx['rule']}/overrides",
        data={"occurrence_date": "2026-05-01", "state": "skipped"},
    )
    r = client.post(f"/recurring/{ctx['rule']}/overrides/2026-05-01/delete")
    assert r.status_code == 200


def test_delete_override_404_rule(client: TestClient) -> None:
    assert client.post("/recurring/9999/overrides/2026-05-01/delete").status_code == 404


def test_delete_override_bad_date(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(f"/recurring/{ctx['rule']}/overrides/bad/delete")
    assert r.status_code == 422
