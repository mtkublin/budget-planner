from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.db.migrate import (
    MIGRATIONS_DIR,
    Migration,
    _split_sql_statements,
    applied_versions,
    apply_migrations,
    discover,
)


def _conn(tmp_path: Path) -> sqlite3.Connection:
    url = f"sqlite:///{(tmp_path / 'db.sqlite').as_posix()}"
    settings = Settings(_env_file=None, database_url=url)
    return get_connection(settings)


def _write_schema_meta_migration(mig_dir: Path) -> Path:
    """Copy the real 0001 meta migration into an isolated dir."""
    source = MIGRATIONS_DIR / "0001_schema_meta.sql"
    target = mig_dir / source.name
    target.write_bytes(source.read_bytes())
    return target


def test_discover_parses_versions(tmp_path: Path) -> None:
    (tmp_path / "0001_schema_meta.sql").write_text("CREATE TABLE a(id INTEGER);")
    (tmp_path / "0002_add_b.sql").write_text("CREATE TABLE b(id INTEGER);")
    out = discover(tmp_path)
    assert [m.version for m in out] == [1, 2]
    assert all(isinstance(m, Migration) for m in out)
    assert all(len(m.checksum) == 64 for m in out)


def test_discover_rejects_bad_filename(tmp_path: Path) -> None:
    (tmp_path / "0001-schema.sql").write_text("--")
    with pytest.raises(ValueError, match="Bad migration filename"):
        discover(tmp_path)


def test_discover_rejects_duplicate_version(tmp_path: Path) -> None:
    (tmp_path / "0001_a.sql").write_text("--")
    (tmp_path / "0001_b.sql").write_text("--")
    with pytest.raises(ValueError, match="Duplicate or non-monotonic"):
        discover(tmp_path)


def test_apply_migrations_fresh_db(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    mig_dir = tmp_path / "m"
    mig_dir.mkdir()
    _write_schema_meta_migration(mig_dir)
    try:
        applied = apply_migrations(conn, mig_dir)
        assert [m.version for m in applied] == [1]
        rows = conn.execute("SELECT version, filename FROM schema_migrations").fetchall()
        assert len(rows) == 1
        assert rows[0]["filename"] == "0001_schema_meta.sql"
    finally:
        conn.close()


def test_apply_migrations_is_idempotent(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    mig_dir = tmp_path / "m"
    mig_dir.mkdir()
    _write_schema_meta_migration(mig_dir)
    try:
        apply_migrations(conn, mig_dir)
        second = apply_migrations(conn, mig_dir)
        assert second == []
    finally:
        conn.close()


def test_apply_migrations_detects_checksum_mismatch(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    mig_dir = tmp_path / "m"
    mig_dir.mkdir()
    file = _write_schema_meta_migration(mig_dir)
    try:
        apply_migrations(conn, mig_dir)
        # Append a byte: checksum changes but version stays.
        file.write_bytes(file.read_bytes() + b"\n-- edited\n")
        with pytest.raises(RuntimeError, match="Checksum mismatch"):
            apply_migrations(conn, mig_dir)
    finally:
        conn.close()


def test_apply_migrations_rolls_back_on_bad_sql(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    mig_dir = tmp_path / "m"
    mig_dir.mkdir()
    _write_schema_meta_migration(mig_dir)
    try:
        apply_migrations(conn, mig_dir)  # meta applied first
        # Only now drop in a bad migration to exercise rollback-on-failure
        # while a prior migration remains cleanly recorded.
        (mig_dir / "0002_bad.sql").write_bytes(b"CREATE TABLE t_valid(id INTEGER);\nNOT_SQL;\n")
        with pytest.raises(sqlite3.OperationalError):
            apply_migrations(conn, mig_dir)
        # 0002 must not have been recorded + its first statement must have rolled back.
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        assert [r["version"] for r in rows] == [1]
        in_sqlite = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t_valid'"
        ).fetchall()
        assert in_sqlite == []
    finally:
        conn.close()


def test_split_sql_statements_handles_comments_and_strings() -> None:
    sql = """
    -- leading comment
    CREATE TABLE t (
        name TEXT NOT NULL DEFAULT 'with; semicolon',
        label TEXT NOT NULL DEFAULT "double; quoted"
    );
    ;;  -- empty statements get skipped
    INSERT INTO t(name, label) VALUES ('a''b', 'x')
    """
    stmts = _split_sql_statements(sql)
    assert len(stmts) == 2
    assert stmts[0].startswith("CREATE TABLE t")
    assert stmts[1].startswith("INSERT INTO t")


def test_applied_versions_empty_before_meta(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    try:
        assert applied_versions(conn) == {}
    finally:
        conn.close()
