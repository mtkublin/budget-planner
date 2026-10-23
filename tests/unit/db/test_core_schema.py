from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.db.migrate import apply_migrations

_EXPECTED_TABLES = {
    "schema_migrations",
    "users",
    "accounts",
    "categories",
    "transactions",
    "planned_transactions",
    "recurring_rules",
    "recurring_rule_overrides",
    "budget_defaults",
    "budget_recurring_overrides",
    "budget_one_off_overrides",
    "account_snapshots",
    "fx_rates",
    "audit_log",
}

_EXPECTED_INDEXES = {
    "ux_accounts_user_name_live",
    "ux_categories_user_name_live",
    "ix_transactions_operation_date",
    "ix_transactions_account",
    "ix_transactions_dest_account",
    "ix_transactions_category",
    "ix_transactions_live",
    "ix_planned_operation_date",
    "ix_planned_rule",
    "ix_recurring_active",
    "ux_budget_defaults_cat_live",
    "ux_budget_recurring_cat_month_live",
    "ux_budget_one_off_cat_year_month_live",
    "ix_snapshots_account_taken_at",
    "ux_fx_rates_date_pair",
    "ix_fx_rates_pair_date",
    "ix_audit_entity",
}


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    url = f"sqlite:///{(tmp_path / 'db.sqlite').as_posix()}"
    settings = Settings(_env_file=None, database_url=url)
    c = get_connection(settings)
    apply_migrations(c)
    try:
        yield c
    finally:
        c.close()


def _insert_user(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO users(id, name) VALUES (1, 'default')")


def _insert_account(conn: sqlite3.Connection, name: str = "ING", currency: str = "PLN") -> int:
    cur = conn.execute("INSERT INTO accounts(name, currency) VALUES (?, ?)", (name, currency))
    return int(cur.lastrowid or 0)


def _insert_category(
    conn: sqlite3.Connection, name: str = "Food", direction: str = "expense"
) -> int:
    cur = conn.execute("INSERT INTO categories(name, direction) VALUES (?, ?)", (name, direction))
    return int(cur.lastrowid or 0)


def test_all_expected_tables_exist(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r["name"] for r in rows}
    missing = _EXPECTED_TABLES - names
    assert not missing, f"missing tables: {missing}"


def test_all_expected_indexes_exist(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = {r["name"] for r in rows}
    missing = _EXPECTED_INDEXES - names
    assert not missing, f"missing indexes: {missing}"


def test_foreign_keys_enforced(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions(operation_date, category_id, account_id, amount) "
            "VALUES ('2026-01-01', 999, 999, 100)"
        )


def test_category_direction_check(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO categories(name, direction) VALUES ('X', 'elephant')")


def test_recurring_cadence_check(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    acc = _insert_account(conn)
    cat = _insert_category(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO recurring_rules("
            "cadence, start_date, category_id, account_id, default_amount) "
            "VALUES ('daily', '2026-01-01', ?, ?, 100)",
            (cat, acc),
        )


def test_transactions_amount_nonzero(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    acc = _insert_account(conn)
    cat = _insert_category(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions(operation_date, category_id, account_id, amount) "
            "VALUES ('2026-01-01', ?, ?, 0)",
            (cat, acc),
        )


def test_transactions_account_differs_from_dest(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    acc = _insert_account(conn)
    cat = _insert_category(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions("
            "operation_date, category_id, account_id, dest_account_id, amount) "
            "VALUES ('2026-01-01', ?, ?, ?, 100)",
            (cat, acc, acc),
        )


def test_accounts_partial_unique_name_live(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    first = _insert_account(conn, name="ING")
    # Duplicate while first is live -> integrity error.
    with pytest.raises(sqlite3.IntegrityError):
        _insert_account(conn, name="ING")
    # Soft-delete first; same-name insert now succeeds.
    conn.execute(
        "UPDATE accounts SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
        (first,),
    )
    _insert_account(conn, name="ING")
    # And another live row with the same name is again rejected.
    with pytest.raises(sqlite3.IntegrityError):
        _insert_account(conn, name="ING")


def test_fx_rates_unique_date_pair(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO fx_rates(date, from_ccy, to_ccy, rate) "
        "VALUES ('2026-01-15', 'EUR', 'PLN', '4.3123')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO fx_rates(date, from_ccy, to_ccy, rate) "
            "VALUES ('2026-01-15', 'EUR', 'PLN', '4.3200')"
        )


def test_audit_log_operation_check(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO audit_log(entity_type, entity_id, operation) "
            "VALUES ('account', 1, 'other')"
        )


def test_currency_length_check(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO accounts(name, currency) VALUES ('X', 'EURO')")


def test_recurring_end_date_after_start(conn: sqlite3.Connection) -> None:
    _insert_user(conn)
    acc = _insert_account(conn)
    cat = _insert_category(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO recurring_rules("
            "cadence, start_date, end_date, category_id, account_id, default_amount) "
            "VALUES ('monthly', '2026-02-01', '2026-01-01', ?, ?, 100)",
            (cat, acc),
        )
