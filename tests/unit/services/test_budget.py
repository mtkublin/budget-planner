"""Tests for the budget service (T-024)."""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from budget_planner.domain.accounts import NewAccount
from budget_planner.domain.budgets import (
    NewBudgetDefault,
    NewBudgetOneOffOverride,
    NewBudgetRecurringOverride,
)
from budget_planner.domain.categories import NewCategory
from budget_planner.domain.enums import Direction
from budget_planner.domain.transactions import NewTransaction, TransactionFilter
from budget_planner.repositories import accounts, budgets, categories, transactions
from budget_planner.services import budget as bs


@pytest.fixture
def seed(conn: sqlite3.Connection) -> dict[str, int]:
    checking = accounts.create(
        conn, NewAccount(name="Checking", currency="PLN", opening_balance=0)
    ).id
    groceries = categories.create(
        conn, NewCategory(name="Groceries", direction=Direction.EXPENSE)
    ).id
    rent = categories.create(conn, NewCategory(name="Rent", direction=Direction.EXPENSE)).id
    utilities = categories.create(
        conn, NewCategory(name="Utilities", direction=Direction.EXPENSE)
    ).id
    gym = categories.create(conn, NewCategory(name="Gym", direction=Direction.EXPENSE)).id
    salary = categories.create(conn, NewCategory(name="Salary", direction=Direction.INCOME)).id

    budgets.set_default(conn, NewBudgetDefault(category_id=groceries, amount=120_000))
    budgets.set_default(conn, NewBudgetDefault(category_id=rent, amount=300_000))
    budgets.set_default(conn, NewBudgetDefault(category_id=utilities, amount=40_000))

    budgets.set_recurring(
        conn, NewBudgetRecurringOverride(category_id=rent, month=1, amount=310_000)
    )
    budgets.set_one_off(
        conn, NewBudgetOneOffOverride(category_id=utilities, year=2026, month=2, amount=60_000)
    )

    def _txn(d: date, cat: int, amount: int) -> int:
        return transactions.create(
            conn,
            NewTransaction(operation_date=d, category_id=cat, account_id=checking, amount=amount),
        ).id

    _txn(date(2026, 1, 5), groceries, 30_000)
    _txn(date(2026, 1, 20), groceries, 40_000)
    _txn(date(2026, 1, 25), rent, 310_000)
    _txn(date(2026, 2, 2), utilities, 55_000)
    _txn(date(2026, 2, 10), groceries, 45_000)
    _txn(date(2025, 11, 15), groceries, 35_000)
    # Income + adjustment: must not touch spent/averages.
    _txn(date(2026, 1, 25), salary, 500_000)

    return {
        "checking": checking,
        "groceries": groceries,
        "rent": rent,
        "utilities": utilities,
        "gym": gym,
        "salary": salary,
    }


