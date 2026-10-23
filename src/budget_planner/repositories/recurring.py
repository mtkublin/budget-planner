"""Recurring rules + sparse overrides repository (ADR-0013)."""

from __future__ import annotations

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

_RULE_COLUMNS = (
    "id, user_id, cadence, start_date, end_date, category_id, account_id, "
    "dest_account_id, default_amount, default_description, day_of_month, "
    "month_of_year, active, created_at, updated_at, deleted_at"
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
        created_at=parse_dt_required(row["created_at"]),
        updated_at=parse_dt_required(row["updated_at"]),
        deleted_at=parse_dt(row["deleted_at"]),
    )


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
        elif key in {"start_date", "end_date"} and value is not None:
            norm[key] = value.isoformat()
        elif key == "active":
            norm[key] = int(bool(value))
        else:
            norm[key] = value
    return norm


def create_rule(conn: sqlite3.Connection, data: NewRecurringRule) -> RecurringRule:
    def _action(c: sqlite3.Connection) -> tuple[int, RecurringRule]:
        cursor = c.execute(
            "INSERT INTO recurring_rules("
            "user_id, cadence, start_date, end_date, category_id, account_id, "
            "dest_account_id, default_amount, default_description, "
            "day_of_month, month_of_year, active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
    "soft_delete_rule",
    "update_rule",
    "upsert_override",
]
