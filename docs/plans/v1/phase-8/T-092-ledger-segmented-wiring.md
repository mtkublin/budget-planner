# T-092 [S] Ledger segmented wiring fix

**Phase:** 8 — Post-redesign UX fixes
**Group:** G3
**Depends on:** T-064 (ledger unification)
**Size:** S
**Status:** planned

## Scope

The ledger segmented control (Actual · Planned · Recurring) is a hard no-op: `hx-target="#ledger-table"` resolves to no element because `_table.html` renders ids `txn-table` / `planned-table` / `recurring-table`. HTMX silently drops the swap and the user sees no feedback. This also makes the context-aware FAB (`fab_target_for`) unreachable because the user can never actually change the ledger view.

## Changes

- `src/budget_planner/web/templates/ledger/_table.html`:
  - Add outer wrapper `<div id="ledger-table" data-ledger-table …>` around the current `<div id="{{ table_id }}" …>`. The inner element keeps legacy ids (`txn-table` / `planned-table` / `recurring-table`) for test selectors and HTMX fragment aliases.
  - The fragment response from `/ledger/table` must include the outer wrapper so `hx-swap="outerHTML"` replaces the whole wrapper on view switch.

- `src/budget_planner/web/templates/ledger/index.html`:
  - Already targets `#ledger-table` — no change.

- `src/budget_planner/web/routers/ledger.py`:
  - `_render_table` already renders `ledger/_table.html` — unchanged.

## Non-goals

- No change to filter form target (`#ledger-table` already correct after this change).
- No URL or query-param changes.
- No change to pagination target.
- Legacy fragment aliases (`/transactions/table`, `/planned/table`) stay backward-compatible.

## Test plan

- Integration test `tests/integration/web/test_ledger.py` (new or extend existing): request `/ledger`, click each segmented button via HTMX simulation, assert the response contains `<div id="ledger-table"` and the correct inner id.
- Add explicit regression: after clicking `view=planned`, response must contain `#planned-table`.
- E2E smoke: open Ledger, click Planned, assert the planned table replaces the actual table.

## Secondary effect (resolves obs 6)

Once the segmented works, `fab_target_for(request)` begins routing per view:

- `/ledger?view=planned` → FAB opens `/planned/new`.
- `/ledger?view=recurring` → FAB opens `/recurring/new`.

No code change needed in `web/context.py`.

## Docs

- `docs/CHANGELOG.md` — one dated line.
- `docs/plans/v1/tasks.md` — mark `✅ T-092`.
- No ADR (bug fix, not a decision).
