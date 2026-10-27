# Phase 12 — Recurring Standalone + Overview/Budget Fixups + Modal Scope + Account/Form Bugs

> Status: pending (docs scaffolding lands via T-116; code starts at T-117). Scope: schema (one additive migration), domain, service, router, and web-layer only. No service-arithmetic regressions permitted — all existing fortune / forecast / budget-month tests must stay green.

## Trigger

Field-use report 2026-10-27 — four non-negotiable changes:

1. **Planned vs Recurring are being conflated.** Recurring occurrences virtualise into the Planned log (ADR-0013), which blurs the mental model and leaves `next_due` without a durable home (`web/routers/ledger.py:144` renders `start_date` as a placeholder `next_due`). Recurring should have its own promote-and-advance flow; Ledger Planned tab should list only one-off planned.
2. **Overview Upcoming** needs the planned + recurring combination with per-kind actions, and the `+ Planned` / `+ Recurring` buttons must sit together as one visual cluster.
3. **New-transaction popover closes on amount keystroke.** `data-reset-on-submit` listener (ADR-0030 §5) matches on any descendant HTMX success — the amount input's `hx-get="/transactions/_limit_preview"` fires on every keystroke and takes the dialog down.
4. **Account slide-over** keeps the "Credit limit" input visible even when "Credit (liability)" is off, violating the ADR-0030 §6 lockstep.

Secondary (same phase, same bounded blast radius):
- **Budget "Left per day"** overstates by not pre-subtracting upcoming recurring commitments inside the current pay cycle.
- **Ledger Recurring row** lacks Promote / Delete / Override-next affordances. (Delete partly addressed by T-114 via `deactivate_rule`, but Promote + Override-next are missing.)
- **Amount field** must be pinned to accept both `,` and `.` as the decimal separator (behaviour exists per `numeric-input.js`; needs a regression test, not a code change).

## Decisions

- [ADR-0038 — Recurring Rules Standalone Lifecycle](../../../adr/0038-recurring-standalone-lifecycle.md): add `recurring_rules.next_due` + `last_promoted_date`; recurring gains its own promotion service; planned log drops the virtual-union branch; overrides narrowed to "one promote, then self-destruct"; forecast continues to use `services.recurring.expand` for the horizon projection only.
- [ADR-0039 — Budget "Left to Spend per Day" Includes Recurring Commitments](../../../adr/0039-budget-daily-spend-includes-recurring.md): `MonthTotals` grows `committed_minor`; `remaining_minor = budgeted − spent − committed`; template surfaces committed as a dim sub-line.
- [ADR-0040 — Modal Dismissal Scope](../../../adr/0040-modal-dismissal-scope.md): `data-reset-on-submit` fires only when `evt.target` is the form element itself *and* the request verb is `POST`/`PUT`/`DELETE`.

## Scope

| Change | Where | Source |
|---|---|---|
| Migration `0006_add_recurring_next_due.sql` + Python backfill | `migrations/`, `db/migrate.py` | ADR-0038 |
| Domain: `RecurringRule.next_due`, `RecurringRule.last_promoted_date` | `domain/recurring.py` | ADR-0038 |
| Repo: `recurring_repo.list_rules` / `create_rule` / `update_rule` / `promote_recurring` keep `next_due` in sync | `repositories/recurring.py` | ADR-0038 |
| `services.recurring.advance_next_due` pure helper | `services/recurring.py` | ADR-0038 |
| `services.recurring.promote_recurring` + `skip_and_advance` | `services/recurring.py` | ADR-0038 |
| `transactions.promoted_from_recurring_rule_id` + `promoted_from_recurring_date` | migration `0006`, `domain/transactions.py`, `repositories/transactions.py` | ADR-0038 |
| Routes: `POST /recurring/{id}/promote`, `POST /recurring/{id}/skip-next` | `web/routers/recurring.py` | ADR-0038 |
| Ledger Recurring row partial: columns + action buttons | `partials/recurring/_row.html`, `partials/ledger/_recurring_table.html` | ADR-0038, §3.9 |
| Planned log: drop virtual-union branch; narrow `PlannedView.kind` to `"persisted"` | `services/planned.py`, `web/routers/ledger.py` | ADR-0038 |
| New `services.upcoming.list_upcoming(window)` composing planned one-offs + recurring `next_due` | `services/upcoming.py` | ADR-0038, §3.9 Overview |
| Overview Upcoming fragment switches to the new service; row partial branches on `kind` | `web/routers/home.py`, `templates/home/_upcoming_list.html` | §3.9 Overview |
| Overview Upcoming header: group `+ Planned` + `+ Recurring` into a `.panel__add-group` cluster | `templates/home/_upcoming_panel.html` + stylesheet | §3.9 Overview |
| `services.income.next_anchor_date` replacing `services.planned.next_planned_for_category` | `services/income.py` | ADR-0038 |
| `services.budget.committed_in_window` + `MonthTotals.committed_minor` + template line | `services/budget.py`, `templates/budget/*`, `templates/home/_month_panel.html` | ADR-0039 |
| `data-reset-on-submit` scoped to form-only submit per ADR-0040 | `templates/base.html` scripts block | ADR-0040 |
| Account form: credit-limit `hidden` + `aria-hidden` + `disabled` applied on initial render when the toggle is off, inside the slide-over wrapper | `partials/accounts/_form.html` | F2.1 |
| Regression test: amount accepts `,` and `.` | `tests/integration/web/test_forms.py` | F1.1 |

## Task table

| ID | Task | Dep |
|---|---|---|
| T-116 | ADR-0038 + ADR-0039 + ADR-0040 + requirements + Phase 12 docs scaffolding (docs only) | — |
| T-117 | Migration + domain + repository: `recurring_rules.next_due` / `last_promoted_date`, `transactions.promoted_from_recurring_*` | T-116, ADR-0038 |
| T-118 | Recurring promotion service + routes (`promote_recurring`, `skip_and_advance`, `advance_next_due`) | T-117 |
| T-119 | Decouple planned log from recurring; narrow `PlannedView`; introduce `services.upcoming.list_upcoming` + `services.income.next_anchor_date` | T-117 |
| T-120 | Budget `committed_in_window` + `MonthTotals.committed_minor` + template surfaces | T-117, T-118, T-119 |
| T-121 | Overview Upcoming: switch to `services.upcoming.list_upcoming`; group `+ Planned` + `+ Recurring`; render kind-aware actions | T-119 |
| T-122 | Ledger Recurring row: `next_due` column + Promote / Override-next / Skip-next / Delete actions | T-118 |
| T-123 | Account form credit-limit initial-render bug: enforce the lockstep inside the slide-over on mount | T-116 |
| T-124 | Modal dismissal scope: `data-reset-on-submit` fires only on owning form submit (ADR-0040); regression test for amount `,` + `.` | T-116, ADR-0040 |

## Handoff invariants

- No change to the forecast line's output values on a frozen DB snapshot (ADR-0038 keeps `services.recurring.expand` for forecast).
- Backfill is one-shot and idempotent (re-running the migration script is a no-op).
- `services.planned.list_planned` continues to serve the Planned tab — scope narrows, signature unchanged for callers outside the Upcoming / Ledger paths.
- `MonthSummary.left_daily_spend_minor` arithmetic test from Phase 9 is updated to reflect the new `committed_minor` subtraction; previous rounding + anchor fallback branches stay pinned.
- All frontend-touching tasks (T-121, T-122, T-123, T-124) must run the `frontend-visual-audit` skill on the affected routes at 1440 / 1024 / 375 before marking done; findings referenced in the handoff.
