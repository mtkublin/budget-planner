"""Recurring rules + sparse overrides repository (ADR-0013 / ADR-0038)."""

from __future__ import annotations

import datetime as dt
import sqlite3
from datetime import date
from typing import Any

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.recurring import (
    NewRecurringOverride,
    NewRecurringRule,
    PatchRecurringRule,
    RecurringOverride,
    RecurringRule,
)
from budget_planner.repositories._shared import mutate, parse_dt, parse_dt_required
from budget_planner.services.recurring import generate_occurrences

_RULE_COLUMNS = (
    "id, user_id, cadence, start_date, end_date, category_id, account_id, "
    "dest_account_id, default_amount, default_description, day_of_month, "
    "month_of_year, active, next_due, last_promoted_date, "
    "created_at, updated_at, deleted_at"
)

_OVERRIDE_COLUMNS = (
    "id, rule_id, occurrence_date, state, amount_override, description_override, "
    "date_override, created_at"
)


def _row_to_rule(row: sqlite3.Row) -> RecurringRule:
    return RecurringRule(
        id=row["id"],
        user_id=row["user_id"],
        cadence=Cadence(row["cadence"]),
        start_date=date.fromisoformat(row["start_date"]),
        end_date=(date.fromisoformat(row["end_date"]) if row["end_date"] is not None else None),
        category_id=row["category_id"],
        account_id=row["account_id"],
        dest_account_id=row["dest_account_id"],
        default_amount=row["default_amount"],
        default_description=row["default_description"],
        day_of_month=row["day_of_month"],
        month_of_year=row["month_of_year"],
        active=bool(row["active"]),
        next_due=date.fromisoformat(row["next_due"]),
        last_promoted_date=(
            date.fromisoformat(row["last_promoted_date"])
            if row["last_promoted_date"] is not None
            else None
        ),
        created_at=parse_dt_required(row["created_at"]),
        updated_at=parse_dt_required(row["updated_at"]),
        deleted_at=parse_dt(row["deleted_at"]),
    )


def _compute_initial_next_due(data: NewRecurringRule, today: date) -> date:
    """Return the earliest canonical occurrence on-or-after ``max(start, today)``.

    Inline port of the generator arithmetic from
    ``services.recurring.generate_occurrences`` — T-118 will refactor to a
    shared pure helper (``first_due_on_or_after``). The duplication is
    deliberate so T-117 lands self-contained without reaching into the
    service module. End-date guard: if the rule's ``end_date`` has already
    passed we still return ``start_date`` as a sentinel; the caller (and
    the migration backfill) is responsible for toggling ``active=False``
    in that terminal case.
    """
    stub = RecurringRule(
        id=0,
        user_id=data.user_id,
        cadence=data.cadence,
        start_date=data.start_date,
        end_date=data.end_date,
        category_id=data.category_id,
        account_id=data.account_id,
        dest_account_id=data.dest_account_id,
        default_amount=data.default_amount,
        default_description=data.default_description,
        day_of_month=data.day_of_month,
        month_of_year=data.month_of_year,
        active=True,
        next_due=data.start_date,  # placeholder; generator doesn't read it
        last_promoted_date=None,
        created_at=dt.datetime.now(dt.UTC),
        updated_at=dt.datetime.now(dt.UTC),
        deleted_at=None,
    )
    range_start = max(data.start_date, today)
    # The first canonical occurrence on-or-after `range_start` is at most
    # one cadence period away. Pick a tight horizon so the generator does
    # not iterate from `start_date` to year-9999 (would hit the 10 000-
    # iteration safety guard on monthly rules whose start is far in the
    # past). 400 days covers monthly / quarterly / yearly in one shot.
    horizon_days = 400
    range_end = range_start + dt.timedelta(days=horizon_days)
    occs = generate_occurrences(stub, range_start, range_end)
    if occs:
        return occs[0].occurrence_date
    # Terminal rule (end_date in the past). Sentinel kept intentionally
    # equal to start_date — the service layer short-circuits inactive
    # rules so this value never surfaces in the UI.
    return data.start_date


def _row_to_override(row: sqlite3.Row) -> RecurringOverride:
    return RecurringOverride(
        id=row["id"],
        rule_id=row["rule_id"],
        occurrence_date=date.fromisoformat(row["occurrence_date"]),
        state=OverrideState(row["state"]),
        amount_override=row["amount_override"],
        description_override=row["description_override"],
        date_override=(
            date.fromisoformat(row["date_override"]) if row["date_override"] is not None else None
        ),
        created_at=parse_dt_required(row["created_at"]),
    )


