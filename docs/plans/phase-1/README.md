# Phase 1 — Data Layer · Plan Index

> Goal of the phase: every persistence shape exists and is exercised by unit tests. No HTTP yet. Repository functions apply soft-delete filtering by default and write an `audit_log` entry inside every mutation.

Phase gate (from `docs/implementation_plan.md`):

- `just migrate` applies the schema from zero.
- Repository functions pass unit tests against a temp DB.
- Audit log receives entries from every mutation.
- Soft-delete filter is applied by default; `include_deleted=True` round-trips.

Tasks:

| # | File | Mode | Purpose |
|---|------|------|---------|
| T-010 | [T-010-migration-framework.md](T-010-migration-framework.md) | `[S]` | Hand-rolled numbered `.sql` migration runner in `src/budget_planner/db/migrate.py` wired to `just migrate`. |
| T-011 | [T-011-core-schema-migration.md](T-011-core-schema-migration.md) | `[S]` | DDL for every table: users, accounts, categories, transactions, planned, recurring (+overrides), budget (3 tables), snapshots, fx_rates, audit_log. Indexes + CHECK constraints + partial UNIQUE on `name` with `deleted_at IS NULL`. |
| T-012 | [T-012-seed-data-migration.md](T-012-seed-data-migration.md) | `[S]` | Seed `users(id=1)` + system categories `Transit` (direction=`transit`) and `Reconciliation` (direction=`adjustment`). Flagged undeletable via a `is_system` column (added in T-011). |
| T-013 | [T-013-repository-layer.md](T-013-repository-layer.md) | `[P]` | One module per entity under `src/budget_planner/repositories/`. Pure functions. Shared `_mutate(...)` helper does audit write + updated_at bump in a single transaction. `include_deleted: bool = False` kwarg on every reader. |
| T-014 | [T-014-domain-types.md](T-014-domain-types.md) | `[P]` | Frozen dataclasses for every entity + Patch/New DTOs + filter DTOs. `Direction` + `Cadence` enums. `Money` helpers (`to_minor_units`, `from_minor_units`, `format_money`). |

Order of execution: T-010 → T-011 → T-012. T-013 and T-014 are parallel-safe once T-011 lands; T-013 depends on T-014 for the DTO shapes but the two can be developed concurrently if DTO signatures are agreed first.

Downstream consumers (Phase 2):
- Services (`fx`, `balance`, `recurring`, `planned`, `budget`, `forecast`, `reconciliation`, `export`, `audit`) consume the repository function signatures listed in T-013 and the dataclasses listed in T-014.
- `audit_log` is written by T-013; Phase 2 only reads it (no further writes from services).

Known doc issue to resolve during this phase:

- `docs/tasks.md` T-013 and T-028 reference **ADR-0022**, but the ADR index tops out at **ADR-0021**. See T-013 "Risks & gotchas" — this plan proposes writing a new ADR for the repository-layer pattern (soft-delete + audit discipline) as the first step inside T-013. Flagged, not yet executed.
