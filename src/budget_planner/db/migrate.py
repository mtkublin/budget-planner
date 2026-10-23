"""Hand-rolled numbered SQL migration runner.

Policy:
- Migration files are placed in ``migrations/`` and named ``NNNN_slug.sql``.
- Four-digit, zero-padded, strictly monotonic. No duplicates.
- Append-only: once applied, a migration's bytes are frozen (sha256 checked).
- No ``DROP TABLE`` in v1 (not enforced here; enforced by review).
- All migrations are applied against an existing connection managed by
  :func:`budget_planner.db.connection.get_connection`.

Public surface:
- :class:`Migration`
- :func:`discover`
- :func:`applied_versions`
- :func:`apply_migrations`
- :func:`main` (CLI entrypoint wired to ``just migrate``)
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from budget_planner.config import get_settings
from budget_planner.db.connection import get_connection

MIGRATIONS_DIR: Path = Path(__file__).resolve().parents[3] / "migrations"
_FILENAME_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


@dataclass(frozen=True, slots=True)
class Migration:
    """A single migration file loaded into memory."""

    version: int
    filename: str
    sql: str
    checksum: str


def discover(migrations_dir: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Load all `.sql` migrations from `migrations_dir`, sorted ascending.

    Raises ``ValueError`` if a filename does not match ``NNNN_slug.sql`` or
    if versions are duplicate / non-monotonic.
    """
    files = sorted(p for p in migrations_dir.iterdir() if p.is_file() and p.suffix == ".sql")
    out: list[Migration] = []
    for p in files:
        match = _FILENAME_RE.match(p.name)
        if match is None:
            raise ValueError(f"Bad migration filename: {p.name}")
        body = p.read_bytes()
        out.append(
            Migration(
                version=int(match.group(1)),
                filename=p.name,
                sql=body.decode("utf-8"),
                checksum=hashlib.sha256(body).hexdigest(),
            )
        )
    versions = [m.version for m in out]
    if versions != sorted(set(versions)):
        raise ValueError("Duplicate or non-monotonic migration versions")
    return out


def _split_sql_statements(sql: str) -> list[str]:
    """Split a `.sql` migration file into individual statements.

    Strips `--` line comments, respects single/double-quoted strings, and
    tolerates stray whitespace / blank lines. Does not support `BEGIN`/`END`
    compound statements (triggers) — v1 schema has none.
    """
    out: list[str] = []
    buf: list[str] = []
    i = 0
    length = len(sql)
    in_single = False
    in_double = False
    while i < length:
        char = sql[i]
        # Line comments only when not inside a string literal.
        if not in_single and not in_double and char == "-" and i + 1 < length and sql[i + 1] == "-":
            while i < length and sql[i] != "\n":
                i += 1
            continue
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == ";" and not in_single and not in_double:
            statement = "".join(buf).strip()
            if statement:
                out.append(statement)
            buf = []
            i += 1
            continue
        buf.append(char)
        i += 1
    trailing = "".join(buf).strip()
    if trailing:
        out.append(trailing)
    return out


def applied_versions(conn: sqlite3.Connection) -> dict[int, str]:
    """Return mapping of applied ``version -> checksum`` or ``{}`` on first run."""
    try:
        rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    except sqlite3.OperationalError:
        return {}
    return {int(r["version"]): r["checksum"] for r in rows}


def apply_migrations(
    conn: sqlite3.Connection,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> list[Migration]:
    """Apply all pending migrations. Returns the list applied in this run.

    Behaviour:
    - Already-applied versions are skipped.
    - If an applied version's checksum differs from the file on disk, raises
      ``RuntimeError`` (editing applied migrations is forbidden).
    - Each pending migration runs inside its own ``BEGIN``/``COMMIT`` guard.
    """
    all_migrations = discover(migrations_dir)
    applied = applied_versions(conn)
    newly_applied: list[Migration] = []
    for mig in all_migrations:
        if mig.version in applied:
            if applied[mig.version] != mig.checksum:
                raise RuntimeError(
                    f"Checksum mismatch for migration {mig.filename}: "
                    "already-applied migrations must not be edited."
                )
            continue
        # SQLite DDL is transactional. We avoid ``executescript`` (which
        # auto-commits any open transaction) by splitting the file into
        # individual statements and running each inside a single explicit
        # BEGIN/COMMIT so a failure anywhere rolls the whole thing back,
        # including the ``schema_migrations`` INSERT.
        conn.execute("BEGIN")
        try:
            for statement in _split_sql_statements(mig.sql):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations(version, filename, checksum) VALUES (?, ?, ?)",
                (mig.version, mig.filename, mig.checksum),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        newly_applied.append(mig)
    return newly_applied


def main() -> None:  # pragma: no cover - CLI shim exercised via `just migrate`
    """CLI entrypoint for ``python -m budget_planner.db.migrate``."""
    settings = get_settings()
    conn = get_connection(settings)
    try:
        applied = apply_migrations(conn)
        for migration in applied:
            print(f"applied {migration.filename}")
    finally:
        conn.close()


if __name__ == "__main__":  # pragma: no cover
    main()
