"""Tests for the planned log service (T-023)."""

from __future__ import annotations

import sqlite3
from datetime import date
from unittest.mock import patch

import pytest

from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Cadence, Direction, OverrideState
from budget_planner.domain.planned import NewPlannedTransaction, PlannedFilter
from budget_planner.domain.recurring import NewRecurringOverride, NewRecurringRule
from budget_planner.domain.transactions import TransactionFilter
from budget_planner.repositories import accounts, categories, planned, recurring, transactions
from budget_planner.services import planned as pl_svc
from budget_planner.services.planned import (
    AlreadyPromotedError,
    CannotPromoteDeletedError,
    PlannedNotFoundError,
    PromotionEdits,
    UnsupportedDirectionError,
    ValidationError,
)


@pytest.fixture
def world(conn: sqlite3.Connection) -> dict[str, int]:
    checking = accounts.create(conn, NewAccount(name="Checking", currency="PLN")).id
    savings = accounts.create(conn, NewAccount(name="Savings", currency="PLN")).id
    eur = accounts.create(conn, NewAccount(name="EUR", currency="EUR")).id
    groceries = categories.create(
        conn, NewCategory(name="Groceries", direction=Direction.EXPENSE)
    ).id
    rent = categories.create(conn, NewCategory(name="Rent", direction=Direction.EXPENSE)).id
    salary = categories.create(conn, NewCategory(name="Salary", direction=Direction.INCOME)).id
    transit = categories.find_by_name(conn, "Transit")
    reconciliation = categories.find_by_name(conn, "Reconciliation")
    assert transit is not None and reconciliation is not None
    rule_rent = recurring.create_rule(
        conn,
        NewRecurringRule(
            cadence=Cadence.MONTHLY,
            start_date=date(2026, 1, 5),
            category_id=rent,
            account_id=checking,
            default_amount=200_000,
            default_description="rent",
        ),
    )
    # Override: skip March, override April to 210_000.
    recurring.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_rent.id,
            occurrence_date=date(2026, 3, 5),
            state=OverrideState.SKIPPED,
        ),
    )
    recurring.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_rent.id,
            occurrence_date=date(2026, 4, 5),
            state=OverrideState.OVERRIDDEN,
            amount_override=210_000,
        ),
    )
    p1 = planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 2, 20),
            category_id=groceries,
            account_id=checking,
            amount=12_345,
            description="valentine groceries",
        ),
    ).id
    # Persisted materialisation of the Jan 5 recurring occurrence (dedup target).
    p2 = planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 1, 5),
            category_id=rent,
            account_id=checking,
            amount=200_000,
            description="rent (edited)",
            recurring_rule_id=rule_rent.id,
            occurrence_date=date(2026, 1, 5),
        ),
    ).id
    return {
        "checking": checking,
        "savings": savings,
        "eur": eur,
        "groceries": groceries,
        "rent": rent,
        "salary": salary,
        "transit": transit.id,
        "reconciliation": reconciliation.id,
        "rule_rent": rule_rent.id,
        "p1": p1,
        "p2": p2,
    }


# ---------------------------------------------------------------------------
# list_planned
# ---------------------------------------------------------------------------
def test_list_planned_dedup_prefers_persisted(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 6, 30)),
    )
    jan_5 = [r for r in rows if r.operation_date == date(2026, 1, 5)]
    assert len(jan_5) == 1  # dedup kept persisted
    assert jan_5[0].kind == "persisted"


def test_list_planned_skipped_occurrence_removed(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 3, 1), date_to=date(2026, 3, 31)),
    )
    assert all(r.operation_date != date(2026, 3, 5) for r in rows)


def test_list_planned_overridden_amount(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 4, 1), date_to=date(2026, 4, 30)),
    )
    apr = [r for r in rows if r.operation_date == date(2026, 4, 5)]
    assert len(apr) == 1
    assert apr[0].amount_minor == 210_000
    assert apr[0].is_overridden


def test_list_planned_category_filter(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 6, 30),
            category_ids=(world["groceries"],),
        ),
    )
    assert len(rows) == 1
    assert rows[0].persisted_id == world["p1"]


def test_list_planned_deactivated_rule_hides_virtuals(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    recurring.deactivate_rule(conn, world["rule_rent"])
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28)),
    )
    assert all(r.recurring_rule_id is None for r in rows)


def test_list_planned_account_filter(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 6, 30),
            account_ids=(world["savings"],),
        ),
    )
    assert rows == ()


def test_list_planned_recurring_rule_id_filter_excludes(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 3, 31),
            recurring_rule_id=world["rule_rent"],
        ),
    )
    # Non-recurring p1 (groceries) is excluded by the filter.
    assert all(r.recurring_rule_id == world["rule_rent"] for r in rows)


def test_list_planned_promoted_filter_excludes(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    # Promote p1 → persisted row flips to is_promoted=True.
    pl_svc.promote_to_actual(conn, world["p1"], PromotionEdits())
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 6, 30), promoted=False),
    )
    assert all(not r.is_promoted for r in rows)


