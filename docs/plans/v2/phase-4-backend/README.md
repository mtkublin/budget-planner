# Phase 4 — Backend additions

> Six new / amended endpoints implied by the design. Each follows router → service → repository → SQL and reuses existing primitives. No new tables.
>
> Parallel-safe with Phase 3.

Entry: Phase 1 exit criteria met.

Exit: each endpoint ships with ≥ 90% coverage, pure service helpers, documented `HX-Trigger` events.

Tasks: T-R40..T-R46.

- T-R40 `GET /today/afford?amount=`
- T-R41 `POST /recurring/formula/preview`
- T-R42 `GET /accounts/last-checked`
- T-R43 `GET /plan/analytics` bundle
- T-R44 `POST /categories/{id}/{archive,restore}`
- T-R45 `POST /recurring/batch/promote-due` + `POST /planned/batch/promote-due`
- T-R46 HTMX event wiring audit

ADR references: 0056, 0038, 0022, 0041, 0043, 0047.
