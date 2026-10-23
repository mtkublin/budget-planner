from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from budget_planner.config import Settings
from budget_planner.db.connection import _resolve_db_path, get_connection


def _settings(tmp_path: Path, name: str = "x.sqlite") -> Settings:
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    return Settings(_env_file=None, database_url=url)


def test_resolve_db_path_rejects_non_sqlite() -> None:
    with pytest.raises(ValueError, match="sqlite"):
        _resolve_db_path("postgresql://localhost/x")


def test_get_connection_creates_parent_dir(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "nested" / "deeper", "db.sqlite")
    conn = get_connection(settings)
    try:
        assert (tmp_path / "nested" / "deeper").is_dir()
    finally:
        conn.close()


def test_pragma_foreign_keys_is_on(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    conn = get_connection(settings)
    try:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1
    finally:
        conn.close()


def test_row_factory_is_row(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    conn = get_connection(settings)
    try:
        row = conn.execute("SELECT 1 AS one").fetchone()
        assert isinstance(row, sqlite3.Row)
        assert row["one"] == 1
    finally:
        conn.close()


def test_isolation_level_none(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    conn = get_connection(settings)
    try:
        assert conn.isolation_level is None
    finally:
        conn.close()
