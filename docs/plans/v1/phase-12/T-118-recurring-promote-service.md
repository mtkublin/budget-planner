# T-118 [S] Recurring promotion service + routes

> Depends on: T-117, [ADR-0038](../../../adr/0038-recurring-standalone-lifecycle.md). Blocks: T-120, T-122.

## Scope

Service + router. No template work (T-122 ships the markup).

### `services/recurring.py` additions

- `advance_next_due(cadence, from_date, end_date, day_of_month, month_of_year) -> dt.date | None` — pure function; wraps the stepping arithmetic currently inlined in `generate_occurrences`. Returns `None` when the next step would exceed `end_date`.
- `first_due_on_or_after(rule, today) -> dt.date` — pure; returns the earliest canonical occurrence `>= max(rule.start_date, today)`. Used by `repositories.recurring.create_rule` (via T-117) and by the migration backfill.
- `promote_recurring(conn, rule_id, edits: PromotionEdits) -> Transaction` — orchestrator, single DB transaction. Behaviour per ADR-0038 §Promotion flow:
  1. Load rule (incl. active + non-deleted guards; raises `RecurringNotFoundError`, `InactiveRecurringError`).
  2. `due_date = rule.next_due`.
  3. Lookup override for `(rule_id, due_date)`; `state=skipped` → `CannotPromoteSkippedError`; `state=overridden` → merge into defaults.
  4. Overlay explicit `edits` (shape mirrors `services.planned.PromotionEdits`).
  5. Reuse validation (factor `_validate_promotion` into a shared `services/_promotion.py` helper consumed by both planned and recurring paths; signature `_validate_promotion(conn, direction, account_id, dest_account_id, amount)`).
  6. In a single `with db_transaction(conn):`
     - Insert `transactions` row with `promoted_from_recurring_rule_id = rule_id`, `promoted_from_recurring_date = due_date`.
     - Compute `new_next_due = advance_next_due(...)`.
     - If `new_next_due is None`, call `recurring_repo.set_inactive(conn, rule_id)`; otherwise `recurring_repo.set_next_due(conn, rule_id, new_next_due, last_promoted_date=due_date)`.
     - Delete the matching override row (if any) via `recurring_repo.delete_override(conn, rule_id, due_date)`.
     - Write audit entries (txn create + rule update) — reuse `audit.write_audit`.
  7. Return the new `Transaction`.
- `skip_and_advance(conn, rule_id) -> dt.date | None` — upserts a `state=skipped` override for current `next_due`, advances `next_due` via `advance_next_due`, deletes the just-written skip override (its purpose is served by the advancement), updates `last_promoted_date=None` (skip is not a promotion). Returns the new `next_due` or `None`. Audit entry on the rule update only. Single DB transaction.

### `web/routers/recurring.py` additions

- `POST /recurring/{rule_id}/promote` — form fields: `operation_date` (optional, defaults to `next_due`), `amount` (optional, defaults to override/default), `description` (optional). Emits `HX-Trigger: ledger-stale, forecast-stale, budget-stale`. Returns the re-rendered recurring row partial (with the advanced `next_due`) on 200; returns the pre-filled modal partial with error state on 422.
- `GET /recurring/{rule_id}/promote` — form fragment (slide-over wrapper + prefilled payload) for the Promote button.
- `POST /recurring/{rule_id}/skip-next` — body-less. Emits `HX-Trigger: ledger-stale, forecast-stale, budget-stale`. Returns the re-rendered row partial.

### `services/planned.py` cleanup

Refactor `promote_to_actual` to call the shared `_validate_promotion` so the two promotion paths stay in step. No behavioural change for planned promotion.

### Tests

- `tests/unit/services/test_recurring_service.py`:
  - `advance_next_due` — monthly / quarterly / yearly cadences; end-of-month clamp (31 → 28/29/30); Feb-29 anchor across leap boundary; `end_date` boundary returning `None`.
  - `first_due_on_or_after` — rule starts in future (returns `start_date`); rule started in past (returns next upcoming).
  - `promote_recurring` — happy path advances `next_due` + stamps provenance; skipped override blocks; overridden override merges; `end_date` reached deactivates rule; override row deleted on promote; audit entries written for both mutations.
  - `skip_and_advance` — advances past the skip; leaves `last_promoted_date` unchanged.
- `tests/integration/web/test_recurring_routes.py`:
  - `POST /recurring/{id}/promote` with no edits — DB has one new transaction, rule's `next_due` advanced, HX-Trigger headers present.
  - `POST /recurring/{id}/skip-next` — rule's `next_due` advanced, no new transaction.
  - 422 paths: promote with amount=0; promote with cross-currency transit (reusing shared validator).
  - Fresh-DB regression: promoting a rule whose `next_due` was backfilled by the T-117 migration lands a transaction dated at the backfilled `next_due`.

## Acceptance

- Tests above pass. Coverage ≥ 90%.
- `mypy --strict` clean.
- `just ci` green.
- No change to `services.planned.list_planned` observable output on a frozen DB (that lands in T-119).

## Non-goals

- Dropping virtual-union from `list_planned` (T-119).
- Row partial / template work (T-122).
- Budget `committed_minor` wiring (T-120).
