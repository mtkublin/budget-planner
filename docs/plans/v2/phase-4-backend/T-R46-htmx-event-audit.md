# T-R46 — HTMX event wiring audit

- **Phase**: 4 — Backend
- **Sequential**: last Phase 4 task.
- **Depends on**: T-R40..T-R45.
- **References**: ADR-0056, prior Phase 11 HTMX event table.

## Context

Every mutation endpoint fires one or more `HX-Trigger` events so listeners (`budget-stale`, `ledger-stale`, `forecast-stale`, `accounts-stale`, `today-stale`, `settings-categories-stale`, `analytics-stale`) refresh dependent fragments. This audit confirms every new endpoint fires the right events + updates the central event table.

## Deliverables

- `src/budget_planner/web/routers/README.md` HTMX event table extended with every new endpoint from T-R40..T-R45.
- Each row carries: endpoint, side-effect description, events fired, downstream listeners.
- `src/budget_planner/web/htmx.py::EVENT_TABLE` constant export (dict mapping endpoint → tuple of event names) consumed by:
  - Integration tests (assert each endpoint response's `HX-Trigger` header matches the table).
  - A new audit script `scripts/htmx_audit.py` that scans the codebase for `HX-Trigger` emissions and reports drift from `EVENT_TABLE`.
- `just htmx-audit` recipe runs the script in CI.

## Acceptance criteria

- `just htmx-audit` green: every endpoint in `EVENT_TABLE` fires exactly the declared events; no endpoint fires an undeclared event.
- Integration tests parametrised over `EVENT_TABLE`; adding a new endpoint without a table entry fails CI.
- `routers/README.md` table matches `EVENT_TABLE` byte-for-byte (verified by a small test).

## Validation hook

```sh
just htmx-audit && pytest tests/integration/web/test_htmx_events.py
```

## Risks & gotchas

- Listeners already registered in templates may consume events the audit cannot see from the server side. Document the listener → event mapping in the same table so human review covers both directions.
- Multi-event triggers (`HX-Trigger: {"a": {...}, "b": true}`) must round-trip through the audit intact.

## Handoff notes

- Phase 7 cleanup consults this table before deleting any legacy route; events emitted by legacy routes must either migrate to a new endpoint or be removed from the table.
