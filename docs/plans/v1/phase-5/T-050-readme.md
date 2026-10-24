# T-050 — README

> Phase 5 — Polish. Status: pending.

## Purpose

Author the top-level `README.md` so a new contributor (or future-you on a new machine) can go from `git clone` to a running app in under five minutes. The README is the shortest path into the project; everything deeper lives in `docs/`. This task does **not** rewrite `docs/`; it points at it.

## Inputs / prerequisites

- Upstream tasks: Phase 3 routers (`T-030..T-039`) and Phase 4 testing (`T-040..T-043`) must be green. The README documents the finished shape of the app, so the commands and routes it names must exist.
- Docs it must reference (relative links from repo root):
  - [`docs/requirements.md`](../../requirements.md)
  - [`docs/tasks.md`](../../tasks.md)
  - [`docs/implementation_plan.md`](../../implementation_plan.md)
  - [`docs/adr/README.md`](../../adr/README.md)
  - [`CLAUDE.md`](../../../CLAUDE.md)
- ADRs implicitly surfaced:
  - [`ADR-0002`](../../adr/0002-web-stack-fastapi-htmx-jinja.md) — stack summary.
  - [`ADR-0003`](../../adr/0003-database-sqlite-only-v1.md) — SQLite-only disclaimer.
  - [`ADR-0004`](../../adr/0004-package-manager-uv.md) — `uv` prereq.
  - [`ADR-0007`](../../adr/0007-timezone-handling.md) — the "times are UTC, dates are naive, display tz = Europe/Warsaw" note.
  - [`ADR-0016`](../../adr/0016-task-runner-just.md) — `just` prereq.
- Local tooling the README asks the reader to install: `uv >= 0.4`, `just`, Python 3.12 (installable via `uv python install 3.12`).

## Deliverables

- `README.md` at the repo root. Single file. Replace any existing stub.

## Step-by-step

Draft section-by-section. Each heading below is a literal top-level `##` section in `README.md` unless otherwise noted.

1. **`# Budget Planner`** (H1, project title). One-sentence tagline: "Local-first personal budget planning and fortune tracking. Single user, multi-account, multi-currency. Served on `127.0.0.1`."

2. **`## What this is`** — three bullets:
   - Local-only web app, binds to `127.0.0.1:8000`. No LAN exposure, no auth.
   - SQLite file on disk; data stays on the machine.
   - Python 3.12 / FastAPI / HTMX / Jinja2 / Tailwind (CDN) / Plotly.

