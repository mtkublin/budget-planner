# T-001 — Repository Scaffolding

> Phase 0 — Repository Bootstrap. Status: pending.

## Purpose

Lay down the Python project foundation: `uv`-managed `pyproject.toml`, pinned Python 3.12, declared runtime and dev dependencies, and the source + test directory skeleton that every later task writes into. This task delivers nothing executable yet — no FastAPI app, no CI — but it is the shared ground that T-002/T-003/T-004 all build on. If this task is wrong, every subsequent `just` recipe and pre-commit hook misfires.

## Inputs / prerequisites

- Upstream tasks: none (first task in the phase).
- ADRs that constrain the choices:
  - [`ADR-0002` — Web Stack: FastAPI + HTMX + Jinja2 + Tailwind (CDN) + Plotly](../../adr/0002-web-stack-fastapi-htmx-jinja.md)
  - [`ADR-0003` — SQLite only in v1](../../adr/0003-database-sqlite-only-v1.md)
  - [`ADR-0004` — Package Manager: uv](../../adr/0004-package-manager-uv.md)
  - [`ADR-0021` — Functional style, no gratuitous OOP](../../adr/0021-functional-style-no-oop.md)
- Required local tools:
  - `uv >= 0.4` (manages Python + lockfile).
  - `git` (repo is already initialised).
  - Python `3.12.x` resolvable by `uv` (`uv python install 3.12` if missing).

## Deliverables

Config / lockfile:

- `pyproject.toml` — single source of truth for metadata, dependencies, tool configs (tool-specific blocks landed in T-003).
- `uv.lock` — committed lockfile produced by `uv lock`.
- `.python-version` — contains the literal string `3.12`.

Repo hygiene:

- `.gitignore` — ignores `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`, `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm`, `.env`, `data/` (dev DB directory), `dist/`, `build/`.
- `.env.example` — created empty here (fields added in T-004).

Source skeleton (each directory holds an `__init__.py`, except `migrations/`, `tests/*`, and `static/`):

```
src/budget_planner/__init__.py
src/budget_planner/config.py            # placeholder, implemented in T-004
src/budget_planner/db/__init__.py
src/budget_planner/domain/__init__.py
src/budget_planner/services/__init__.py
src/budget_planner/repositories/__init__.py
src/budget_planner/web/__init__.py
src/budget_planner/web/routers/__init__.py
src/budget_planner/web/templates/.gitkeep
src/budget_planner/web/static/.gitkeep
src/budget_planner/adapters/__init__.py
src/budget_planner/adapters/fx/__init__.py
src/budget_planner/adapters/export/__init__.py
tests/__init__.py
tests/unit/__init__.py
tests/integration/__init__.py
tests/e2e/__init__.py
migrations/.gitkeep
```

Role, one line each:

- `src/budget_planner/config.py` — process-wide settings (T-004 fills it).
- `src/budget_planner/db/` — SQLite connection + migration runner (Phase 1).
- `src/budget_planner/domain/` — frozen dataclasses + enums (Phase 1).
- `src/budget_planner/services/` — pure business-logic modules (Phase 2).
- `src/budget_planner/repositories/` — CRUD + audit helpers (Phase 1).
- `src/budget_planner/web/routers/` — thin FastAPI routers (Phase 3).
- `src/budget_planner/web/templates/` — Jinja2 templates.
- `src/budget_planner/web/static/` — static assets.
- `src/budget_planner/adapters/fx/` — frankfurter HTTP client.
- `src/budget_planner/adapters/export/` — CSV/Parquet writers.
- `tests/unit|integration|e2e/` — pytest trees.
- `migrations/` — numbered `.sql` files landing in Phase 1.

## Step-by-step

1. From repo root pin Python:

   ```sh
   echo 3.12 > .python-version
   uv python install 3.12
   ```

2. Scaffold `pyproject.toml`. Create the file verbatim:

   ```toml
   [project]
   name = "budget-planner"
   version = "0.1.0"
   description = "Local-first personal budget planning and fortune tracking web app."
   requires-python = ">=3.12,<3.13"
   readme = "README.md"
   authors = [{ name = "Mikolaj Kublin" }]

   dependencies = [
     "fastapi>=0.115",
     "uvicorn[standard]>=0.32",
     "jinja2>=3.1",
     "pydantic>=2.9",
     "pydantic-settings>=2.6",
     "python-multipart>=0.0.12",
     "plotly>=5.24",
     "pandas>=2.2",
     "pyarrow>=17",
     "httpx>=0.27",
     "python-dateutil>=2.9",
   ]

   [dependency-groups]
   dev = [
     "ruff>=0.6",
     "mypy>=1.11",
     "pytest>=8.3",
     "pytest-cov>=5.0",
     "pytest-asyncio>=0.24",
     "pytest-xdist>=3.6",
     "beautifulsoup4>=4.12",
     "playwright>=1.47",
     "sqlfluff>=3.1",
     "djlint>=1.35",
     "bandit>=1.7",
     "detect-secrets>=1.5",
     "pre-commit>=3.8",
     "types-python-dateutil>=2.9",
     "pandas-stubs>=2.2",
   ]

   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [tool.hatch.build.targets.wheel]
   packages = ["src/budget_planner"]

   [tool.uv]
   package = true
   ```

   Rationale on choices (keep in this plan, not in `pyproject.toml`):

   - `requires-python = ">=3.12,<3.13"` locks the matrix to a single row ([ADR-0018](../../adr/0018-ci-single-matrix-row.md)).
   - `hatchling` backend is `uv`-native and standard; no reason to pick anything exotic.
   - `[dependency-groups]` is the modern `uv` way to express dev dependencies (PEP 735).

