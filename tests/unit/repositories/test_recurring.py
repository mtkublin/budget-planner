from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.recurring import (
    NewRecurringOverride,
    NewRecurringRule,
    PatchRecurringRule,
)
from budget_planner.repositories import audit, recurring


def _new_rule(account_id: int, category_id: int) -> NewRecurringRule:
    return NewRecurringRule(
        cadence=Cadence.MONTHLY,
        start_date=date(2026, 1, 1),
        category_id=category_id,
        account_id=account_id,
        default_amount=100,
        day_of_month=1,
    )


def test_create_rule_round_trip(
    conn: sqlite3.Connection, account_id: int, category_id: int
) -> None:
    rule = recurring.create_rule(conn, _new_rule(account_id, category_id))
    assert recurring.find_rule(conn, rule.id) == rule
    rules = recurring.list_rules(conn)
    assert any(r.id == rule.id for r in rules)
    assert audit.list_entries(conn, "recurring_rule", rule.id)[0].operation.value == ("create")


def test_update_rule_fields(conn: sqlite3.Connection, account_id: int, category_id: int) -> None:
    rule = recurring.create_rule(conn, _new_rule(account_id, category_id))
    updated = recurring.update_rule(
        conn,
        rule.id,
        PatchRecurringRule(
            cadence=Cadence.QUARTERLY,
            start_date=date(2026, 2, 1),
            end_date=date(2027, 1, 1),
            default_amount=250,
            active=False,
        ),
    )
    assert updated.cadence is Cadence.QUARTERLY
    assert updated.start_date == date(2026, 2, 1)
    assert updated.end_date == date(2027, 1, 1)
    assert updated.active is False


def test_deactivate_and_soft_delete(
    conn: sqlite3.Connection, account_id: int, category_id: int
) -> None:
    rule = recurring.create_rule(conn, _new_rule(account_id, category_id))
    deactivated = recurring.deactivate_rule(conn, rule.id)
    assert deactivated.active is False
    recurring.soft_delete_rule(conn, rule.id)
    assert recurring.find_rule(conn, rule.id) is None
    assert recurring.find_rule(conn, rule.id, include_deleted=True) is not None
    recurring.soft_delete_rule(conn, 999)  # no-op path


def test_list_rules_active_only(
    conn: sqlite3.Connection, account_id: int, category_id: int
) -> None:
    r1 = recurring.create_rule(conn, _new_rule(account_id, category_id))
    r2 = recurring.create_rule(conn, _new_rule(account_id, category_id))
    recurring.deactivate_rule(conn, r2.id)
    actives = recurring.list_rules(conn, active_only=True)
    ids = {r.id for r in actives}
    assert r1.id in ids
    assert r2.id not in ids


def test_update_rule_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(LookupError):
        recurring.update_rule(conn, 999, PatchRecurringRule(active=False))


def test_override_upsert_and_delete(
    conn: sqlite3.Connection, account_id: int, category_id: int
) -> None:
    rule = recurring.create_rule(conn, _new_rule(account_id, category_id))
    override = recurring.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule.id,
            occurrence_date=date(2026, 2, 1),
            state=OverrideState.OVERRIDDEN,
            amount_override=200,
            description_override="february uplift",
        ),
    )
    assert override.state is OverrideState.OVERRIDDEN

    # upsert with same key updates existing row.
    bumped = recurring.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule.id,
            occurrence_date=date(2026, 2, 1),
            state=OverrideState.OVERRIDDEN,
            amount_override=300,
            date_override=date(2026, 2, 5),
        ),
    )
    assert bumped.id == override.id
    assert bumped.amount_override == 300
    assert bumped.date_override == date(2026, 2, 5)

    all_overrides = recurring.list_overrides(conn, rule.id)
    assert len(all_overrides) == 1

    recurring.delete_override(conn, rule.id, date(2026, 2, 1))
    assert recurring.list_overrides(conn, rule.id) == []
    # Deleting again is a no-op.
    recurring.delete_override(conn, rule.id, date(2026, 2, 1))
