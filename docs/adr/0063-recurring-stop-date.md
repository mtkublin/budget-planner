# ADR-0063: Recurring Rules — User-Facing Stop Date

- **Status**: Accepted
- **Date**: 2026-10-30
- **Amends**: [ADR-0038](0038-recurring-standalone-lifecycle.md) (surfaces the existing `end_date` column as a first-class user-facing field)

## Context

`recurring_rules.end_date DATE NULL` has existed since migration `0002_core_schema.sql`:

- `generate_occurrences` clips the virtual-occurrence stream at `end_date` inclusive (`src/budget_planner/services/recurring.py:120`).
- `advance_next_due` returns `None` when the next step would exceed `end_date` (`src/budget_planner/services/recurring.py:295`).
- The promotion orchestrator deactivates the rule (`active=0`) when `advance_next_due` returns `None` (per ADR-0038 §Promotion flow, step 6c).
- `RecurringRule`, `NewRecurringRule`, and `PatchRecurringRule` all expose `end_date: date | None`.

Three things are missing:

1. **UI**: The create/edit form does not render an `end_date` input. Users have no way to set the stop date.
2. **Validation feedback**: The DB has a `CHECK (end_date IS NULL OR end_date >= start_date)` constraint, but the user-facing form has no inline error path. A bad input today raises a 500 (constraint violation) instead of a 422 with a field error.
3. **Pre-promotion termination**: `services.upcoming.list_upcoming` filters only on `active=True`. If `end_date` is set in the past but the rule has not yet been promoted (so no advancement has run), the rule still surfaces in the Upcoming list with a `next_due > end_date`. Same leak at `create_rule` time (`end_date` already past at insert).

The termination semantics inside the engine are correct — this ADR only surfaces them and closes the two leak paths.

## Decision

### F3.2a — Stop date (optional)

A recurring rule may carry an optional `end_date`:

- Optional. `NULL` means "no end".
- Must be `>= start_date` (DB-enforced; also validated at the form boundary with an inline field error, 422).
- Semantically **inclusive**: the last valid occurrence is the latest canonical date `<= end_date`.
- Setting `end_date` to a value `< today` (new rule) or `< next_due` (existing rule) terminates the rule immediately: the service layer flips `active = 0` within the same transaction as the create/update.
- The rule still deactivates on the next promotion when `advance_next_due` returns `None` — unchanged from ADR-0038.
- Forecast and Budget already respect `end_date` through `generate_occurrences`. No change required in those services.

### Behavioural edges

| Scenario | Behavior |
|---|---|
| Create with `end_date < start_date` | 422 inline error on the form field. |
| Create with `end_date < today` and valid vs. `start_date` | Rule inserted with `active=0`. The user has effectively created a historical record of a dead schedule — allowed; the row shows as "ended" in the Recurring tab. |
| Edit `end_date` to a date `< rule.next_due` | Rule flipped to `active=0` within the same transaction as the patch. Audit log records both the `end_date` change and the `active` flip. |
| Edit `end_date` to a date `>= rule.next_due` on a previously ended rule | Rule stays inactive. Re-activation is a separate operation not covered by this ADR (future work). |
| Override exists for an `occurrence_date > end_date` | Override is silently ignored by `generate_occurrences` (current behavior). No surfaced warning in v2 — rare and self-correcting. |
| Promote the last occurrence (`next_due == end_date`) | Promotion succeeds; `advance_next_due` returns `None`; rule deactivates. Already works. |
| Upcoming list contains a rule where `next_due > end_date` | `services.upcoming.list_upcoming` filters it out. Prevents stale rows between create/edit and the next promotion. |

### UI contract

**Form** (`partials/recurring/_form.html`):
- New `<input type="date" name="end_date">` placed next to Start.
- Label: "Stop (optional)".
- Helper copy: "Last occurrence on or before. Leave empty for no end."
- Field error slot adjacent, mirroring other form fields.

**Row** (`partials/recurring/_row.html`):
- When `end_date` set and in the future: subdued caption "ends YYYY-MM-DD".
- When rule is inactive **and** `end_date` is set and `<= today`: caption "ended YYYY-MM-DD" (replaces generic inactive copy).
- When `end_date` is unset: no caption (unchanged).

**Promote modal** (`partials/recurring/_promote_modal.html`):
- When `rule.next_due == rule.end_date`: footnote "Last occurrence — rule deactivates after promote."

### Non-goals

- Reactivation of ended rules (out of scope for v2; add if demand surfaces).
- Multi-stop (pause + resume) semantics.
- Grace-period rounding of `end_date` to cadence anchors — users specify an exact calendar date; the engine clips naturally.

## Consequences

- One net-new column rendering + 1 new form field; no schema change.
- Two new filter branches: `create_rule` edge (end_date already past) and `update_rule` edge (end_date < next_due) — both centralised in the router/service layer, not re-implemented in the repository.
- One new filter in `services.upcoming.list_upcoming`.
- Audit log unchanged in shape; the existing update_rule write naturally captures the `end_date` and `active` deltas.
- Forecast + Budget + Overview Upcoming automatically pick up the behaviour; no changes required there (verified against existing clip logic).

## Alternatives Considered

- **Deactivate on the next read of `upcoming` instead of filtering**: write path side-effect on read is a classic footgun. Rejected.
- **Enforce `end_date >= next_due` at save time**: too restrictive — users want to cancel a rule mid-schedule by setting a past stop date; our model handles this cleanly.
- **Add a separate `terminated_at` audit column**: redundant. The `audit_log` entry for the `active` flip already carries timestamp + prev/next JSON.
- **Allow `end_date < start_date` with semantics "no occurrences at all"**: pointlessly surprising; keep the existing DB CHECK and surface it in the form.
