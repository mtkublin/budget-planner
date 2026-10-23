from __future__ import annotations

import sqlite3

import pytest

from budget_planner.domain.categories import NewCategory, PatchCategory
from budget_planner.domain.enums import Direction
from budget_planner.repositories import audit, categories


def test_create_and_list(conn: sqlite3.Connection) -> None:
    created = categories.create(conn, NewCategory(name="Food", direction=Direction.EXPENSE))
    assert categories.find_by_id(conn, created.id) == created
    assert categories.find_by_name(conn, "Food") == created
    names = {c.name for c in categories.list_all(conn)}
    assert "Food" in names
    assert "Transit" in names  # Seeded system category.


def test_seeded_system_categories_present(conn: sqlite3.Connection) -> None:
    transit = categories.find_by_name(conn, "Transit")
    assert transit is not None
    assert transit.is_system is True
    assert transit.direction is Direction.TRANSIT


def test_update_rename(conn: sqlite3.Connection) -> None:
    created = categories.create(conn, NewCategory(name="Shopping", direction=Direction.EXPENSE))
    renamed = categories.update(conn, created.id, PatchCategory(name="Shops"))
    assert renamed.name == "Shops"
    assert audit.list_entries(conn, "category", created.id)[-1].operation.value == ("update")


def test_update_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(LookupError):
        categories.update(conn, 999, PatchCategory(name="x"))


def test_soft_delete_and_undelete(conn: sqlite3.Connection) -> None:
    created = categories.create(conn, NewCategory(name="Rent", direction=Direction.EXPENSE))
    categories.soft_delete(conn, created.id)
    assert categories.find_by_id(conn, created.id) is None

    restored = categories.undelete(conn, created.id)
    assert restored.deleted_at is None
    ops = [e.operation.value for e in audit.list_entries(conn, "category", created.id)]
    assert ops == ["create", "delete", "undelete"]


def test_soft_delete_missing_is_noop(conn: sqlite3.Connection) -> None:
    categories.soft_delete(conn, 999)
    assert audit.list_entries(conn, "category", 999) == []


def test_undelete_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(LookupError):
        categories.undelete(conn, 999)


def test_update_noop_patch(conn: sqlite3.Connection) -> None:
    created = categories.create(conn, NewCategory(name="Fuel", direction=Direction.EXPENSE))
    # Patch with no changes still audits as 'update'.
    categories.update(conn, created.id, PatchCategory())
    ops = [e.operation.value for e in audit.list_entries(conn, "category", created.id)]
    assert ops == ["create", "update"]