def test_list_planned_rule_end_date_before_window(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    # Deactivate / shrink the rule's lifetime via a new rule with early end_date.
    cat_rent = world["rent"]
    old_rule = recurring.create_rule(
        conn,
        NewRecurringRule(
            cadence=Cadence.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            category_id=cat_rent,
            account_id=world["checking"],
            default_amount=100,
            default_description="old",
        ),
    )
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 6, 30)),
    )
    assert all(r.recurring_rule_id != old_rule.id for r in rows)


def test_list_planned_rule_start_after_window(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    future_rule = recurring.create_rule(
        conn,
        NewRecurringRule(
            cadence=Cadence.MONTHLY,
            start_date=date(2028, 1, 1),
            category_id=world["rent"],
            account_id=world["checking"],
            default_amount=100,
            default_description="future",
        ),
    )
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 6, 30)),
    )
    assert all(r.recurring_rule_id != future_rule.id for r in rows)


def test_list_planned_sort_order(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 6, 30)),
    )
    dates = [r.operation_date for r in rows]
    assert dates == sorted(dates)


def test_list_planned_virtual_rows_for_months_without_persisted(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    rows = pl_svc.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28)),
    )
    feb = [r for r in rows if r.recurring_rule_id == world["rule_rent"]]
    assert len(feb) == 1
    assert feb[0].kind == "virtual"


# ---------------------------------------------------------------------------
# promote_to_actual
# ---------------------------------------------------------------------------
def test_promote_happy_path(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    txn = pl_svc.promote_to_actual(conn, world["p1"], PromotionEdits())
    assert txn.promoted_from_planned_id == world["p1"]
    assert txn.amount == 12_345
    assert txn.operation_date == date(2026, 2, 20)
    # Planned row is linked.
    pt = planned.find_by_id(conn, world["p1"])
    assert pt is not None
    assert pt.promoted_to_txn_id == txn.id


def test_promote_with_edits(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    txn = pl_svc.promote_to_actual(
        conn,
        world["p1"],
        PromotionEdits(
            operation_date=date(2026, 2, 22),
            amount_minor=11_000,
            description="valentine (edited)",
        ),
    )
    assert txn.operation_date == date(2026, 2, 22)
    assert txn.amount == 11_000
    assert txn.description == "valentine (edited)"


def test_promote_already_blocked(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    pl_svc.promote_to_actual(conn, world["p1"], PromotionEdits())
    with pytest.raises(AlreadyPromotedError):
        pl_svc.promote_to_actual(conn, world["p1"], PromotionEdits())


def test_promote_deleted_raises(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    planned.soft_delete(conn, world["p1"])
    with pytest.raises(CannotPromoteDeletedError):
        pl_svc.promote_to_actual(conn, world["p1"], PromotionEdits())


def test_promote_adjustment_unsupported(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    adj_p = planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 3, 1),
            category_id=world["reconciliation"],
            account_id=world["checking"],
            amount=100,
        ),
    ).id
    with pytest.raises(UnsupportedDirectionError):
        pl_svc.promote_to_actual(conn, adj_p, PromotionEdits())


def test_promote_transit_cross_currency_rejected(
    conn: sqlite3.Connection, world: dict[str, int]
) -> None:
    trans_p = planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 3, 1),
            category_id=world["transit"],
            account_id=world["checking"],
            dest_account_id=world["eur"],
            amount=1000,
        ),
    ).id
    with pytest.raises(ValidationError):
        pl_svc.promote_to_actual(conn, trans_p, PromotionEdits())


def test_promote_transit_same_currency(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    trans_p = planned.create(
        conn,
        NewPlannedTransaction(
            operation_date=date(2026, 3, 1),
            category_id=world["transit"],
            account_id=world["checking"],
            dest_account_id=world["savings"],
            amount=1000,
        ),
    ).id
    txn = pl_svc.promote_to_actual(conn, trans_p, PromotionEdits())
    assert txn.dest_account_id == world["savings"]


def test_promote_unknown_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(PlannedNotFoundError):
        pl_svc.promote_to_actual(conn, 9999, PromotionEdits())


def test_promote_amount_zero_rejected(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        pl_svc.promote_to_actual(conn, world["p1"], PromotionEdits(amount_minor=0))


def test_rollback_on_stamp_failure(conn: sqlite3.Connection, world: dict[str, int]) -> None:
    empty = TransactionFilter()
    before = len(transactions.list_filtered(conn, filters=empty))
    with (
        patch(
            "budget_planner.services.planned.planned_repo.stamp_promotion",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(RuntimeError),
    ):
        pl_svc.promote_to_actual(conn, world["p1"], PromotionEdits())
    after = len(transactions.list_filtered(conn, filters=empty))
    assert before == after
    pt = planned.find_by_id(conn, world["p1"])
    assert pt is not None
    assert pt.promoted_to_txn_id is None
