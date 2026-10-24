"""Planned-log UNION flow (ADR-0013).

Verifies ``services.planned.list_planned`` merges persisted planned rows
with virtual recurring occurrences, deduplicates by
``(recurring_rule_id, occurrence_date)``, respects window and promoted
filters, and applies recurring overrides to virtual occurrences.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date

import pytest

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.planned import PlannedFilter
from budget_planner.domain.recurring import NewRecurringOverride
from budget_planner.repositories import planned as planned_repo, recurring as recurring_repo
from budget_planner.services import planned as planned_service

pytestmark = pytest.mark.integration


def test_list_planned_merges_rows_and_virtual_occurrences(
    conn: sqlite3.Connection,
    make_account: Callable[..., int],
    make_category: Callable[..., int],
    make_planned: Callable[..., int],
    make_rule: Callable[..., int],
) -> None:
    account_id = make_account()
    category_id = make_category()
    make_rule(
        account_id=account_id,
        category_id=category_id,
        cadence=Cadence.MONTHLY,
        start_date=date(2026, 1, 15),
        amount=5000,
    )
    make_planned(
        account_id=account_id,
        category_id=category_id,
        amount=1000,
        operation_date=date(2026, 1, 20),
    )

    rows = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 3, 31)),
    )
    dates = [v.operation_date for v in rows]
    # One persisted on 1/20, three virtual on 1/15, 2/15, 3/15.
    assert date(2026, 1, 15) in dates
    assert date(2026, 1, 20) in dates
    assert date(2026, 2, 15) in dates
    assert date(2026, 3, 15) in dates
    assert dates == sorted(dates)


def test_list_planned_respects_filter_window(
    conn: sqlite3.Connection,
    make_account: Callable[..., int],
    make_category: Callable[..., int],
    make_rule: Callable[..., int],
) -> None:
    make_rule(
        account_id=make_account(),
        category_id=make_category(),
        cadence=Cadence.MONTHLY,
        start_date=date(2026, 1, 15),
        amount=5000,
    )
    rows = planned_service.list_planned(
        conn, PlannedFilter(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28))
    )
    assert [v.operation_date for v in rows] == [date(2026, 2, 15)]


def test_list_planned_applies_overrides_to_virtual_occurrences(
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
    recurring_repo.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_id,
            occurrence_date=date(2026, 3, 15),
            state=OverrideState.OVERRIDDEN,
            amount_override=9900,
        ),
    )

    rows = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 3, 31)),
    )
    virtuals = {v.operation_date: v for v in rows if v.persisted_id is None}
    # Feb skipped.
    assert date(2026, 2, 15) not in virtuals
    # Jan default amount, Mar overridden.
    assert virtuals[date(2026, 1, 15)].amount_minor == 5000
    assert virtuals[date(2026, 3, 15)].amount_minor == 9900


def test_list_planned_excludes_promoted_rows(
    conn: sqlite3.Connection,
    make_account: Callable[..., int],
    make_category: Callable[..., int],
    make_planned: Callable[..., int],
    make_transaction: Callable[..., int],
) -> None:
    account_id = make_account()
    category_id = make_category()
    unpromoted_id = make_planned(
        account_id=account_id, category_id=category_id, operation_date=date(2026, 1, 10)
    )
    promoted_id = make_planned(
        account_id=account_id, category_id=category_id, operation_date=date(2026, 1, 20)
    )
    txn_id = make_transaction(
        account_id=account_id,
        category_id=category_id,
        operation_date=date(2026, 1, 20),
        promoted_from_planned_id=promoted_id,
    )
    planned_repo.stamp_promotion(conn, promoted_id, txn_id)

    rows = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date(2026, 1, 1), date_to=date(2026, 1, 31), promoted=False),
    )
    ids = {v.persisted_id for v in rows if v.persisted_id is not None}
    assert unpromoted_id in ids
    assert promoted_id not in ids