def find_rule(
    conn: sqlite3.Connection,
    rule_id: int,
    *,
    include_deleted: bool = False,
) -> RecurringRule | None:
    sql = f"SELECT {_RULE_COLUMNS} FROM recurring_rules WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    row = conn.execute(sql, (rule_id,)).fetchone()
    return _row_to_rule(row) if row is not None else None


def list_rules(
    conn: sqlite3.Connection,
    *,
    active_only: bool = False,
    include_deleted: bool = False,
) -> list[RecurringRule]:
    sql = f"SELECT {_RULE_COLUMNS} FROM recurring_rules"
    clauses: list[str] = []
    if active_only:
        clauses.append("active = 1")
    if not include_deleted:
        clauses.append("deleted_at IS NULL")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY start_date ASC, id ASC"
    return [_row_to_rule(r) for r in conn.execute(sql).fetchall()]


def _normalise_rule_patch(changes: dict[str, Any]) -> dict[str, Any]:
    norm: dict[str, Any] = {}
    for key, value in changes.items():
        if key == "cadence":
            norm[key] = value.value
        elif key in {"start_date", "end_date", "next_due"} and value is not None:
            norm[key] = value.isoformat()
        elif key == "active":
            norm[key] = int(bool(value))
        else:
            norm[key] = value
    return norm


def create_rule(conn: sqlite3.Connection, data: NewRecurringRule) -> RecurringRule:
    today = dt.date.today()  # noqa: DTZ011 — date-only anchor; display tz applies at render
    initial_next_due = _compute_initial_next_due(data, today)

    def _action(c: sqlite3.Connection) -> tuple[int, RecurringRule]:
        cursor = c.execute(
            "INSERT INTO recurring_rules("
            "user_id, cadence, start_date, end_date, category_id, account_id, "
            "dest_account_id, default_amount, default_description, "
            "day_of_month, month_of_year, active, next_due) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.user_id,
                data.cadence.value,
                data.start_date.isoformat(),
                data.end_date.isoformat() if data.end_date else None,
                data.category_id,
                data.account_id,
                data.dest_account_id,
                data.default_amount,
                data.default_description,
                data.day_of_month,
                data.month_of_year,
                int(data.active),
                initial_next_due.isoformat(),
            ),
        )
        new_id = int(cursor.lastrowid or 0)
        created = find_rule(c, new_id)
        assert created is not None
        return new_id, created

    return mutate(
        conn,
        entity_type="recurring_rule",
        operation="create",
        prev=None,
        action=_action,
    )


def set_next_due(
    conn: sqlite3.Connection,
    rule_id: int,
    *,
    next_due: date,
    last_promoted_date: date | None,
) -> None:
    """Thin helper for the T-118 promotion service.

    Audit-free: the orchestrating service is responsible for writing a
    paired audit entry via `services.audit.record` after calling this
    helper. Keeping the write audit-free here lets the service compose
    multiple repository calls (txn insert + rule advance + override
    delete) under a single audit row.
    """
    conn.execute(
        "UPDATE recurring_rules SET next_due = ?, last_promoted_date = ?, "
        "updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
        "WHERE id = ?",
        (
            next_due.isoformat(),
            last_promoted_date.isoformat() if last_promoted_date is not None else None,
            rule_id,
        ),
    )


def set_inactive(conn: sqlite3.Connection, rule_id: int) -> None:
    """Thin helper for the T-118 promotion service — mark a rule inactive.

    Audit-free; the service writes the paired audit entry (see
    `set_next_due`). Idempotent: setting an already-inactive rule inactive
    is a no-op.
    """
    conn.execute(
        "UPDATE recurring_rules SET active = 0, "
        "updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
        "WHERE id = ?",
        (rule_id,),
    )


def update_rule(
    conn: sqlite3.Connection,
    rule_id: int,
    data: PatchRecurringRule,
) -> RecurringRule:
    prev = find_rule(conn, rule_id, include_deleted=True)
    if prev is None:
        raise LookupError(f"recurring_rule {rule_id} not found")
    changes = _normalise_rule_patch(data.as_dict())

    def _action(c: sqlite3.Connection) -> tuple[int, RecurringRule]:
        if changes:
            sets = [f"{field} = ?" for field in changes]
            sets.append("updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")
            c.execute(
                f"UPDATE recurring_rules SET {', '.join(sets)} WHERE id = ?",
                (*changes.values(), rule_id),
            )
        updated = find_rule(c, rule_id, include_deleted=True)
        assert updated is not None
        return rule_id, updated

    return mutate(
        conn,
        entity_type="recurring_rule",
        operation="update",
        prev=prev,
        action=_action,
    )


