# T-116 [S] Phase 12 docs scaffolding — ADR-0038 + ADR-0039 + ADR-0040 + requirements + task files (docs only)

> Depends on: nothing. Blocks: T-117, T-123, T-124.

## Scope

Docs-only. No code lands. Delivery:

- Write [ADR-0038](../../../adr/0038-recurring-standalone-lifecycle.md) — Recurring Rules Standalone Lifecycle (supersedes ADR-0013; amends ADR-0012).
- Write [ADR-0039](../../../adr/0039-budget-daily-spend-includes-recurring.md) — Budget "Left to Spend per Day" Includes Recurring Commitments (amends ADR-0025 §F4.6, ADR-0038).
- Write [ADR-0040](../../../adr/0040-modal-dismissal-scope.md) — Modal Dismissal Fires on Form Submit Only (amends ADR-0030 §5).
- Flip ADR-0013 header to **Superseded by ADR-0038**; keep file contents (forecast still uses the generator) but add a supersession note at the top.
- Update [`docs/adr/README.md`](../../../adr/README.md) index with ADR-0038 / 0039 / 0040 rows.
- Update [`docs/requirements.md`](../../../requirements.md):
  - F1.1 — amount accepts `,` and `.`; side-effect HTMX from amount input must not dismiss the slide-over (ADR-0040 cross-link).
  - F2.1 — Credit-limit visibility pinned to lockstep *including* initial render inside slide-over (bugfix noted + T-123 reference).
  - §2.3 — Split into §2.3a (Planned, one-off) and §2.3b (Recurring, standing). F3.1 narrowed (new rows always `recurring_rule_id IS NULL`); F3.2 adds `next_due` persistence; F3.5 adds Promote/Override/Skip-next/Delete affordances; F3.6 narrowed to "one override applies to one promote"; F3.7 unchanged (planned); new F3.8 (recurring promote flow) + F3.9 (skip-next vs delete) + F3.10 (Ledger Planned tab excludes virtual rows).
  - F4.6 — `remaining_minor = budgeted − spent − committed`; cross-link ADR-0039.
  - §3.9 Overview panel C — rewrite upcoming semantics around planned + recurring union by `services.upcoming.list_upcoming`; group `+ Planned` + `+ Recurring` into one visual cluster.
  - §3.9 Ledger — Planned tab excludes virtual; Recurring tab gains Promote / Override-next / Skip-next / Delete columns.
- Create `docs/plans/v1/phase-12/README.md` with trigger, decisions, scope, task table, handoff invariants.
- Create per-task stubs: `T-116-docs-scaffolding.md` (this file), `T-117-migration-and-domain.md`, `T-118-recurring-promote-service.md`, `T-119-decouple-planned-from-recurring.md`, `T-120-budget-committed-minor.md`, `T-121-overview-upcoming-union.md`, `T-122-ledger-recurring-actions.md`, `T-123-account-credit-limit-initial-render.md`, `T-124-modal-dismissal-scope.md`.
- Append a dated line to [`docs/CHANGELOG.md`](../../../CHANGELOG.md).
- Append the Phase 12 block to [`docs/plans/v1/tasks.md`](../tasks.md).

## Acceptance

- `rg -n "ADR-0038|ADR-0039|ADR-0040" docs/` returns the full cross-reference set (requirements, phase readme, task files, index).
- ADR-0013 header shows the superseded status.
- `docs/plans/v1/tasks.md` lists Phase 12 with T-116..T-124 and dependencies.
- No source files in `src/budget_planner/` touched.
- `just ci` unchanged (docs changes do not affect test selectors — `tests/integration/docs/*` has no gates).

## Non-goals

- Writing any `.py`, `.sql`, `.html`, `.css`, or `.js`.
- Running `frontend-visual-audit` (nothing visual changed).
