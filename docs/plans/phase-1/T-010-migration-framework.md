# T-010 — Migration Framework

> Phase 1 — Data Layer. Status: pending.

## Purpose

Provide a tiny, test-friendly SQL migration runner so every subsequent schema change is a numbered, append-only `.sql` file. No third-party migration dependency. `just migrate` applies every pending file against the configured SQLite database.

## Inputs / prerequisites

- Upstream task: [`../phase-0/T-004-config-module.md`](../phase-0/T-004-config-module.md) — provides `settings.database_url` (SQLite path).
- ADRs:
  - [`../../adr/0003-database-sqlite-only-v1.md`](../../adr/0003-database-sqlite-only-v1.md) — SQLite is the only engine in v1.
  - [`../../adr/0019-soft-delete-and-audit-log.md`](../../adr/0019-soft-delete-and-audit-log.md) — every schema change must preserve the soft-delete + audit discipline.
  - [`../../adr/0021-functional-style-no-oop.md`](../../adr/0021-functional-style-no-oop.md) — runner is a module of pure functions.
- Domain decisions already fixed: amounts as positive integer minor units (ADR-0008); UTC `TIMESTAMP` metadata, `DATE` `operation_date` (ADR-0007); migrations never DROP tables in v1.

## Deliverables

```
src/budget_planner/db/__init__.py
src/budget_planner/db/connection.py          # get_connection(settings) -> sqlite3.Connection
src/budget_planner/db/migrate.py             # discover + apply migrations
migrations/
  0001_schema_meta.sql                       # schema_migrations table only
tests/unit/db/test_migrate.py
tests/unit/db/test_connection.py
```

`justfile` recipe `migrate` wired to `python -m budget_planner.db.migrate`.

## Step-by-step

1. **Add `schema_migrations` meta table in `0001_schema_meta.sql`.**

   ```sql
   -- migrations/0001_schema_meta.sql
   CREATE TABLE IF NOT EXISTS schema_migrations (
       version      INTEGER     PRIMARY KEY,
       filename     TEXT        NOT NULL UNIQUE,
       applied_at   TIMESTAMP   NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
       checksum     TEXT        NOT NULL
   );
   ```

   `checksum` is `sha256(file_bytes)`. A mismatch on re-run aborts with a clear error (prevents silent edits to applied migrations).

2. **`src/budget_planner/db/connection.py`:**

   ```python
   from __future__ import annotations

   import sqlite3
   from pathlib import Path

   from budget_planner.config import Settings


   def get_connection(settings: Settings) -> sqlite3.Connection:
       db_path = Path(settings.database_url.removeprefix("sqlite:///"))
       db_path.parent.mkdir(parents=True, exist_ok=True)
       conn = sqlite3.connect(
           db_path,
           detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
           isolation_level=None,  # we manage transactions explicitly
       )
       conn.row_factory = sqlite3.Row
       conn.execute("PRAGMA foreign_keys = ON;")
       conn.execute("PRAGMA journal_mode = WAL;")
       conn.execute("PRAGMA synchronous = NORMAL;")
       return conn
   ```

   `PRAGMA foreign_keys = ON` is **mandatory** per SQLite docs; must run on every connection.

