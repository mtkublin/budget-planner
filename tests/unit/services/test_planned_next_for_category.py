"""Tests for `next_planned_for_category` (T-099)."""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Cadence, Direction
from budget_planner.domain.planned import NewPlannedTransaction
from budget_planner.domain.recurring import NewRecurringRule
from budget_planner.domain.transactions import NewTransaction
from budget_planner.repositories import (
    accounts,
    categories,
    planned,
    recurring,
    transactions,
)
from budget_planner.services import planned as pl_svc


@pytest.fixture
def ids(conn: sqlite3.Connection) -> dict[str, int]:
    checking = accounts.create(conn, NewAccount(name="Checking", currency="PLN")).id
    salary = categories.create(conn, NewCategory(name="Salary", direction=Direction.INCOME)).id
    other_income = categories.create(conn, NewCategory(name="Side", direction=Direction.INCOME)).id
    return {
        "checking": checking,
        "salary": salary,
        "other_income": other_income,
    }


def test_returns_none_when_empty(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    assert pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 1)) is None


def test_returns_persisted_hit(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 2, 5),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=500_000,
        ),
    )
    result = pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 20))
    assert result is not None
    assert result.operation_date == date(2026, 2, 5)
    assert result.kind == "persisted"


def test_returns_virtual_hit(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    recurring.create_rule(
        conn,
        NewRecurringRule(
            cadence=Cadence.MONTHLY,
            start_date=date(2026, 1, 25),
            category_id=ids["salary"],
            account_id=ids["checking"],
            default_amount=500_000,
            default_description="payroll",
        ),
    )
    result = pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 20))
    assert result is not None
    assert result.operation_date == date(2026, 1, 25)
    assert result.kind == "virtual"


def test_persisted_wins_over_virtual_on_same_date(
    conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    rule = recurring.create_rule(
        conn,
        NewRecurringRule(
            cadence=Cadence.MONTHLY,
            start_date=date(2026, 1, 25),
            category_id=ids["salary"],
            account_id=ids["checking"],
            default_amount=500_000,
            default_description="payroll",
        ),
    )
    planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 1, 25),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=505_000,
            description="payroll (edited)",
            recurring_rule_id=rule.id,
            occurrence_date=date(2026, 1, 25),
        ),
    )
    result = pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 20))
    assert result is not None
    assert result.kind == "persisted"
    assert result.amount_minor == 505_000


def test_skips_promoted_rows(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    row = planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 2, 5),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=500_000,
        ),
    )
    txn = transactions.create(
        conn,
        NewTransaction(
            operation_date=date(2026, 2, 5),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=500_000,
            description="",
            promoted_from_planned_id=row.id,
        ),
    )
    planned.stamp_promotion(conn, row.id, txn.id)
    assert pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 20)) is None


def test_excludes_soft_deleted_persisted(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    row = planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 2, 5),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=500_000,
        ),
    )
    planned.soft_delete(conn, row.id)
    assert pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 20)) is None


def test_ignores_rows_at_or_before_after(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 1, 20),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=500_000,
        ),
    )
    planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 1, 21),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=500_000,
        ),
    )
    result = pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 20))
    assert result is not None
    assert result.operation_date == date(2026, 1, 21)


def test_horizon_limits_search(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 6, 1),
            category_id=ids["salary"],
            account_id=ids["checking"],
            amount=500_000,
        ),
    )
    assert (
        pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 1), horizon_days=30)
        is None
    )
    result = pl_svc.next_planned_for_category(
        conn, ids["salary"], date(2026, 1, 1), horizon_days=200
    )
    assert result is not None
    assert result.operation_date == date(2026, 6, 1)


def test_returns_none_for_unknown_category_id(
    conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 2, 5),
            category_id=ids["other_income"],
            account_id=ids["checking"],
            amount=500_000,
        ),
    )
    assert pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 20)) is None


def test_rejects_non_positive_horizon(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        pl_svc.next_planned_for_category(conn, ids["salary"], date(2026, 1, 1), horizon_days=0)
