"""Seed CLI entrypoint.

Seed data is encoded as a migration (``0003_seed_system_rows.sql``), so this
module just applies pending migrations. ``just seed`` is kept as its own
recipe for ergonomics and future use.
"""

from __future__ import annotations

from budget_planner.config import get_settings
from budget_planner.db.connection import get_connection
from budget_planner.db.migrate import apply_migrations


def main() -> None:  # pragma: no cover - CLI shim exercised via `just seed`
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
