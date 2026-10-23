from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from budget_planner.config import Settings
from budget_planner.db import seed
from budget_planner.db.connection import get_connection
from budget_planner.db.migrate import apply_migrations
from budget_planner.domain.system_categories import (
    RECONCILIATION_CATEGORY_NAME,
    SYSTEM_CATEGORY_NAMES,
    TRANSIT_CATEGORY_NAME,
)


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


def test_default_user_seeded(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT id, name FROM users WHERE id = 1").fetchone()
    assert row is not None
    assert row["name"] == "default"


def test_transit_category_seeded(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT direction, is_system FROM categories WHERE name = ?",
        (TRANSIT_CATEGORY_NAME,),
    ).fetchone()
    assert row is not None
    assert row["direction"] == "transit"
    assert row["is_system"] == 1


def test_reconciliation_category_seeded(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT direction, is_system FROM categories WHERE name = ?",
        (RECONCILIATION_CATEGORY_NAME,),
    ).fetchone()
    assert row is not None
    assert row["direction"] == "adjustment"
    assert row["is_system"] == 1


def test_system_category_names_frozenset() -> None:
    assert isinstance(SYSTEM_CATEGORY_NAMES, frozenset)
    assert {"Transit", "Reconciliation"} == SYSTEM_CATEGORY_NAMES


def test_seed_is_idempotent(conn: sqlite3.Connection) -> None:
    # Reapply migrations: ON CONFLICT ... DO NOTHING keeps counts stable.
    applied = apply_migrations(conn)
    assert applied == []
    user_count = conn.execute("SELECT count(*) AS n FROM users").fetchone()["n"]
    cat_count = conn.execute("SELECT count(*) AS n FROM categories WHERE is_system = 1").fetchone()[
        "n"
    ]
    assert user_count == 1
    assert cat_count == 2


def test_seed_does_not_write_audit_log(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT count(*) AS n FROM audit_log").fetchone()
    assert row["n"] == 0


def test_only_system_categories_present(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT name FROM categories WHERE is_system = 1").fetchall()
    names = {r["name"] for r in rows}
    assert names == SYSTEM_CATEGORY_NAMES


def test_seed_module_importable() -> None:
    # `just seed` CLI shim: ensure it imports cleanly so the pre-commit hook
    # catches regressions earlier than runtime invocation.
    assert callable(seed.main)