def deactivate_rule(conn: sqlite3.Connection, rule_id: int) -> RecurringRule:
    return update_rule(conn, rule_id, PatchRecurringRule(active=False))


def soft_delete_rule(conn: sqlite3.Connection, rule_id: int) -> None:
    prev = find_rule(conn, rule_id)
    if prev is None:
        return

    def _action(c: sqlite3.Connection) -> tuple[int, None]:
        c.execute(
            "UPDATE recurring_rules SET deleted_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "
            "updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
            "WHERE id = ? AND deleted_at IS NULL",
            (rule_id,),
        )
        return rule_id, None

    mutate(
        conn,
        entity_type="recurring_rule",
        operation="delete",
        prev=prev,
        action=_action,
    )


def list_overrides(conn: sqlite3.Connection, rule_id: int) -> list[RecurringOverride]:
    rows = conn.execute(
        f"SELECT {_OVERRIDE_COLUMNS} FROM recurring_rule_overrides "
        "WHERE rule_id = ? ORDER BY occurrence_date ASC",
        (rule_id,),
    ).fetchall()
    return [_row_to_override(r) for r in rows]


def upsert_override(conn: sqlite3.Connection, data: NewRecurringOverride) -> RecurringOverride:
    existing = conn.execute(
        f"SELECT {_OVERRIDE_COLUMNS} FROM recurring_rule_overrides "
        "WHERE rule_id = ? AND occurrence_date = ?",
        (data.rule_id, data.occurrence_date.isoformat()),
    ).fetchone()
    prev = _row_to_override(existing) if existing is not None else None

    def _action(c: sqlite3.Connection) -> tuple[int, RecurringOverride]:
        if existing is None:
            cursor = c.execute(
                "INSERT INTO recurring_rule_overrides("
                "rule_id, occurrence_date, state, amount_override, "
                "description_override, date_override) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    data.rule_id,
                    data.occurrence_date.isoformat(),
                    data.state.value,
                    data.amount_override,
                    data.description_override,
                    data.date_override.isoformat() if data.date_override else None,
                ),
            )
            new_id = int(cursor.lastrowid or 0)
        else:
            new_id = int(existing["id"])
            c.execute(
                "UPDATE recurring_rule_overrides SET state = ?, amount_override = ?, "
                "description_override = ?, date_override = ? WHERE id = ?",
                (
                    data.state.value,
                    data.amount_override,
                    data.description_override,
                    data.date_override.isoformat() if data.date_override else None,
                    new_id,
                ),
            )
        row = conn.execute(
            f"SELECT {_OVERRIDE_COLUMNS} FROM recurring_rule_overrides WHERE id = ?",
            (new_id,),
        ).fetchone()
        return new_id, _row_to_override(row)

    return mutate(
        conn,
        entity_type="recurring_override",
        operation="update" if prev is not None else "create",
        prev=prev,
        action=_action,
    )


def delete_override(
    conn: sqlite3.Connection,
    rule_id: int,
    occurrence_date: date,
) -> None:
    existing = conn.execute(
        f"SELECT {_OVERRIDE_COLUMNS} FROM recurring_rule_overrides "
        "WHERE rule_id = ? AND occurrence_date = ?",
        (rule_id, occurrence_date.isoformat()),
    ).fetchone()
    if existing is None:
        return
    prev = _row_to_override(existing)

    def _action(c: sqlite3.Connection) -> tuple[int, None]:
        c.execute(
            "DELETE FROM recurring_rule_overrides WHERE id = ?",
            (prev.id,),
        )
        return prev.id, None

    mutate(
        conn,
        entity_type="recurring_override",
        operation="delete",
        prev=prev,
        action=_action,
    )


__all__ = [
    "create_rule",
    "deactivate_rule",
    "delete_override",
    "find_rule",
    "list_overrides",
    "list_rules",
    "set_inactive",
    "set_next_due",
    "soft_delete_rule",
    "update_rule",
    "upsert_override",
]
