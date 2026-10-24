# Phase 2 — Services (Pure Business Logic) · Plan Index

> Goal of the phase: every business rule exists as a module of pure functions in `src/budget_planner/services/`. No HTTP yet. Services receive a `sqlite3.Connection` plus pure data; they call Phase 1 repositories and never touch SQL directly.

Phase gate (from `docs/implementation_plan.md`):

- Each service module ≥ 90% coverage.
- Forecast + balance derivable from a seeded fixture with known expected output.
- FX service passes with mocked HTTP for both happy and fallback paths.
- Recurring occurrence generator correct for all three cadences, including year-boundary wrap and the full override state machine.

Design rules enforced across every plan in this phase:

- Functional-first — no classes beyond frozen dataclasses / Pydantic DTOs / Protocols (ADR-0021).
- Immutable by default — build new values; do not mutate inputs.
- Thin web, fat services — all business rules land here; Phase 3 routers are mechanical.
- Dependencies passed explicitly — `conn: sqlite3.Connection`, `http: httpx.Client`. No module-level state.
- Audit discipline — services never bypass repositories; mutations go through Phase 1 repository functions, which call `write_audit` (see T-028).

Tasks:

| # | File | Mode | Purpose |
|---|------|------|---------|
| T-020 | [T-020-fx-service.md](T-020-fx-service.md) | `[P]` | Cached historical FX lookup with `frankfurter.app` fetch + stale-fallback on API error (ADR-0006). |
| T-021 | [T-021-balance-service.md](T-021-balance-service.md) | `[P]` | Pure derivation of per-account balance from `opening_balance` + signed transactions (ADR-0008, ADR-0011). |
| T-022 | [T-022-recurring-occurrence-generator.md](T-022-recurring-occurrence-generator.md) | `[P]` | Expand recurring rules into virtual occurrences for a date range + apply sparse overrides (ADR-0013). |
| T-023 | [T-023-planned-log-service.md](T-023-planned-log-service.md) | `[P]` | UNION persisted planned rows with virtual occurrences; manual planned→actual promotion (ADR-0012, ADR-0013). |
| T-024 | [T-024-budget-service.md](T-024-budget-service.md) | `[P]` | Three-tier budget resolution + current-month summary with analytics (ADR-0014). |
| T-025 | [T-025-forecast-service.md](T-025-forecast-service.md) | `[P]` | Deterministic daily projection across horizon with per-day FX to base currency (ADR-0015). |
| T-026 | [T-026-reconciliation-service.md](T-026-reconciliation-service.md) | `[P]` | Insert a signed `adjustment` transaction so derived balance equals the user-supplied actual (ADR-0008, ADR-0011). |
| T-027 | [T-027-export-service.md](T-027-export-service.md) | `[P]` | CSV + Parquet serialization shared by transactions / planned / analytics views (ADR-0020). |
| T-028 | [T-028-audit-helper.md](T-028-audit-helper.md) | `[P]` | Shared `write_audit` function used by every mutating repository call (ADR-0019). |

## Dependency graph

Within Phase 2 (upstream → downstream). T-013 (repositories) and T-014 (domain types) are Phase 1 prerequisites; everything in this phase imports from both.

```
                          ┌──────────────────────────┐
                          │ Phase 1                  │
                          │   T-013 Repositories     │
                          │   T-014 Domain types     │
                          └────────────┬─────────────┘
                                       │
   ┌───────────────┬───────────────────┼───────────────────┬─────────────────┐
   │               │                   │                   │                 │
   ▼               ▼                   ▼                   ▼                 ▼
T-028 Audit    T-020 FX           T-021 Balance        T-022 Recurring   T-024 Budget
helper         service            service              occurrence gen    service
   │               │                   │                   │                 │
   │               │                   │                   ▼                 │
   │               │                   │              T-023 Planned log      │
   │               │                   │                   │                 │
   │               │                   └──────────┬────────┤                 │
   │               │                              ▼        ▼                 │
   │               └─────────────────────────► T-025 Forecast service        │
   │                                               │                         │
   │                                               ▼                         ▼
   │                                        (Phase 3 web layer: forecast, budget, …)
   │
   ├──► consumed implicitly by every mutating repository function in T-013
   │
   ▼
T-026 Reconciliation ◄── depends on T-021 (derived balance) + T-013 (txn repo)

T-027 Export ◄── stands alone; depends only on T-013 for the row shapes it serializes.
```

Narrative edges:

- T-028 is a transversal helper. T-013 is where it is physically called from; services never call it directly. Listed here so Phase 2 agents understand the invariant.
- T-020 feeds T-025 (forecast converts to base currency per day).
- T-021 feeds T-025 (horizon starts at today's derived balance) and T-026 (reconciliation delta).
- T-022 feeds T-023 (virtual occurrences inside planned list) and T-025 (projected inflows/outflows across horizon).
- T-024 is independent of the balance/forecast chain; it reads transactions + the three budget tables.
- T-027 reads already-shaped records from any upstream caller; it does not know the domain.

## Suggested execution order

Any order satisfying the arrows above is legal. A single-threaded agent should walk:

1. T-028 (unblocks ambient audit invariant checks in later tests).
2. T-020, T-021, T-022 in parallel (independent).
3. T-023 (needs T-022).
4. T-024 (independent, slot anywhere).
5. T-026 (needs T-021).
6. T-025 (needs T-020, T-021, T-022).
7. T-027 last (requires no other service but benefits from seeing final record shapes).

## Doc-correctness notes (upstream)

- `docs/tasks.md` cites **ADR-0017** for T-024 and **ADR-0018** for T-025; those ADR numbers are the pre-commit stack and the CI matrix. The correct references are **ADR-0014** (budget three-tier) and **ADR-0015** (forecast deterministic). Each per-task plan here uses the correct ADR.
- `docs/tasks.md` cites **ADR-0022** for T-028 and T-013; the index tops out at **ADR-0021**. The Phase 1 T-013 plan already flags a follow-up ADR for the repository/audit pattern. T-028's plan references the active ADR-0019 (soft delete + audit log) and defers writing a dedicated repository-pattern ADR to Phase 1.
