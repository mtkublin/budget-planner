from __future__ import annotations

import sqlite3

import pytest

from budget_planner.domain.accounts import NewAccount, PatchAccount
from budget_planner.repositories import accounts, audit


def test_create_round_trip(conn: sqlite3.Connection) -> None:
    acc = accounts.create(conn, NewAccount(name="ING", currency="PLN"))
    fetched = accounts.find_by_id(conn, acc.id)
    assert fetched == acc
    assert accounts.find_by_name(conn, "ING") == acc
    entries = audit.list_entries(conn, "account", acc.id)
    assert len(entries) == 1
    assert entries[0].operation.value == "create"


def test_update_patch(conn: sqlite3.Connection) -> None:
    acc = accounts.create(conn, NewAccount(name="X", currency="PLN"))
    updated = accounts.update(conn, acc.id, PatchAccount(name="Y", type="bank"))
    assert updated.name == "Y"
    assert updated.type == "bank"
    assert updated.updated_at >= acc.updated_at
    entries = audit.list_entries(conn, "account", acc.id)
    assert [e.operation.value for e in entries] == ["create", "update"]


def test_update_noop_still_audits(conn: sqlite3.Connection) -> None:
    acc = accounts.create(conn, NewAccount(name="N", currency="PLN"))
    accounts.update(conn, acc.id, PatchAccount())
    entries = audit.list_entries(conn, "account", acc.id)
    assert [e.operation.value for e in entries] == ["create", "update"]


def test_update_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(LookupError):
        accounts.update(conn, 999, PatchAccount(name="X"))


def test_soft_delete_round_trip(conn: sqlite3.Connection) -> None:
    acc = accounts.create(conn, NewAccount(name="D", currency="PLN"))
    accounts.soft_delete(conn, acc.id)
    assert accounts.find_by_id(conn, acc.id) is None
    assert accounts.find_by_id(conn, acc.id, include_deleted=True) is not None
    assert accounts.find_by_name(conn, "D") is None
    assert accounts.find_by_name(conn, "D", include_deleted=True) is not None
    assert accounts.list_all(conn) == []
    assert accounts.list_all(conn, include_deleted=True) != []

    restored = accounts.undelete(conn, acc.id)
    assert restored.deleted_at is None
    assert accounts.find_by_id(conn, acc.id) == restored

    entries = audit.list_entries(conn, "account", acc.id)
    assert [e.operation.value for e in entries] == [
        "create",
        "delete",
        "undelete",
    ]


def test_soft_delete_on_missing_is_noop(conn: sqlite3.Connection) -> None:
    accounts.soft_delete(conn, 999)
    # Should not have audited anything.
    assert audit.list_entries(conn, "account", 999) == []


def test_undelete_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(LookupError):
        accounts.undelete(conn, 999)


def test_soft_delete_frees_name(conn: sqlite3.Connection) -> None:
    first = accounts.create(conn, NewAccount(name="ING", currency="PLN"))
    accounts.soft_delete(conn, first.id)
    second = accounts.create(conn, NewAccount(name="ING", currency="PLN"))
    assert second.id != first.id
