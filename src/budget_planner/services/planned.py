"""Planned log service (T-023).

Unified view that UNIONs persisted ``planned_transactions`` rows with the
virtual occurrences expanded from active recurring rules (ADR-0013). Also
performs the manual planned → actual promotion flow (ADR-0012) in a single
DB transaction.
"""

from __future__ import annotations

import calendar
import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import Literal

from budget_planner.domain.enums import Direction
from budget_planner.domain.planned import PlannedFilter, PlannedTransaction
from budget_planner.domain.recurring import Occurrence
from budget_planner.domain.transactions import NewTransaction, Transaction
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    planned as planned_repo,
    recurring as recurring_repo,
    transactions as transactions_repo,
)
from budget_planner.repositories._shared import transaction as db_transaction
from budget_planner.services import recurring as recurring_svc

PlannedKind = Literal["persisted", "virtual"]


@dataclass(frozen=True, slots=True)
class PlannedView:
    kind: PlannedKind
    operation_date: dt.date
    account_id: int
    dest_account_id: int | None
    category_id: int
    amount_minor: int
    description: str
    persisted_id: int | None
    recurring_rule_id: int | None
    occurrence_date: dt.date | None
    is_overridden: bool
    is_promoted: bool


@dataclass(frozen=True, slots=True)
class PromotionEdits:
    operation_date: dt.date | None = None
    amount_minor: int | None = None
    description: str | None = None


class PlannedNotFoundError(LookupError):
    """Raised when the planned_id does not exist."""


class AlreadyPromotedError(RuntimeError):
    """Raised when the planned row has already been promoted."""


class CannotPromoteDeletedError(RuntimeError):
    """Raised when attempting to promote a soft-deleted planned row."""


class UnsupportedDirectionError(RuntimeError):
    """Raised for direction=adjustment; use reconciliation service instead."""


class ValidationError(ValueError):
    """Raised for invalid promotion payloads (zero amount, cross-currency transit, …)."""


# ---------------------------------------------------------------------------
# list_planned
# ---------------------------------------------------------------------------
def _default_window(filters: PlannedFilter) -> tuple[dt.date, dt.date]:
    """Fill in a window if filters don't specify one — defaults to the current month."""
    today = dt.date.today()  # noqa: DTZ011 - naive date, routers inject when needed
    first = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    last = today.replace(day=last_day)
    date_from = filters.date_from or first
    date_to = filters.date_to or last
    return date_from, date_to


def _persisted_to_view(row: PlannedTransaction) -> PlannedView:
    return PlannedView(
        kind="persisted",
        operation_date=row.operation_date,
        account_id=row.account_id,
        dest_account_id=row.dest_account_id,
        category_id=row.category_id,
        amount_minor=row.amount,
        description=row.description,
        persisted_id=row.id,
        recurring_rule_id=row.recurring_rule_id,
        occurrence_date=row.occurrence_date,
        is_overridden=False,
        is_promoted=row.promoted_to_txn_id is not None,
    )


def _virtual_to_view(rule_id: int, occ: Occurrence) -> PlannedView:
    return PlannedView(
        kind="virtual",
        operation_date=occ.effective_date,
        account_id=occ.account_id,
        dest_account_id=occ.dest_account_id,
        category_id=occ.category_id,
        amount_minor=occ.amount,
        description=occ.description,
        persisted_id=None,
        recurring_rule_id=rule_id,
        occurrence_date=occ.occurrence_date,
        is_overridden=occ.is_overridden,
        is_promoted=False,
    )


def _match_non_date_filters(view: PlannedView, filters: PlannedFilter) -> bool:
    if filters.account_ids and view.account_id not in filters.account_ids:
        return False
    if filters.category_ids and view.category_id not in filters.category_ids:
        return False
    if (
        filters.recurring_rule_id is not None
        and view.recurring_rule_id != filters.recurring_rule_id
    ):
        return False
    return not (filters.promoted is not None and view.is_promoted != filters.promoted)


def list_planned(
    conn: sqlite3.Connection,
    filters: PlannedFilter,
) -> tuple[PlannedView, ...]:
    """UNION persisted planned rows + virtual recurring occurrences.

    Dedup key for rule-linked rows: ``(recurring_rule_id, occurrence_date)``.
    Virtual rows carry ``persisted_id=None``. Pure w.r.t. DB snapshot.
    """
    date_from, date_to = _default_window(filters)
    persisted_rows = planned_repo.list_filtered(conn, filters)

    dedup_keys: set[tuple[int, dt.date]] = {
        (row.recurring_rule_id, row.occurrence_date)
        for row in persisted_rows
        if row.recurring_rule_id is not None and row.occurrence_date is not None
    }

    views: list[PlannedView] = [_persisted_to_view(row) for row in persisted_rows]

    for rule in recurring_repo.list_rules(conn, active_only=True):
        if rule.start_date > date_to:
            continue
        if rule.end_date is not None and rule.end_date < date_from:
            continue
        overrides = recurring_repo.list_overrides(conn, rule.id)
        for occ in recurring_svc.expand(rule, overrides, date_from, date_to):
            if (rule.id, occ.occurrence_date) in dedup_keys:
                continue
            views.append(_virtual_to_view(rule.id, occ))

    filtered = [v for v in views if _match_non_date_filters(v, filters)]
    filtered.sort(key=lambda v: (v.operation_date, v.kind != "persisted", v.persisted_id or 0))
    return tuple(filtered)


