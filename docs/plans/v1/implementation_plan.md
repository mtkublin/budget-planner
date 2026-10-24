# Budget Planner — Implementation Plan

> Companion to `docs/tasks.md`. Describes the order, phasing, acceptance criteria, and handoff shape so subsequent agents can pick up work without re-deriving context.

---

## Guiding Principles

1. **Functional-first.** No classes beyond dataclasses, Pydantic models, Protocols. Services and repositories are modules of pure functions. The only state is the SQLite connection and the FastAPI request.
2. **Thin web, fat services.** Routers call services, services call repositories, repositories call SQL. No business logic in routers.
3. **DRY by composition.** Shared repository helpers, shared Jinja partials, shared service primitives. Transactions log, planned log, and recurring materialisation share filtering/export code paths.
4. **Immutable by default.** Dataclasses `frozen=True`. Build new values; don't mutate.
5. **Explicit audit.** Every mutation calls `write_audit` in the same DB transaction.
6. **One ADR per meaningful decision.** Documented upfront in `docs/adr/`.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Browser  ◄──── HTMX fragments ───── Jinja templates          │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI routers  (src/budget_planner/web/routers/)           │
│    - thin orchestration, request parsing, template rendering  │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Services  (src/budget_planner/services/)                     │
│    - pure business logic                                      │
│    - fx, balance, planned, recurring, budget, forecast,       │
│      reconciliation, export, audit                            │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Repositories  (src/budget_planner/repositories/)             │
│    - CRUD with soft-delete filter + audit write               │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  SQLite  (file)   +  adapters (fx HTTP, export writers)       │
└──────────────────────────────────────────────────────────────┘
```

### Module dependencies (no cycles)

```
config  ◄──  everything
domain  ◄──  repositories, services, web
repositories  ◄──  services, web
services  ◄──  web
adapters  ◄──  services (fx), web (export download)
```

---

## Phased Delivery

### Phase 0 — Bootstrap (T-001..T-004)
Goal: a developer can `git clone`, `just install`, `just migrate`, `just seed`, `just dev` and land on an empty FastAPI page.

Exit criteria:
- CI runs `just ci` on push and passes with the empty project.
- Pre-commit active on every commit.
- `just --list` self-documents all recipes.

### Phase 1 — Data layer (T-010..T-014)
Goal: all persistence shapes exist; no HTTP yet.

Exit criteria:
- `just migrate` applies the schema from zero.
- Repository functions pass unit tests against a temp DB.
- Audit log receives entries from every mutation.
- Soft-delete filter is applied by default; `include_deleted=True` round-trips.

### Phase 2 — Services (T-020..T-028)
Goal: all business logic exists as pure functions, independently testable.

Exit criteria:
- Each service module ≥ 90% coverage.
- Forecast + balance derivable from a seeded fixture with known expected output.
- FX service passes with mocked HTTP for both happy and fallback paths.
- Recurring occurrence generator correct for all three cadences, including year-boundary wrap and the full override state machine.

### Phase 3 — Web layer (T-030..T-039)
Goal: every functional requirement reachable through the browser.

Exit criteria:
- Each router under test via `TestClient` + Jinja (snapshot or structural assertions on key fragments).
- HTMX partials swap correctly (verify via response headers + body shape).
- `GET /` lands on a dashboard showing current-month budget state + total fortune + next 7 days.
- Plotly charts render on forecast + analytics.

### Phase 4 — Testing (T-040..T-043)
Goal: coverage gate green, e2e smoke flows green.

Exit criteria:
- `just test` enforces 90% coverage, CI fails otherwise.
- E2E suite covers: add txn, set budget, recurring rule → promote, reconciliation.

### Phase 5 — Polish (T-050..T-053)
Goal: not embarrassing to show someone.

Exit criteria:
- README quick-start works end to end on a clean machine.
- Validation errors rendered inline.
- No a11y regressions on main flows.
- UI avoids the generic template look (see global `web/design-quality.md` rule).

### Phase 6 — Deferred
Documented in `docs/tasks.md` under Phase 6. Not planned for v1.

---

## Suggested Execution Order (for sequential agents)

A single-threaded agent should walk tasks top-to-bottom within a phase. Parallel-safe tasks (`[P]`) can be done out of order within their phase. Phases are strict gates.

Recommended agent personas per phase:
- **Phase 0**: `general-purpose` or `architect`.
- **Phase 1**: `code-architect` for schema, `general-purpose` for repository fillers.
- **Phase 2**: `general-purpose` with `tdd-guide` style discipline (write tests first, especially for the generator, forecast, FX).
- **Phase 3**: `general-purpose` + review via `code-reviewer`.
- **Phase 4**: `tdd-guide` + `e2e-runner`.
- **Phase 5**: `code-simplifier`, `comment-analyzer`.

---

## Handoff Protocol

For each task:

1. Agent reads: this file, `docs/requirements.md`, `docs/tasks.md`, relevant ADR(s), existing code.
2. Agent writes:
   - Code + tests.
   - Updates `docs/tasks.md` with a `✅` prefix on the task line.
   - Appends a dated note to `docs/CHANGELOG.md` (create if missing) with the task id and what was shipped.
   - New ADR under `docs/adr/XXXX-*.md` for any decision not already covered.
3. Agent verifies: `just ci` green locally.
4. Agent commits with conventional-commits format referencing the task id (e.g. `feat(T-021): derive account balance`).

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SQLite concurrency when running tests in parallel | Use per-test temp DB file + `pytest-xdist`-safe fixtures. |
| HTMX swap bugs hard to catch in unit tests | Structural assertions on returned HTML fragments (`BeautifulSoup`), not full snapshots. |
| FX API downtime | Fallback to last-known rate implemented in `fx.get_rate`. CI tests both paths with mocks. |
| Forecast perf as data grows | Pure fn, measured with pytest-benchmark on a 10-year seed. If slow, add caching keyed on last `audit_log.id`. |
| Scope creep into v2 features | Phase 6 is a hard "no" for v1. Any ask in that list requires a new ADR. |

---

## Definition of Done (v1)

- All functional requirements in `docs/requirements.md` section 2 reachable via the UI.
- `just ci` green on `main`.
- Coverage ≥ 90%.
- README up to date; `just dev` works on a clean clone.
- All ADRs committed.
- No TODO/FIXME in `src/` without an attached issue reference.
