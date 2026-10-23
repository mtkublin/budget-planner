# Phase 0 — Repository Bootstrap · Plan Index

> Goal of the phase: a developer can `git clone`, `just install`, `just migrate` (stub), `just seed` (stub), `just dev` and land on an empty FastAPI page. CI runs `just ci` on push. Pre-commit active.

Phase gate (from `docs/implementation_plan.md`):

- CI runs `just ci` on push and passes with the empty project.
- Pre-commit active on every commit.
- `just --list` self-documents all recipes.

Tasks (strictly sequential — all `[S]`):

| # | File | Purpose |
|---|------|---------|
| T-001 | [T-001-repository-scaffolding.md](T-001-repository-scaffolding.md) | `pyproject.toml` via `uv`, dependency pins, source tree + test tree skeleton, `.python-version`, baseline `.gitignore` / `.env.example` placeholders. |
| T-002 | [T-002-justfile-and-ci.md](T-002-justfile-and-ci.md) | `justfile` recipes (`dev`, `test`, `lint`, `format`, `typecheck`, `ci`, `db-reset`, `seed`, `migrate`, `install`, `install-hooks`) and GitHub Actions workflow running `just ci` on `ubuntu-latest` + Python 3.12. |
| T-003 | [T-003-precommit-stack.md](T-003-precommit-stack.md) | `.pre-commit-config.yaml` with `ruff`, `ruff-format`, `mypy --strict`, `pytest` fast subset, `sqlfluff`, `djlint`, `bandit`, `detect-secrets`, stdlib hooks; `pyproject.toml` config blocks for each; 90% coverage threshold wiring. |
| T-004 | [T-004-config-module.md](T-004-config-module.md) | `src/budget_planner/config.py` using `pydantic-settings`, `.env.example`, bootstrap `app.py` wiring enough to serve a 200 OK on `/`. |

Order of execution: T-001 → T-002 → T-003 → T-004. Each task is a required predecessor of the next; agents must land each one green (its own validation section) before starting the next.

Downstream consumers (Phase 1+): the config module (T-004), the recipe surface (T-002), and the directory layout (T-001) are all referenced by Phase 1 migrations and Phase 2 services.