3. **`## Prerequisites`** — table or list:
   - Python 3.12 (resolved via `uv python install 3.12`).
   - [`uv`](https://docs.astral.sh/uv/) `>= 0.4` — dependency and venv manager.
   - [`just`](https://github.com/casey/just) — task runner.
   - macOS/Linux. Windows unverified; use WSL.

4. **`## Quick start`** — five commands in order, each with one-line "what it does":

   ```sh
   git clone <repo-url> budget_planner
   cd budget_planner
   just install    # uv sync + install pre-commit hooks
   just migrate    # apply pending SQL migrations into the dev SQLite file
   just seed       # seed default categories (Transit, Reconciliation) and demo accounts
   just dev        # start FastAPI with hot reload on http://127.0.0.1:8000
   ```

   Add a note: "First `uv sync` pulls `pyarrow` which is ~70 MB. One-off."

5. **`## Daily commands`** — command cheat-sheet matching the `justfile` recipes:

   | Command | Does |
   |---------|------|
   | `just dev` | FastAPI dev server, hot reload, `127.0.0.1:8000`. |
   | `just test` | Pytest with coverage; fails under 90%. |
   | `just lint` | `ruff` + `sqlfluff` + `djlint`. |
   | `just format` | `ruff format` + `ruff --fix`. |
   | `just typecheck` | `mypy --strict`. |
   | `just ci` | Everything CI runs. |
   | `just db-reset` | Recreate the dev DB from migrations + seed. |
   | `just migrate` | Apply pending migrations. |
   | `just seed` | Insert seed data. |

6. **`## Where things live`** — three-column table (feature → route → doc link). Cover the eight primary routes implemented in Phase 3: `/`, `/transactions`, `/accounts`, `/categories`, `/planned`, `/recurring`, `/budget`, `/forecast`, `/analytics`.

7. **`## Project docs`** — bulleted map:
   - `docs/requirements.md` — canonical requirements, scope guard in section 3.8.
   - `docs/tasks.md` — task breakdown by phase.
   - `docs/implementation_plan.md` — phased plan + Definition of Done.
   - `docs/adr/` — architecture decisions. Start at `docs/adr/README.md`.
   - `docs/plans/` — per-task implementation plans (what you're reading if you're an agent).
   - `CLAUDE.md` — agent handoff rules; docs-first policy.

8. **`## Configuration`** — one short block:
   - `.env.example` lists all keys. Copy to `.env` and edit.
   - Keys: `database_url`, `base_currency` (default `PLN`), `display_timezone` (default `Europe/Warsaw`), `host` (locked to `127.0.0.1` in v1), `port` (default `8000`), `fx_api_url` (default `https://api.frankfurter.app`).
   - Reference ADR-0007 for the time semantics (UTC in DB, naive `DATE` on transactions, display tz).

9. **`## Data model one-liner`** — one paragraph pointing at `docs/requirements.md` section 2 for details. Mention: positive-integer minor units, direction from `category.direction`, soft delete + audit log on every mutation (link ADR-0019).

10. **`## Troubleshooting`** — four known failure modes:
    - `uv sync` fails on `pyarrow` wheels → upgrade `uv`, retry.
    - `just migrate` fails with `database is locked` → close any open SQLite browser, retry.
    - FX fetch failing on the forecast page → expected offline; last-known rate is used (ADR-0006 fallback).
    - Pre-commit hook `detect-secrets` flags a file → audit, run `detect-secrets scan --baseline .secrets.baseline`, review additions.

11. **`## License`** — placeholder: "Personal project. All rights reserved." (adjust if the owner picks a license later; this task does not pick one).

12. **`## Status`** — one-line "v1 scope frozen at Phase 5; see `docs/requirements.md` section 3.8 for what's out of scope."

## Validation / acceptance

- Fresh clone + the five quick-start commands succeed on a machine that has only Python 3.12, `uv`, and `just` installed. Measured on macOS and Linux at minimum.
- `curl http://127.0.0.1:8000/` returns `200 OK` after `just dev` is up.
- Every relative link in the README resolves (verify with a Markdown link-check tool or by hand).
- No command listed in the "Daily commands" table is missing from the actual `justfile`.
- Phase 5 exit criterion #4 from `docs/implementation_plan.md` ("README up to date; `just dev` works on a clean clone") is satisfied.

## Risks & gotchas

- Quick-start drift: `just install` is a composite that must call `uv sync` **and** install pre-commit hooks. If T-002's recipe diverges, the README's instructions will silently stop working. Re-read `justfile` before committing.
- Platform-specific `uv python install` output can confuse first-time users on Linux without `curl`. Call out `uv --version` sanity check in the troubleshooting section if needed.
- Do **not** add deploy / Docker / Fly.io sections — explicitly deferred to v2 (`docs/tasks.md` Phase 6). Note this in a one-line "Deployment" subsection pointing at Phase 6 so a reader does not file an issue asking for it.
- Avoid duplicating content from `docs/requirements.md`. The README is a map, not a mirror.

## Handoff notes

Last of the Phase 5 tasks to land, because it documents the finished UI shape. After this task:

- Add a dated `v1.0.0` entry to `docs/CHANGELOG.md` referencing T-050 and the three sibling Phase 5 tasks.
- Flip the T-050 line in `docs/tasks.md` to `✅`.
- Flip Definition-of-Done row #4 in `docs/plans/phase-5/README.md` from pending to done.
- Commit message: `docs(T-050): write top-level README quick-start and docs map`.
