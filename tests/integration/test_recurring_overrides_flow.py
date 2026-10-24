"""Recurring override state-machine flow (ADR-0013).

``skipped`` removes an occurrence; ``overridden`` mutates nullable
fields; deleting an override restores the default occurrence.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date

import pytest

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.planned import PlannedFilter
from budget_planner.domain.recurring import NewRecurringOverride
from budget_planner.repositories import recurring as recurring_repo
from budget_planner.services import planned as planned_service

pytestmark = pytest.mark.integration


def test_skipped_override_removes_occurrence(
    conn: sqlite3.Connection,
    make_account: Callable[..., int],
    make_category: Callable[..., int],
    make_rule: Callable[..., int],
) -> None:
    rule_id = make_rule(
        account_id=make_account(),
        category_id=make_category(),
        cadence=Cadence.MONTHLY,
        start_date=date(2026, 1, 15),
        amount=5000,
    )
    recurring_repo.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_id,
            occurrence_date=date(2026, 2, 15),
            state=OverrideState.SKIPPED,
        ),
    )

    rows = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 3, 31)),
    )
    dates = {v.operation_date for v in rows if v.recurring_rule_id == rule_id}
    assert date(2026, 2, 15) not in dates
    assert date(2026, 1, 15) in dates
    assert date(2026, 3, 15) in dates


def test_overridden_mutates_amount(
    conn: sqlite3.Connection,
    make_account: Callable[..., int],
    make_category: Callable[..., int],
    make_rule: Callable[..., int],
) -> None:
    rule_id = make_rule(
        account_id=make_account(),
        category_id=make_category(),
        cadence=Cadence.MONTHLY,
        start_date=date(2026, 1, 15),
        amount=5000,
    )
    recurring_repo.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_id,
            occurrence_date=date(2026, 2, 15),
            state=OverrideState.OVERRIDDEN,
            amount_override=9900,
        ),
    )
    rows = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28)),
    )
    feb = next(v for v in rows if v.operation_date == date(2026, 2, 15))
    assert feb.amount_minor == 9900
    assert feb.is_overridden is True


def test_override_delete_restores_default_occurrence(
    conn: sqlite3.Connection,
    make_account: Callable[..., int],
    make_category: Callable[..., int],
    make_rule: Callable[..., int],
) -> None:
    rule_id = make_rule(
        account_id=make_account(),
        category_id=make_category(),
        cadence=Cadence.MONTHLY,
        start_date=date(2026, 1, 15),
        amount=5000,
    )
    recurring_repo.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_id,
            occurrence_date=date(2026, 2, 15),
            state=OverrideState.SKIPPED,
        ),
    )
    # Confirm skip is active.
    initial_rows = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28)),
    )
    assert all(v.operation_date != date(2026, 2, 15) for v in initial_rows)

    recurring_repo.delete_override(conn, rule_id, date(2026, 2, 15))

    # After delete the default virtual occurrence returns.
    rows = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28)),
    )
    feb = next(v for v in rows if v.operation_date == date(2026, 2, 15))
    assert feb.amount_minor == 5000
    assert feb.is_overridden is False