# ---------------------------------------------------------------------------
# promote_to_actual
# ---------------------------------------------------------------------------
def _validate_promotion(
    conn: sqlite3.Connection,
    row: PlannedTransaction,
    direction: Direction,
    amount: int,
) -> None:
    if direction is Direction.ADJUSTMENT:
        raise UnsupportedDirectionError(
            "adjustment promotion is handled by the reconciliation flow"
        )
    if amount == 0:
        raise ValidationError("amount must be non-zero")
    if direction is Direction.TRANSIT:
        if row.dest_account_id is None:  # pragma: no cover - schema CHECK blocks it
            raise ValidationError("transit requires dest_account_id")
        src = accounts_repo.find_by_id(conn, row.account_id)
        dst = accounts_repo.find_by_id(conn, row.dest_account_id)
        if src is None or dst is None:  # pragma: no cover - FK blocks it
            raise ValidationError("transit source or destination account not found")
        if src.currency != dst.currency:
            raise ValidationError(
                f"transit currencies must match (got {src.currency} vs {dst.currency})"
            )


def promote_to_actual(
    conn: sqlite3.Connection,
    planned_id: int,
    edits: PromotionEdits,
) -> Transaction:
    """Insert a transactions row linked to ``planned_id`` and stamp the planned row.

    Both mutations and their audit entries happen in a single DB transaction.
    Raises:
      ``PlannedNotFoundError``, ``AlreadyPromotedError``,
      ``CannotPromoteDeletedError``, ``UnsupportedDirectionError``,
      ``ValidationError``.
    """
    row = planned_repo.find_by_id(conn, planned_id, include_deleted=True)
    if row is None:
        raise PlannedNotFoundError(planned_id)
    if row.deleted_at is not None:
        raise CannotPromoteDeletedError(planned_id)
    if row.promoted_to_txn_id is not None:
        raise AlreadyPromotedError(planned_id)

    category = categories_repo.find_by_id(conn, row.category_id, include_deleted=True)
    if category is None:  # pragma: no cover - FK guarantees existence
        raise ValidationError(f"category {row.category_id} not found")
    operation_date = edits.operation_date or row.operation_date
    amount = edits.amount_minor if edits.amount_minor is not None else row.amount
    description = edits.description if edits.description is not None else row.description
    _validate_promotion(conn, row, category.direction, amount)

    new_txn = NewTransaction(
        operation_date=operation_date,
        category_id=row.category_id,
        account_id=row.account_id,
        dest_account_id=row.dest_account_id,
        amount=amount,
        description=description,
        promoted_from_planned_id=planned_id,
    )

    with db_transaction(conn):
        txn = transactions_repo.create(conn, new_txn)
        planned_repo.stamp_promotion(conn, planned_id, txn.id)
    return txn


# ---------------------------------------------------------------------------
# next_planned_for_category (T-099)
# ---------------------------------------------------------------------------
def next_planned_for_category(
    conn: sqlite3.Connection,
    category_id: int,
    after: dt.date,
    *,
    horizon_days: int = 400,
) -> PlannedView | None:
    """Earliest planned entry (persisted or virtual) for ``category_id`` whose
    ``operation_date`` is strictly after ``after``, within ``horizon_days``.

    Promoted rows are excluded (they already live in ``transactions``).
    Returns ``None`` when the window holds no matching entries.
    """
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")
    filters = PlannedFilter(
        date_from=after + dt.timedelta(days=1),
        date_to=after + dt.timedelta(days=horizon_days),
        category_ids=(category_id,),
        promoted=False,
    )
    result = list_planned(conn, filters)
    return result[0] if result else None


__all__ = [
    "AlreadyPromotedError",
    "CannotPromoteDeletedError",
    "PlannedKind",
    "PlannedNotFoundError",
    "PlannedView",
    "PromotionEdits",
    "UnsupportedDirectionError",
    "ValidationError",
    "list_planned",
    "next_planned_for_category",
    "promote_to_actual",
]
