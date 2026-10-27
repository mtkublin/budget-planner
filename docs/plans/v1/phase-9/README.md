# Phase 9 — Left Daily Spend

> Status: pending (docs scaffolding landed via T-090; code starts at T-091). Scope: budget surface + first per-user preference. No change to transaction / account / category / FX arithmetic.

## Overview

Phase 9 adds a prominent **left daily spend** metric to `/budget`:

```
left_daily_spend_minor =
    MonthTotals.remaining_minor
  / max((next_planned_income_date - today).days, 1)
```

- `MonthTotals.remaining_minor` is the existing sum of per-category remaining budgets, already computed by `services.budget.month_summary` (lines 179-183 of `services/budget.py`). Unbudgeted categories are already excluded there.
- `next_planned_income_date` is the earliest `operation_date > today` in the planned log (persisted `planned_transactions` + virtual recurring occurrences, deduped per ADR-0013) whose `category_id` equals the user's configured **income anchor** category.
- If no planned income is found for the anchor (or no anchor is configured), the denominator falls back to the number of days from today (exclusive) through the last day of the current month (inclusive). The minimum denominator is 1 to guard against division by zero on the final day of the month.
- If `MonthTotals.budgeted_minor == 0` the metric is undefined and renders as `—`.

The anchor category is a per-user preference. v1 has no settings store, so this phase also introduces a generic `user_preferences(user_id, key, value)` table — one migration, pays for every future preference. See [ADR-0025](../../../adr/0025-user-preferences-and-income-anchor.md).

Primary surfaces:

| Change | Where |
|---|---|
| New metric card (number + caption) above the ledger table | `/budget` |
| New "Income anchor" `<select>` section | `/budget/manage` |
| New endpoint for setting / clearing the anchor | `POST /budget/preferences/income-anchor` |

Decision: see [`ADR-0025`](../../../adr/0025-user-preferences-and-income-anchor.md). Requirements: [F4.6](../../../requirements.md#24-monthly-budget), [F4.7](../../../requirements.md#24-monthly-budget).

## Task table

| ID | Task | Dep |
|---|---|---|
| T-090 | ADR-0025 + requirements + CHANGELOG (docs only) | — |
| T-091 | Migration `0005_user_preferences.sql` | T-090 |
| T-092 | Domain + repository (`preferences.py` modules) | T-091 |
| T-093 | Preferences service + income anchor resolver (liveness + direction defence) | T-092, T-033 |
| T-094 | Next-planned-income lookup on `services/planned.py` | T-023 |
| T-095 | Left daily spend in `services/budget.py` (`MonthSummary` extension + `today` injection) | T-024, T-093, T-094 |
| T-096 | `/budget` card + `/budget/manage` anchor selector + endpoint | T-036, T-095 |

## Dependency map

- **T-090** unblocks every code task; it is the docs round itself.
- **T-091** → **T-092** → **T-093** (vertical slice through the new preference store).
- **T-094** is independent of the preferences work and may land in parallel with T-091..T-093.
- **T-095** needs both T-093 (anchor resolver) and T-094 (next-income lookup).
- **T-096** closes the phase; depends on T-095 and the existing budget router (T-036).

Parallel-safe set once T-092 is in: `{T-093, T-094}`.

Est. size: each task ≤ 1 day; whole phase ~1 week sequential, ~3 days with fan-out.

## Exit criteria (verification checklist)

Local, end-to-end, no new tooling:

- [ ] `just migrate` applies `0005_user_preferences.sql` cleanly on a fresh DB and idempotently on an existing one.
- [ ] `just seed` is unaffected (preference table is empty by design).
- [ ] `just test` — new unit + integration tests pass. Coverage stays ≥ 90%.
- [ ] `just lint` + `just typecheck` + `just ci` all green.
- [ ] Manual: `just dev` → `/budget/manage`, pick a salary category, save:
  - [ ] `/budget` card shows `remaining / days` number + caption with the chosen category name and next income date.
  - [ ] Add a planned one-off for the anchor one week ahead → card updates (via HTMX `budget-stale` or page reload).
  - [ ] Clear the anchor (`— none —`) → card caption falls back to "end of month" and the number recomputes.
  - [ ] Soft-delete the anchor category → card still renders, falls back to end-of-month; no 500.
- [ ] `grep` guard still passes (no hard-coded palette values outside tokens).
- [ ] `docs/CHANGELOG.md` entry for the phase landing day.

## See also

- Decision: [`docs/adr/0025-user-preferences-and-income-anchor.md`](../../../adr/0025-user-preferences-and-income-anchor.md)
- Prior phase: [`../phase-7/`](../phase-7/) — Liability Accounts (sibling first "post-v1-polish" additive phase, same shape of docs-first → migration → domain/repo → service → UI → tests).
- Related phase: [`../phase-6/`](../phase-6/) — UX redesign that defined the current `/budget` composition.
