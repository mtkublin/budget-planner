# ADR-0020: Import Deferred to a later version, Export in v1

- **Status**: Accepted
- **Date**: 2026-10-23 (updated 2026-10-28: deferral target was "v2" when authored; v2 was reassigned to the Rising Dough redesign, so import is now deferred — target version unassigned, remains out of scope for both v2 and v3)

## Decision

- **Export** (CSV + Parquet) is in v1. Available on the persistent transaction log, the planned log, and the analytics view — operating on the currently filtered record set.
- **Import** (bank CSVs) is **deferred past v1**. v1 ships with manual-entry only; v2 (Rising Dough redesign) and v3 (remote deployment) do not pick it up either. A future version will carry the import work.

## Rationale

Each bank's CSV format differs. Writing N parsers plus a column-mapping UI plus a dedupe strategy is 1–2 weeks of work that detracts from proving the core loop (log, budget, forecast). Easier to adopt once the v1 shape is validated.

## Future shape (preview, not binding)

- Pluggable parser modules under `src/budget_planner/adapters/import_/parsers/`.
- Each parser exposes `name`, `can_parse(file) -> bool`, `parse(file) -> list[NewTransaction]`.
- Import UI: upload file → auto-detect parser → preview mapping → confirm.
- Dedupe via content-hash on `(operation_date, amount, description, account_id)`.

## Alternatives Considered

- **Generic CSV import in v1**: non-trivial dev + UX design; delays core loop.
- **Only one bank parser hard-coded**: slippery slope, biases design.
