"""T-035 recurring router + T-118 promote/skip routes."""

from __future__ import annotations

import datetime as dt
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Cadence, Direction
from budget_planner.domain.recurring import NewRecurringRule
from budget_planner.domain.transactions import TransactionFilter
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    recurring as recurring_repo,
    transactions as transactions_repo,
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


def test_index_redirects_to_ledger(client: TestClient, ctx: dict[str, int]) -> None:
    """T-070: ``/recurring`` returns 302 to the unified ledger (recurring view)."""
    r = client.get("/recurring", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/ledger?view=recurring"


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


# ---------------------------------------------------------------------------
# T-118 — promote + skip-next routes (ADR-0038)
# ---------------------------------------------------------------------------
def _get_rule_next_due(_migrated: Settings, rule_id: int) -> date:
    conn = get_connection(_migrated)
    try:
        rule = recurring_repo.find_rule(conn, rule_id)
        assert rule is not None
        return rule.next_due
    finally:
        conn.close()


def test_promote_form_renders(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.get(f"/recurring/{ctx['rule']}/promote")
    assert r.status_code == 200
    assert "Promote recurring" in r.text
    assert f"/recurring/{ctx['rule']}/promote" in r.text


def test_promote_form_404(client: TestClient) -> None:
    r = client.get("/recurring/9999/promote")
    assert r.status_code == 404


def test_promote_submit_no_edits(
    client: TestClient, ctx: dict[str, int], _migrated: Settings
) -> None:
    r = client.post(f"/recurring/{ctx['rule']}/promote", data={})
    assert r.status_code == 200
    payload = json.loads(r.headers["HX-Trigger"])
    assert payload == {"ledger-stale": True, "forecast-stale": True, "budget-stale": True}

    # DB side-effect: rule's next_due advanced + one new transaction exists.
    conn = get_connection(_migrated)
    try:
        rows = transactions_repo.list_filtered(conn, TransactionFilter())
        assert len(rows) == 1
        assert rows[0].promoted_from_recurring_rule_id == ctx["rule"]
    finally:
        conn.close()


def test_promote_submit_404(client: TestClient) -> None:
    r = client.post("/recurring/9999/promote", data={})
    assert r.status_code == 404


def test_promote_submit_invalid_amount_422(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/promote",
        data={"amount": "not-a-number"},
    )
    assert r.status_code == 422
    assert "amount" in r.text.lower()


def test_promote_submit_zero_amount_422(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/promote",
        data={"amount": "0"},
    )
    assert r.status_code == 422


def test_promote_submit_invalid_date_422(client: TestClient, ctx: dict[str, int]) -> None:
    r = client.post(
        f"/recurring/{ctx['rule']}/promote",
        data={"operation_date": "not-a-date"},
    )
    assert r.status_code == 422


def test_promote_submit_cross_currency_transit_422(client: TestClient, _migrated: Settings) -> None:
    conn = get_connection(_migrated)
    try:
        pln = accounts_repo.create(conn, NewAccount(name="PLN", currency="PLN")).id
        eur = accounts_repo.create(conn, NewAccount(name="EUR", currency="EUR")).id
        transit = categories_repo.find_by_name(conn, "Transit")
        assert transit is not None
        transit_rule = recurring_repo.create_rule(
            conn,
            NewRecurringRule(
                cadence=Cadence.MONTHLY,
                start_date=date(2026, 1, 5),
                category_id=transit.id,
                account_id=pln,
                dest_account_id=eur,
                default_amount=1000,
            ),
        )
        rule_id = transit_rule.id
    finally:
        conn.close()
    r = client.post(f"/recurring/{rule_id}/promote", data={})
    assert r.status_code == 422


def test_skip_next_advances(client: TestClient, ctx: dict[str, int], _migrated: Settings) -> None:
    before = _get_rule_next_due(_migrated, ctx["rule"])
    r = client.post(f"/recurring/{ctx['rule']}/skip-next")
    assert r.status_code == 200
    payload = json.loads(r.headers["HX-Trigger"])
    assert payload == {"ledger-stale": True, "forecast-stale": True, "budget-stale": True}
    after = _get_rule_next_due(_migrated, ctx["rule"])
    assert after > before

    # No new transaction.
    conn = get_connection(_migrated)
    try:
        rows = transactions_repo.list_filtered(conn, TransactionFilter())
        assert len(rows) == 0
    finally:
        conn.close()


def test_skip_next_404(client: TestClient) -> None:
    r = client.post("/recurring/9999/skip-next")
    assert r.status_code == 404


def test_promote_submit_backfilled_next_due(client: TestClient, _migrated: Settings) -> None:
    """Fresh-DB regression: a rule whose next_due was computed on insert
    (equivalent to the T-117 backfill path) promotes a transaction dated at
    that next_due."""
    conn = get_connection(_migrated)
    try:
        acc = accounts_repo.create(conn, NewAccount(name="Freshly", currency="PLN"))
        cat = categories_repo.create(
            conn, NewCategory(name="Utilities", direction=Direction.EXPENSE)
        )
        # Pick a start_date in the past so repository backfills next_due to a
        # future canonical date (not start_date itself).
        past_start = dt.date.today() - dt.timedelta(days=800)  # noqa: DTZ011
        rule = recurring_repo.create_rule(
            conn,
            NewRecurringRule(
                cadence=Cadence.MONTHLY,
                start_date=past_start,
                category_id=cat.id,
                account_id=acc.id,
                default_amount=50_000,
            ),
        )
        backfilled = rule.next_due
    finally:
        conn.close()

    r = client.post(f"/recurring/{rule.id}/promote", data={})
    assert r.status_code == 200

    conn = get_connection(_migrated)
    try:
        rows = transactions_repo.list_filtered(conn, TransactionFilter(account_ids=(acc.id,)))
        assert len(rows) == 1
        assert rows[0].operation_date == backfilled
        assert rows[0].promoted_from_recurring_date == backfilled
    finally:
        conn.close()
