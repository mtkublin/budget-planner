# Budget Planner — Claude Guide

Local-first personal budget planning and fortune tracking web app. Single user, multi-account, multi-currency.

## Change policy — docs come first (MANDATORY)

**Any change to this project must go through the documentation first.** No exceptions.

Before touching code (or docs that drive code):

1. **Requirement change** → update `docs/requirements.md` first. If scope-affecting, also update `docs/tasks.md` and `docs/implementation_plan.md`.
2. **Architectural / design decision** → write a new ADR under `docs/adr/` (next sequential number), update `docs/adr/README.md`, and reference it from the affected requirement or task. Supersede, don't delete, prior ADRs.
3. **New task or re-scoped task** → edit `docs/tasks.md` first; link to the ADR(s) it depends on.
4. **Stack / tooling change** → ADR first, then `docs/requirements.md` section 3, then code.
5. **Scope creep into Phase 6 / v2 items** → requires an ADR explicitly flipping it into v1.

Only after the relevant docs are updated and committed (or staged in the same PR) may the code change land. A code change without a matching doc update is treated as incomplete.

## Where to look

| Need | Path |
|------|------|
| Full requirements | `docs/requirements.md` |
| Task breakdown | `docs/tasks.md` |
| Phased implementation plan + handoff rules | `docs/implementation_plan.md` |
| Decisions (and *why*) | `docs/adr/README.md` |

Always read the relevant ADR before changing an area it covers.

## Stack

- Python 3.12, FastAPI, Jinja2, HTMX, Tailwind (CDN), Plotly.
- SQLite only in v1 (DuckDB deferred).
- `uv` for deps, `just` for recipes.
- Pre-commit: `ruff`, `ruff-format`, `mypy --strict`, `pytest`, `sqlfluff`, `djlint`, `bandit`, `detect-secrets`.

## Code conventions

- **Functional-first.** Modules of pure functions. Dataclasses `frozen=True` for data; no classes beyond that unless they are DTOs or Protocols. See ADR-0021.
- **Thin web, fat services.** Routers call services; services call repositories; repositories call SQL. No business logic in routers.
- **Soft delete + audit log** for every mutable table. Use the repository helpers; never bypass them. See ADR-0019.
- **Amounts** stored as positive integer minor units; direction derived from `category.direction`. Reconciliation (direction=`adjustment`) is the only signed-amount exception. See ADR-0008.
- **Multi-currency**: account owns currency, transactions inherit. Aggregates convert to `base_currency` (default PLN) using historical FX rates cached locally. See ADR-0006.
- **Immutable by default.** Build new values; do not mutate.

## Developer commands

```sh
just install      # uv sync + install pre-commit hooks
just dev          # run FastAPI with hot reload on 127.0.0.1:8000
just test         # pytest with coverage; fails under 90%
just lint         # ruff + sqlfluff + djlint
just format       # ruff format + ruff --fix
just typecheck    # mypy --strict
just ci           # everything CI runs
just db-reset     # recreate the dev DB
just migrate      # apply pending migrations
just seed         # seed default categories + demo accounts
```

## Rules & scope

- **Scope guard**: `docs/requirements.md` section 3.8 lists what is **out of scope** for v1. Do not add v2 features without first writing a new ADR and updating `docs/requirements.md`.
- **Server binds to `127.0.0.1` only** in v1. No LAN or public exposure.
- **No secrets committed.** `detect-secrets` is in the pre-commit stack.
- **Timestamps are UTC in DB**, dates on transactions are naive `DATE`, display timezone defaults to `Europe/Warsaw`. See ADR-0007.

## Handoff checklist (for subsequent agents)

Before marking a task done:

1. **Docs updated first** (see "Change policy" above). `docs/requirements.md`, `docs/tasks.md`, and/or a new ADR reflect the change *before* code lands.
2. Code + tests committed; `just ci` green.
3. `docs/tasks.md` task line prefixed with `✅`.
4. Relevant ADR(s) referenced in the commit; a new ADR added if the task introduced an architectural decision not already recorded.
5. Append a dated line to `docs/CHANGELOG.md` (create on first use).
6. Conventional-commits message referencing the task id: e.g. `feat(T-021): derive account balance`.
