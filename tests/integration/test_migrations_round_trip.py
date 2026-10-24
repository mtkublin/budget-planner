"""Migrations round-trip integration test.

Confirms every migration applies cleanly to an empty DB, the system seed
lands, and the schema migrations ledger refuses to re-apply.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.db.migrate import apply_migrations
from budget_planner.domain.system_categories import (
    RECONCILIATION_CATEGORY_NAME,
    TRANSIT_CATEGORY_NAME,
)

pytestmark = pytest.mark.integration


EXPECTED_TABLES = {
    "accounts",
    "account_snapshots",
    "audit_log",
    "budget_defaults",
    "budget_one_off_overrides",
    "budget_recurring_overrides",
    "categories",
    "fx_rates",
    "planned_transactions",
    "recurring_rule_overrides",
    "recurring_rules",
    "schema_migrations",
    "transactions",
    "users",
}


def _settings_for(tmp_path: Path) -> Settings:
    db = (tmp_path / "db.sqlite").as_posix()
    return Settings(_env_file=None, database_url=f"sqlite:///{db}")


def test_migrate_from_empty_db_creates_all_tables(tmp_path: Path) -> None:
    settings = _settings_for(tmp_path)
    conn = get_connection(settings)
    try:
        apply_migrations(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {r["name"] for r in rows}
        assert EXPECTED_TABLES.issubset(table_names)
    finally:
        conn.close()


def test_migrate_is_idempotent_when_run_twice(tmp_path: Path) -> None:
    settings = _settings_for(tmp_path)
    conn = get_connection(settings)
    try:
        apply_migrations(conn)
        apply_migrations(conn)  # second application: no-op, no exception.
        count = conn.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()["n"]
        assert count >= 3  # at least schema_meta, core_schema, seed
    finally:
        conn.close()


def test_seed_migration_inserts_system_rows(conn: sqlite3.Connection) -> None:
    user_count = conn.execute("SELECT COUNT(*) AS n FROM users WHERE id=1").fetchone()["n"]
    assert user_count == 1

    system_names = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM categories WHERE is_system=1 AND deleted_at IS NULL"
        ).fetchall()
    }
    assert TRANSIT_CATEGORY_NAME in system_names
    assert RECONCILIATION_CATEGORY_NAME in system_names


def test_audit_log_empty_after_seed(conn: sqlite3.Connection) -> None:
    """Seeds bypass audit by design (ADR-0019 — schema facts, not user actions)."""
    n = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
    assert n == 0
