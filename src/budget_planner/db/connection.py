"""SQLite connection factory.

Every connection returned here has:
- `foreign_keys` pragma ON (required for FK enforcement; per-connection).
- `journal_mode = WAL` for safer concurrent reads.
- `synchronous = NORMAL`.
- `row_factory = sqlite3.Row` for column-name access.
- `isolation_level = None` so transactions are managed explicitly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from budget_planner.config import Settings

_SQLITE_PREFIX = "sqlite:///"


def _resolve_db_path(database_url: str) -> Path:
    if not database_url.startswith(_SQLITE_PREFIX):
        raise ValueError(f"Unsupported database_url (expected sqlite:///): {database_url!r}")
    return Path(database_url.removeprefix(_SQLITE_PREFIX))


def get_connection(settings: Settings) -> sqlite3.Connection:
    """Open a SQLite connection honouring project-wide pragmas.

    Creates the parent directory for the database file if missing.
    """
    db_path = _resolve_db_path(settings.database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        db_path,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn
