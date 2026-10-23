# T-002 — Justfile + CI

> Phase 0 — Repository Bootstrap. Status: pending.

## Purpose

Give the project a single, self-documenting command surface (`just --list`) and a one-matrix-row GitHub Actions pipeline that runs the same commands locally and on push. From here on, every subsequent task runs through `just` recipes — new tasks add recipes, they do not reinvent commands. CI is the forcing function for the Phase 0 exit criteria.

## Inputs / prerequisites

- Upstream tasks:
  - [T-001 — Repository scaffolding](T-001-repository-scaffolding.md) must be merged. `pyproject.toml`, `uv.lock`, and the source tree exist.
- ADRs that constrain the choices:
  - [`ADR-0016` — Task Runner: just](../../adr/0016-task-runner-just.md)
  - [`ADR-0018` — CI: Single Matrix Row (Python 3.12 + Ubuntu)](../../adr/0018-ci-single-matrix-row.md)
  - [`ADR-0004` — Package Manager: uv](../../adr/0004-package-manager-uv.md)
- Required local tools:
  - `just >= 1.34`.
  - `uv >= 0.4`.
  - `gh` CLI (optional, for triggering workflow dispatches locally).

> Note on tasks.md: the T-002 line in `docs/tasks.md` cites ADR-0019 and ADR-0021. Those are soft-delete/audit-log and functional style — unrelated to task-running or CI. The correct references are ADR-0016 (just) and ADR-0018 (CI). Use the ones listed above; `docs/tasks.md` is not modified from this plan.

## Deliverables

- `justfile` at repo root — recipe surface described below.
- `.github/workflows/ci.yml` — single-job workflow running `just ci` with coverage artifact upload.
- No code under `src/` is changed by this task.

## Step-by-step

1. Create `justfile` at repo root. All recipes shell out to `uv run <tool>` so the virtualenv is deterministic and matches CI.

   ```just
   # Budget Planner — developer commands.
   # Discoverable via `just --list`.

   set shell := ["bash", "-cu"]
   set dotenv-load := true

   # --- environment -----------------------------------------------------------

   # Install runtime + dev deps, sync lockfile, install pre-commit hooks.
   install:
       uv sync --group dev
       uv run pre-commit install --install-hooks

   # Install only the pre-commit hooks (no dependency sync).
   install-hooks:
       uv run pre-commit install --install-hooks

   # --- dev loop --------------------------------------------------------------

   # Run FastAPI with hot reload. Binds 127.0.0.1 per ADR-0005.
   dev:
       uv run uvicorn budget_planner.web.app:app \
         --reload --host 127.0.0.1 --port 8000

   # --- quality gates ---------------------------------------------------------

   # Run all linters: ruff, sqlfluff, djlint.
   lint:
       uv run ruff check src tests
       uv run sqlfluff lint migrations
       uv run djlint src/budget_planner/web/templates --check

   # Auto-fix formatting + simple lint issues.
   format:
       uv run ruff format src tests
       uv run ruff check src tests --fix
       uv run sqlfluff fix migrations
       uv run djlint src/budget_planner/web/templates --reformat

   # mypy --strict over the package + tests.
   typecheck:
       uv run mypy src tests

   # Full pytest suite with coverage. 90% gate wired here and in CI.
   test:
       uv run pytest

   # Everything CI runs. Keep deterministic — no network except frankfurter mocks.
   ci: lint typecheck test

   # --- database --------------------------------------------------------------

   # Apply all pending SQL migrations. Implemented in Phase 1 (T-010).
   migrate:
       uv run python -m budget_planner.db.migrate

   # Seed system data (default categories, demo accounts). Implemented in Phase 1 (T-012).
   seed:
       uv run python -m budget_planner.db.seed

   # Nuke and recreate the dev DB from scratch. Destructive.
   db-reset:
       rm -f data/budget.sqlite data/budget.sqlite-wal data/budget.sqlite-shm
       just migrate
       just seed
   ```

   Notes:
   - `set dotenv-load := true` makes `just` autoload `.env` (used from T-004 onward).
   - `migrate` / `seed` reference modules that do not exist yet (`budget_planner.db.migrate`, `budget_planner.db.seed`). That is intentional — they are stubs filled in Phase 1 (T-010, T-012). Phase 0 does not require them to execute successfully; `just --list` must still render.
   - `dev` references `budget_planner.web.app:app`. T-004 provides a trivial app so this recipe becomes runnable at the end of Phase 0.