3. Create directory skeleton. All `__init__.py` files are empty.

   ```sh
   mkdir -p \
     src/budget_planner/{db,domain,services,repositories,adapters/{fx,export},web/{routers,templates,static}} \
     tests/{unit,integration,e2e} \
     migrations

   touch \
     src/budget_planner/__init__.py \
     src/budget_planner/config.py \
     src/budget_planner/db/__init__.py \
     src/budget_planner/domain/__init__.py \
     src/budget_planner/services/__init__.py \
     src/budget_planner/repositories/__init__.py \
     src/budget_planner/web/__init__.py \
     src/budget_planner/web/routers/__init__.py \
     src/budget_planner/web/templates/.gitkeep \
     src/budget_planner/web/static/.gitkeep \
     src/budget_planner/adapters/__init__.py \
     src/budget_planner/adapters/fx/__init__.py \
     src/budget_planner/adapters/export/__init__.py \
     tests/__init__.py \
     tests/unit/__init__.py \
     tests/integration/__init__.py \
     tests/e2e/__init__.py \
     migrations/.gitkeep
   ```

4. Write `.gitignore`:

   ```gitignore
   # Python
   __pycache__/
   *.py[cod]
   *.egg-info/
   dist/
   build/

   # Env + venv
   .env
   .venv/

   # Tooling caches
   .pytest_cache/
   .mypy_cache/
   .ruff_cache/
   .coverage
   htmlcov/

   # SQLite dev DBs
   *.sqlite
   *.sqlite-wal
   *.sqlite-shm
   data/
   ```

   Note: `CLAUDE.md` references that SQLite ignore globs were already broadened in commit `aed205b`; verify the final `.gitignore` matches that commit's intent before overwriting. If a `.gitignore` already exists, extend rather than replace.

5. Create empty `.env.example` (fields added in T-004):

   ```sh
   : > .env.example
   ```

6. Resolve and lock dependencies:

   ```sh
   uv sync
   uv lock --check    # fails if the lockfile is out of sync with pyproject
   ```

7. Smoke-check: `uv run python -c "import budget_planner; print('ok')"` prints `ok`.

8. Stage and commit per CLAUDE.md handoff checklist (do not run yet — committing is the agent's final action after validation):

   ```sh
   git add .python-version pyproject.toml uv.lock .gitignore .env.example src tests migrations
   ```

   Commit message (conventional-commits):

   ```
   feat(T-001): scaffold uv project and directory skeleton
   ```

## Interfaces / contracts

Downstream tasks depend on these literals — do not rename.

- Project source root: `src/budget_planner/`.
- Importable package name: `budget_planner`.
- Config module path: `src/budget_planner/config.py` (filled in T-004).
- Test roots: `tests/unit`, `tests/integration`, `tests/e2e`.
- Migrations root: `migrations/`.
- Python version pin: `.python-version` = `3.12`.
- Dev dependencies live in `[dependency-groups].dev` (PEP 735), not `[project.optional-dependencies]`.
- Build backend: `hatchling`.
- Wheel package list: `["src/budget_planner"]` (used by `hatchling` to find the package).

## Validation / acceptance

Commands that must pass (from repo root):

- `uv sync` — succeeds with no network errors.
- `uv lock --check` — exit code 0.
- `uv run python -c "import budget_planner"` — exit code 0.
- `uv run python -c "import importlib; [importlib.import_module(m) for m in ('budget_planner', 'budget_planner.db', 'budget_planner.domain', 'budget_planner.services', 'budget_planner.repositories', 'budget_planner.web', 'budget_planner.web.routers', 'budget_planner.adapters', 'budget_planner.adapters.fx', 'budget_planner.adapters.export')]"` — exit code 0.
- `tree -L 3 src tests migrations` matches the deliverable layout.

Docs updates required to mark done (per `CLAUDE.md` handoff checklist):

- Prefix the T-001 line in `docs/tasks.md` with `✅`.
- Append a dated line to `docs/CHANGELOG.md` (create the file if missing) referencing T-001.
- No new ADR needed — ADR-0002/0003/0004 already cover these decisions.

## Risks & gotchas

- `uv lock` can churn transitively — pin only `>=` majors in `pyproject.toml`, let `uv.lock` carry exact versions.
- Avoid `[project.optional-dependencies]` for dev deps. Use PEP 735 `[dependency-groups]`; this matches `uv sync` default group behaviour.
- `pyarrow` wheels are chunky (~70 MB). CI runners handle it, but local first-run install feels slow — do not retry.
- If the repo already has a `.gitignore` from earlier commits (`CLAUDE.md` mentions SQLite patterns were broadened), merge rather than overwrite.
- Do **not** run `uv init`; it rewrites `pyproject.toml` to its own template.
- `uv sync` writes `.venv/`; ensure it is in `.gitignore` before the first commit.

## Handoff notes

- T-002 will add the `justfile` and GitHub Actions workflow and rely on `uv run <cmd>` + `uv sync --group dev` for every recipe/step.
- T-003 will fill `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, `[tool.coverage.*]`, `[tool.sqlfluff]`, `[tool.djlint]`, `[tool.bandit]` blocks in the same `pyproject.toml`.
- T-004 will replace the empty `config.py` with a `pydantic-settings` module and populate `.env.example`.
- Phase 1 (T-010) will populate `migrations/` with numbered `.sql` files.
