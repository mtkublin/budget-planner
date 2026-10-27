# T-122 [P] Ledger Recurring row: Promote / Override-next / Skip-next / Delete + `next_due` column

> Depends on: T-118. Parallel-safe with T-121, T-123, T-124.

## Scope

Ledger Recurring tab row partial + supporting modal partials. No new service work (T-118 shipped the service + routes).

### `partials/recurring/_row.html`

Columns, in order:

| Col | Content |
|---|---|
| Cadence | `rule.cadence.value \| capitalize` |
| Next due | `rule.next_due \| date_fmt` — rendered **bold** when `override_present` (visual signal that the next occurrence has a per-row tweak). |
| Account | `account.name` |
| Category | `category.name` |
| Amount | `rule.default_amount \| money(currency)` — rendered **italic** when override overrides the amount for `next_due`. |
| Active | `Yes` / `No` |
| Actions | **Promote**, **Override next…**, **Skip next**, **Edit**, **Delete** |

Action semantics:

- **Promote** — `hx-get="/recurring/{{ rule.id }}/promote"` → `#modal-root`. Opens the Promote modal (`partials/recurring/_promote_modal.html`, new) pre-filled from the rule defaults + override on `next_due`; user may tweak amount / date / description. Submit `POST /recurring/{{ rule.id }}/promote` → emits `HX-Trigger: ledger-stale, forecast-stale, budget-stale`.
- **Override next…** — `hx-get="/recurring/{{ rule.id }}/overrides/new?occurrence_date={{ rule.next_due }}"` → `#modal-root`. Reuses the existing override form; `occurrence_date` is readonly-pre-filled to `rule.next_due`. Posting to `POST /recurring/{{ rule.id }}/overrides` writes/updates the override; the row re-renders with the override indicators.
- **Skip next** — `hx-post="/recurring/{{ rule.id }}/skip-next" hx-confirm="Skip {{ rule.next_due }}?"` → `outerHTML` swap of the row. On success the row shows the newly advanced `next_due`.
- **Edit** — unchanged; opens the rule edit slide-over.
- **Delete** — behavioural same as today's "Deactivate" (soft delete via `active=0`). Button label changes from "Deactivate" to **"Delete"** to match the Planned/Actual Delete affordance; `hx-confirm="Delete this recurring rule? Past promotions are kept."`

### New partial: `partials/recurring/_promote_modal.html`

- Slide-over wrapper around a `<form hx-post="/recurring/{rule_id}/promote" data-reset-on-submit>` carrying:
  - `operation_date` (date input, default = `next_due`).
  - `amount` (digit-only `data-numeric` input, default = effective override amount or `rule.default_amount`).
  - `description` (text, default = effective description).
  - A read-only banner at the top: `"Next occurrence: {{ next_due }}" + conditional "(override applied)"`.
  - Submit button + Cancel (closes the slide-over without posting).

### `partials/ledger/_recurring_table.html` (or its template-level consumer)

- Add the `Next due` column header; drop `Start date` (migrated into Edit).
- `hx-trigger="ledger-stale from:body"` already in place from T-114; no change beyond the row partial.

### Tests

- `tests/integration/web/test_recurring.py`:
  - Row renders with `next_due` column populated from DB (not `start_date`).
  - Promote button opens the modal; the modal shows the override banner when an override exists on `next_due`.
  - `POST /recurring/{id}/promote` creates a txn + advances the row; HX-Trigger headers present.
  - Skip-next advances the row without creating a txn.
  - Delete action soft-deletes (sets `active=0`).
- Regression: `tests/integration/web/test_ledger.py` — "`#ledger-table` listens for `ledger-stale`" test still passes; the row-level actions do not break the shared refresh contract.

### `frontend-visual-audit`

- `/ledger?view=recurring` at 1440 / 1024 / 375. Refresh the baseline. Verify the five actions wrap sensibly on mobile.

## Acceptance

- All actions reachable from the Recurring tab; promote lands a transaction visible on the Actual tab after refresh.
- `next_due` column no longer drifts (uses `rule.next_due`, not `start_date`).
- `just ci` + visual sweep green.

## Non-goals

- Overview-side changes (T-121).
- Any schema changes (T-117).