# ---------------------------------------------------------------------------
# resolve_budget
# ---------------------------------------------------------------------------
def test_default_only(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    assert bs.resolve_budget(conn, seed["groceries"], 2026, 3) == 120_000


def test_recurring_beats_default(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    assert bs.resolve_budget(conn, seed["rent"], 2026, 1) == 310_000


def test_recurring_only_in_its_month(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    assert bs.resolve_budget(conn, seed["rent"], 2026, 7) == 300_000


def test_one_off_beats_both(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    assert bs.resolve_budget(conn, seed["utilities"], 2026, 2) == 60_000


def test_one_off_single_year(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    assert bs.resolve_budget(conn, seed["utilities"], 2027, 2) == 40_000


def test_unbudgeted_returns_none(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    assert bs.resolve_budget(conn, seed["gym"], 2026, 3) is None


def test_zero_default_returns_zero(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    budgets.set_default(conn, NewBudgetDefault(category_id=seed["gym"], amount=0))
    assert bs.resolve_budget(conn, seed["gym"], 2026, 4) == 0


# ---------------------------------------------------------------------------
# month_summary
# ---------------------------------------------------------------------------
def test_january_summary(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    s = bs.month_summary(conn, 2026, 1, today=date(2026, 1, 15))
    assert s.year == 2026
    assert s.month == 1
    by_cat = {line.category_id: line for line in s.lines}
    # Rent: recurring override 310_000; spent 310_000 → remaining 0.
    assert by_cat[seed["rent"]].budgeted_minor == 310_000
    assert by_cat[seed["rent"]].spent_minor == 310_000
    assert by_cat[seed["rent"]].remaining_minor == 0
    # Groceries: default 120_000; spent 70_000; remaining 50_000.
    assert by_cat[seed["groceries"]].budgeted_minor == 120_000
    assert by_cat[seed["groceries"]].spent_minor == 70_000
    assert by_cat[seed["groceries"]].remaining_minor == 50_000
    # Utilities: default 40_000, spent 0 → remaining 40_000.
    assert by_cat[seed["utilities"]].budgeted_minor == 40_000
    assert by_cat[seed["utilities"]].spent_minor == 0
    # Gym: unbudgeted, no spend.
    assert by_cat[seed["gym"]].budgeted_minor is None
    assert by_cat[seed["gym"]].remaining_minor is None


def test_february_delta_vs_prev_month(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    s = bs.month_summary(conn, 2026, 2, today=date(2026, 2, 15))
    by_cat = {line.category_id: line for line in s.lines}
    # Utilities one-off 60_000; spent 55_000; remaining 5_000.
    assert by_cat[seed["utilities"]].budgeted_minor == 60_000
    assert by_cat[seed["utilities"]].spent_minor == 55_000
    assert by_cat[seed["utilities"]].remaining_minor == 5000
    # Groceries delta vs Jan: 45_000 - 70_000 = -25_000.
    assert by_cat[seed["groceries"]].delta_vs_prev_month_minor == -25_000


def test_totals_exclude_unbudgeted(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    s = bs.month_summary(conn, 2026, 1, today=date(2026, 1, 15))
    # Budgeted: Rent 310k + Groceries 120k + Utilities 40k = 470k.
    assert s.totals.budgeted_minor == 470_000
    assert s.totals.spent_minor == 310_000 + 70_000 + 0
    assert s.totals.remaining_minor == 470_000 - (310_000 + 70_000)


def test_previous_month_rollover_january_to_december(
    conn: sqlite3.Connection, seed: dict[str, int]
) -> None:
    s = bs.month_summary(conn, 2026, 1, today=date(2026, 1, 15))
    by_cat = {line.category_id: line for line in s.lines}
    # No Dec 2025 Groceries in fixture → delta = 70_000.
    assert by_cat[seed["groceries"]].delta_vs_prev_month_minor == 70_000


def test_avg_monthly_overall_uses_active_months(
    conn: sqlite3.Connection, seed: dict[str, int]
) -> None:
    s = bs.month_summary(conn, 2026, 2, today=date(2026, 2, 15))
    by_cat = {line.category_id: line for line in s.lines}
    # Groceries active months: Nov 2025, Jan 2026, Feb 2026 → 3 months.
    # Sum = 35_000 + 70_000 + 45_000 = 150_000; avg = 50_000.
    assert by_cat[seed["groceries"]].avg_monthly_overall_minor == 50_000


def test_avg_this_year(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    s = bs.month_summary(conn, 2026, 2, today=date(2026, 2, 15))
    by_cat = {line.category_id: line for line in s.lines}
    # Groceries YTD through Feb: Jan 70_000 + Feb 45_000 = 115_000; / 2 = 57_500.
    assert by_cat[seed["groceries"]].avg_this_year_minor == 57_500


def test_soft_deleted_excluded(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    # Delete a January Groceries txn → spent + averages drop.
    cat_id = seed["groceries"]
    jan_txns = transactions.list_filtered(
        conn,
        TransactionFilter(
            date_from=date(2026, 1, 1), date_to=date(2026, 1, 31), category_ids=(cat_id,)
        ),
    )
    assert jan_txns
    transactions.soft_delete(conn, jan_txns[0].id)
    s = bs.month_summary(conn, 2026, 1, today=date(2026, 1, 15))
    by_cat = {line.category_id: line for line in s.lines}
    assert by_cat[cat_id].spent_minor == 70_000 - jan_txns[0].amount


def test_income_excluded_from_spent(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    s = bs.month_summary(conn, 2026, 1, today=date(2026, 1, 15))
    by_cat = {line.category_id: line for line in s.lines}
    # Salary category is income — should not appear in month_summary lines.
    assert seed["salary"] not in by_cat


def test_adjustment_excluded(conn: sqlite3.Connection, seed: dict[str, int]) -> None:
    adj_cat = categories.find_by_name(conn, "Reconciliation")
    assert adj_cat is not None
    transactions.create(
        conn,
        NewTransaction(
            operation_date=date(2026, 1, 10),
            category_id=adj_cat.id,
            account_id=seed["checking"],
            amount=-5000,
        ),
    )
    s = bs.month_summary(conn, 2026, 1, today=date(2026, 1, 15))
    # Adjustment direction excluded; Groceries spent unchanged at 70_000.
    by_cat = {line.category_id: line for line in s.lines}
    assert by_cat[seed["groceries"]].spent_minor == 70_000


def test_sort_order_budgeted_first_then_alpha(
    conn: sqlite3.Connection, seed: dict[str, int]
) -> None:
    s = bs.month_summary(conn, 2026, 1, today=date(2026, 1, 15))
    # Budgeted lines first, then None-budget lines, each alpha by name.
    kinds = [line.budgeted_minor is None for line in s.lines]
    assert kinds == sorted(kinds)
    # Within budgeted group, names sorted.
    budgeted_names = [line.category_name for line in s.lines if line.budgeted_minor is not None]
    assert budgeted_names == sorted(budgeted_names)


def test_prev_year_month_rollover_december() -> None:
    assert bs.prev_year_month(2026, 1) == (2025, 12)
    assert bs.prev_year_month(2026, 7) == (2026, 6)