3. **`src/budget_planner/db/migrate.py`:**

   ```python
   from __future__ import annotations

   import hashlib
   import re
   import sqlite3
   from dataclasses import dataclass
   from pathlib import Path

   MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
   FILENAME_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


   @dataclass(frozen=True)
   class Migration:
       version: int
       filename: str
       sql: str
       checksum: str


   def discover(migrations_dir: Path = MIGRATIONS_DIR) -> list[Migration]:
       files = sorted(p for p in migrations_dir.iterdir() if p.is_file() and p.suffix == ".sql")
       out: list[Migration] = []
       for p in files:
           m = FILENAME_RE.match(p.name)
           if m is None:
               raise ValueError(f"Bad migration filename: {p.name}")
           body = p.read_bytes()
           out.append(
               Migration(
                   version=int(m.group(1)),
                   filename=p.name,
                   sql=body.decode("utf-8"),
                   checksum=hashlib.sha256(body).hexdigest(),
               )
           )
       versions = [m.version for m in out]
       if versions != sorted(set(versions)):
           raise ValueError("Duplicate or non-monotonic migration versions")
       return out


   def applied_versions(conn: sqlite3.Connection) -> dict[int, str]:
       try:
           rows = conn.execute(
               "SELECT version, checksum FROM schema_migrations"
           ).fetchall()
       except sqlite3.OperationalError:
           return {}
       return {int(r["version"]): r["checksum"] for r in rows}


   def apply_migrations(
       conn: sqlite3.Connection,
       migrations_dir: Path = MIGRATIONS_DIR,
   ) -> list[Migration]:
       """Apply all pending migrations. Returns the list applied in this run."""
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
           conn.execute("BEGIN")
           try:
               conn.executescript(mig.sql)
               conn.execute(
                   "INSERT INTO schema_migrations(version, filename, checksum) "
                   "VALUES (?, ?, ?)",
                   (mig.version, mig.filename, mig.checksum),
               )
               conn.execute("COMMIT")
           except Exception:
               conn.execute("ROLLBACK")
               raise
           newly_applied.append(mig)
       return newly_applied


   def main() -> None:
       from budget_planner.config import get_settings

       settings = get_settings()
       from budget_planner.db.connection import get_connection

       with get_connection(settings) as conn:
           applied = apply_migrations(conn)
           for m in applied:
               print(f"applied {m.filename}")


   if __name__ == "__main__":
       main()
   ```

4. **Wire `just migrate`:**

   ```make
   migrate:
       uv run python -m budget_planner.db.migrate
   ```

5. **Tests** (`tests/unit/db/test_migrate.py`):
   - Fresh DB → `apply_migrations` applies 0001 and inserts a row in `schema_migrations`.
   - Second call is a no-op (`len(newly_applied) == 0`).
   - Edit a file's bytes after first apply → second call raises `RuntimeError("Checksum mismatch...")`.
   - Bad filename (`0001-schema.sql`, missing underscore, etc.) raises `ValueError`.
   - Duplicate version numbers raise `ValueError`.
   - Transaction rollback on bad SQL inside a candidate migration (synthetic failure file in a temp dir).

## Interfaces / contracts

Public surface consumed by Phase 1 (T-011, T-012) and tests:

```python
# connection
def get_connection(settings: Settings) -> sqlite3.Connection: ...

# migrate
def discover(migrations_dir: Path = MIGRATIONS_DIR) -> list[Migration]: ...
def applied_versions(conn: sqlite3.Connection) -> dict[int, str]: ...
def apply_migrations(
    conn: sqlite3.Connection,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> list[Migration]: ...
```

Naming convention for migration files: `NNNN_snake_case_slug.sql`, strictly four-digit zero-padded version, lower-snake slug, UTF-8, no `DROP TABLE` in v1.

## Validation / acceptance

- `just db-reset && just migrate` from a clean filesystem creates the SQLite file, applies `0001_schema_meta.sql`, prints `applied 0001_schema_meta.sql`.
- `just migrate` run twice is idempotent (second run prints nothing).
- `just test tests/unit/db/` green.
- `PRAGMA foreign_keys` is `1` after every `get_connection` call (asserted in a test).
- Phase-1 exit criterion satisfied for migration tooling: "`just migrate` applies the schema from zero" (the meta migration here; T-011 adds the actual tables).

## Risks & gotchas

- **SQLite FK pragma is per-connection.** It must be set on every `get_connection` call, not globally. Verified in `test_connection.py`.
- **`executescript` auto-commits any open transaction.** We call `BEGIN` and then `executescript` which internally commits; we therefore commit again around the `INSERT INTO schema_migrations` call to keep the pair atomic in a single logical step and tolerate SQLite's quirk by using `isolation_level=None` and explicit `BEGIN`/`COMMIT`/`ROLLBACK`.
- **Checksum discipline.** Once a migration is applied, its bytes are frozen. All corrections become new numbered migrations.
- **No down-migrations in v1.** `just db-reset` deletes the file and re-applies forwards.
- **Working directory assumption.** `MIGRATIONS_DIR` is resolved relative to the installed package layout; tests inject a temp directory to avoid coupling.

## Handoff notes

- T-011 adds `0002_core_schema.sql` using this runner. Its tests use `apply_migrations(conn, migrations_dir=<temp>)` with both files copied into a tmp path.
- T-012 adds `0003_seed_system_rows.sql`.
- Phase 2 services never call `apply_migrations` directly; test fixtures do.
