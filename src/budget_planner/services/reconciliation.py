"""Reconciliation service (T-026).

Given a user-supplied real-world account balance, compute
``delta = actual - derived`` and insert a signed ``adjustment`` direction
transaction so ``derive_balance`` now equals ``actual`` (ADR-0011). The
adjustment is the only route by which a signed-amount transaction enters
the system (ADR-0008 exception).
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from budget_planner.domain.enums import Direction
from budget_planner.domain.system_categories import RECONCILIATION_CATEGORY_NAME
from budget_planner.domain.transactions import NewTransaction, Transaction
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    transactions as transactions_repo,
)
from budget_planner.services import balance as balance_svc


class AccountNotFoundError(LookupError):
    """Raised when the account id does not exist."""


class CannotReconcileDeletedAccountError(RuntimeError):
    """Raised when the account is soft-deleted."""


class NoAdjustmentNeededError(RuntimeError):
    """Raised when derived == actual (zero-amount txn would violate schema CHECK)."""


class MissingSystemCategoryError(RuntimeError):
    """Raised when the seeded ``Reconciliation`` category cannot be found."""


def reconcile(
    conn: sqlite3.Connection,
    account_id: int,
    actual_balance_minor: int,
    today: dt.date,
    note: str | None = None,
) -> Transaction:
    """Insert a signed adjustment so ``derive_balance == actual_balance_minor``.

    Preconditions:
      - account exists and is not soft-deleted.
      - delta != 0 (zero raises ``NoAdjustmentNeededError``).
      - the seeded ``Reconciliation`` category is present.

    Post-condition:
      ``services.balance.derive_balance(conn, account_id, today) == actual_balance_minor``
    """
    account = accounts_repo.find_by_id(conn, account_id, include_deleted=True)
    if account is None:
        raise AccountNotFoundError(account_id)
    if account.deleted_at is not None:
        raise CannotReconcileDeletedAccountError(account_id)

    derived = balance_svc.derive_balance(conn, account_id)
    delta = actual_balance_minor - derived
    if delta == 0:
        raise NoAdjustmentNeededError(account_id)

    category = categories_repo.find_by_name(conn, RECONCILIATION_CATEGORY_NAME)
    if category is None:
        raise MissingSystemCategoryError(RECONCILIATION_CATEGORY_NAME)
    assert category.direction is Direction.ADJUSTMENT  # schema invariant

    description = f"auto-reconciliation {today.isoformat()}"
    if note:
        description += f" — {note}"

    return transactions_repo.create(
        conn,
        NewTransaction(
            operation_date=today,
            category_id=category.id,
            account_id=account_id,
            dest_account_id=None,
            amount=delta,
            description=description,
            promoted_from_planned_id=None,
        ),
    )


__all__ = [
    "AccountNotFoundError",
    "CannotReconcileDeletedAccountError",
    "MissingSystemCategoryError",
    "NoAdjustmentNeededError",
    "reconcile",
]
