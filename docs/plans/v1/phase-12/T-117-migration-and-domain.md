# T-117 [S] Migration + domain + repository for `recurring_rules.next_due`

> Depends on: T-116, [ADR-0038](../../../adr/0038-recurring-standalone-lifecycle.md). Blocks: T-118, T-119, T-120, T-122.

## Scope

Additive schema migration + domain + repository changes. No service-level promotion logic yet (that lands in T-118).

### Migration `migrations/0006_add_recurring_next_due.sql`

- `ALTER TABLE recurring_rules ADD COLUMN next_due DATE` (nullable at first for backfill).
- `ALTER TABLE recurring_rules ADD COLUMN last_promoted_date DATE` (nullable; stays nullable).
- `ALTER TABLE transactions ADD COLUMN promoted_from_recurring_rule_id INTEGER REFERENCES recurring_rules (id) DEFERRABLE INITIALLY DEFERRED`.
- `ALTER TABLE transactions ADD COLUMN promoted_from_recurring_date DATE`.
- `CREATE INDEX ix_transactions_promoted_from_recurring ON transactions (promoted_from_recurring_rule_id, promoted_from_recurring_date)`.
- Backfill `next_due` via a Python-driven step in `db/migrate.py` (post-SQL hook): for each live rule, compute the earliest canonical occurrence that is on-or-after `max(start_date, today_utc)` with `end_date` honoured; if the generator yields nothing (rule end has passed), set `active=0` and leave `next_due = start_date` (sentinel for inactive rules — the service ignores inactive rules anyway).
- SQLite 12-step `ALTER TABLE ... RECREATE` migration to flip `next_due` to `NOT NULL` once backfill is done. Keep inside the same migration file so partial-apply states are impossible.

### Domain changes

- `domain/recurring.py`:
  - `RecurringRule` gains `next_due: dt.date` + `last_promoted_date: dt.date | None`.
  - `NewRecurringRule` **does not** expose `next_due` — the repository computes it on create via the generator.
  - `PatchRecurringRule` optionally accepts `next_due` for admin fixes, defaulting to `_UNCHANGED` sentinel.
- `domain/transactions.py`:
  - `Transaction` gains `promoted_from_recurring_rule_id: int | None` + `promoted_from_recurring_date: dt.date | None`.
  - `NewTransaction` gains the same two fields with `None` defaults.
  - Service-layer invariant (not DB CHECK): `(promoted_from_planned_id IS NULL) OR (promoted_from_recurring_rule_id IS NULL)`.

### Repository changes

- `repositories/recurring.py`:
  - `create_rule` computes initial `next_due` by calling `services.recurring.first_due_on_or_after(rule, today)` (new pure helper landing in T-118) — until T-118, use an inline port of the same logic so T-117 is self-contained; T-118 refactors to call the final helper.
  - `list_rules(active_only=…)` SELECTs the new columns.
  - New `set_next_due(conn, rule_id, next_due, last_promoted_date)` + `set_inactive(conn, rule_id)` repository helpers for use by T-118 — kept thin and audit-free (service orchestrates audit).
- `repositories/transactions.py`:
  - `create` accepts the two new fields.
  - `list_filtered` surfaces them.

### Tests

- `tests/integration/db/test_migrations.py` — new case asserts `next_due NOT NULL` constraint + the two new transactions columns post-apply.
- `tests/unit/repositories/test_recurring_repo.py` — `create_rule` populates `next_due`; `list_rules` returns it; `set_next_due` round-trips.
- `tests/unit/repositories/test_transactions_repo.py` — `create` round-trips the recurring provenance fields.
- `tests/integration/db/test_seed.py` — assert seed data (demo accounts, categories, FX cache) still applies; no demo recurring rules are seeded (none exist today).

## Acceptance

- `just migrate` on a fresh DB succeeds; `just migrate` on an existing dev DB is idempotent.
- All existing recurring tests pass unchanged (no behavioural service shift until T-118).
- `mypy --strict` clean.
- Coverage stays ≥ 90%.

## Non-goals

- Promotion / advancement service (T-118).
- Any router changes (T-118, T-122).
- Template changes (T-121, T-122).