2. Create `.github/workflows/ci.yml`:

   ```yaml
   name: CI

   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true

   jobs:
     ci:
       name: just ci (Python 3.12, ubuntu-latest)
       runs-on: ubuntu-latest
       timeout-minutes: 15
       steps:
         - name: Checkout
           uses: actions/checkout@v4

         - name: Install uv
           uses: astral-sh/setup-uv@v3
           with:
             version: "latest"
             enable-cache: true
             cache-dependency-glob: "uv.lock"

         - name: Set up Python
           run: uv python install 3.12

         - name: Install just
           uses: extractions/setup-just@v2
           with:
             just-version: "1.34.0"

         - name: Sync dependencies
           run: uv sync --group dev --frozen

         - name: Run full CI pipeline
           run: just ci

         - name: Upload coverage report
           if: always()
           uses: actions/upload-artifact@v4
           with:
             name: coverage-html
             path: htmlcov/
             if-no-files-found: ignore
             retention-days: 7

         - name: Upload coverage xml
           if: always()
           uses: actions/upload-artifact@v4
           with:
             name: coverage-xml
             path: coverage.xml
             if-no-files-found: ignore
             retention-days: 30
   ```

   Rationale:
   - One job, one matrix row. ADR-0018.
   - `uv sync --frozen` enforces the committed lockfile.
   - Coverage artefacts come from `pytest-cov` config landed in T-003.
   - `concurrency` block prevents redundant runs on force-pushes.

3. Verify locally:

   ```sh
   just --list
   # Lists: ci, db-reset, dev, format, install, install-hooks, lint, migrate, seed, test, typecheck.
   ```

   `just lint` / `just typecheck` / `just test` may fail with "no files to check" or similar before T-003 lands configs — that is expected and resolved by T-003.

4. Commit (final step after validation passes):

   ```sh
   git add justfile .github/workflows/ci.yml
   git commit -m "feat(T-002): add just recipe surface and GitHub Actions CI"
   ```

## Interfaces / contracts

Recipe surface frozen for downstream tasks:

- `just install` — bootstrap full dev env.
- `just install-hooks` — install pre-commit hooks only.
- `just dev` — serve FastAPI with reload (requires T-004 app module).
- `just lint` / `just format` / `just typecheck` / `just test` — quality gates.
- `just ci` — meta recipe executed in CI (`lint → typecheck → test`).
- `just migrate` / `just seed` / `just db-reset` — DB lifecycle, filled by Phase 1.

Workflow contract:

- Workflow file path: `.github/workflows/ci.yml`.
- Job id: `ci`. Branch protection on `main` should require this check once the repo is pushed.
- Coverage artefacts: `coverage-html/`, `coverage.xml`.

## Validation / acceptance

Local:

- `just --list` prints all recipes listed above.
- `just install` succeeds end to end (hooks install themselves — the hook config lands in T-003, so this may be a no-op pre-commit install; it must still exit 0).
- `just lint`, `just typecheck`, `just test` can fail cleanly before T-003 — document as expected; what must not happen is a missing-recipe error.

CI:

- A push to a feature branch opens a PR; the `ci` job appears in the Checks tab.
- First green run only possible after T-003 (configs) and T-004 (app module) land. At that point `just ci` must be green on `main`.

Docs updates (CLAUDE.md handoff checklist):

- Prefix the T-002 line in `docs/tasks.md` with `✅`.
- Append a dated line to `docs/CHANGELOG.md` naming the recipe surface + CI workflow.
- No new ADR needed — ADR-0016 and ADR-0018 already cover these decisions. If a change here (e.g. caching strategy) deviates from ADR-0018, raise a new ADR.

## Risks & gotchas

- `set dotenv-load := true` requires that `.env` exist or at least `.env.example` only — if neither is present `just` warns but continues. Keep `.env.example` committed, `.env` ignored.
- `extractions/setup-just@v2` pins the `just` version used in CI. Keep it in sync with the local version via a `.tool-versions` or developer README note; a drift causes "unknown recipe" errors.
- `astral-sh/setup-uv@v3` cache keys on `uv.lock` — if the lockfile is missing (T-001 regression) the cache silently misses and the CI job slows.
- `uv sync --frozen` fails if `uv.lock` is out of date. Agents must `uv lock` after any `pyproject.toml` change and commit the lockfile.
- `djlint` on an empty templates directory can throw a "no files" warning; the `--check` call tolerates it. Verify once a template exists in Phase 3.
- GitHub Actions runs `bash` by default but macOS devs may run `just` under `zsh`. The `set shell := ["bash", "-cu"]` directive avoids drift.
- Avoid adding `pytest` as a pre-commit hook *and* a `just test` dependency; pre-commit should run only a fast subset (T-003 config), while `just test` runs the full suite.

## Handoff notes

- T-003 relies on `just install-hooks` existing and will add `.pre-commit-config.yaml` + `[tool.*]` blocks to `pyproject.toml`. It will also wire the `--cov-fail-under=90` flag into `[tool.pytest.ini_options]` so `just test` enforces coverage.
- T-004 will provide the `budget_planner.web.app` module so `just dev` boots a 200 OK on `/`.
- Phase 1 (T-010) implements `budget_planner.db.migrate` and `budget_planner.db.seed`, making `just migrate` / `just seed` / `just db-reset` effective.
- Phase 4 (T-043) tightens the coverage gate inside the same `[tool.pytest.ini_options]` block — do not duplicate the flag in the recipe.
