# T-041 — Integration tests

> Phase 4 — Testing. Status: pending.

## Purpose

Exercise the full stack from service → repository → SQLite for the cross-layer flows called out in Phase 2/3. Integration tests prove that transactions, audit rows, soft-delete filters, and FX caching behave correctly together under a real SQLite file. They also cover the four explicit flows: promotion, reconciliation, FX fetch with mocked HTTP, and planned-log union (persistent + virtual).

## Inputs / prerequisites

- Upstream code:
  - [`src/budget_planner/services/`](../../../src/budget_planner/services/) — all Phase 2 modules.
  - [`src/budget_planner/repositories/`](../../../src/budget_planner/repositories/) — all Phase 1 modules.
  - [`src/budget_planner/db/migrate.py`](../../../src/budget_planner/db/migrate.py) — runs numbered SQL migrations.
- ADRs: [ADR-0011](../../adr/0011-derived-balance-snapshots-reconciliation.md), [ADR-0012](../../adr/0012-planned-manual-promotion.md), [ADR-0013](../../adr/0013-recurring-virtual-occurrences-and-overrides.md), [ADR-0014](../../adr/0014-budget-flat-no-rollover-three-tier.md), [ADR-0015](../../adr/0015-forecast-deterministic-live-htmx.md), [ADR-0019](../../adr/0019-soft-delete-and-audit-log.md), [ADR-0021](../../adr/0021-functional-style-no-oop.md).
- Testing stack already provisioned in T-001: `pytest`, `pytest-cov`, `pytest-asyncio`.
- Fixtures from T-040: `tests/conftest.py`, `tests/fixtures/seed.py`, `tests/fixtures/http.py`.

## Deliverables

Test files under `tests/integration/`:

```
tests/integration/
├── test_migrations_round_trip.py
├── test_audit_log_coverage.py
├── test_promotion_flow.py
├── test_reconciliation_flow.py
├── test_fx_fetch_flow.py
├── test_planned_log_union.py
├── test_recurring_overrides_flow.py
├── test_budget_resolution_flow.py
└── test_forecast_flow.py
```

Shared fixtures reused from T-040:

- `tests/conftest.py` — `tmp_db_path`, `conn`, `migrated_conn`, `seeded_conn`, `fx_http_mock` / `FxFetcher` double.
- `tests/fixtures/seed.py` — builders.

No new config diffs beyond the markers already added in T-040. Integration tests opt in via `@pytest.mark.integration`.

## Scope & test matrix

| Area | Test file | Test names | Asserts |
|------|-----------|------------|---------|
| Migrations | `test_migrations_round_trip.py` | `migrate_from_empty_db_creates_all_tables_and_indexes`, `migrate_is_idempotent_when_run_twice`, `seed_migration_inserts_system_rows` | Table list, index list, seed presence |
| Audit coverage | `test_audit_log_coverage.py` | `every_mutating_repo_fn_writes_exactly_one_audit_row`, `update_captures_prev_and_new_json`, `soft_delete_logs_delete_operation`, `undelete_logs_undelete_operation` | Parametrised across every (`entity_type`, mutation) pair |
| Promotion | `test_promotion_flow.py` | `promote_one_off_planned_inserts_txn_and_stamps_promoted_to_txn_id`, `promote_applies_user_edits_to_amount_and_date`, `promote_writes_audit_rows_on_both_planned_and_transaction`, `promote_is_atomic_rollback_leaves_no_partial_state` | Dual-table write in one txn; audit on both; rollback on service error |
| Reconciliation | `test_reconciliation_flow.py` | `reconcile_computes_delta_from_derived_balance`, `reconcile_inserts_adjustment_under_reconciliation_category`, `derived_balance_after_reconcile_matches_actual`, `reconcile_is_noop_when_delta_zero`, `reconcile_writes_audit_row` | Before/after derived balance per ADR-0011 |
| FX fetch | `test_fx_fetch_flow.py` | `fx_cache_miss_fetches_persists_and_returns`, `fx_cache_hit_short_circuits_without_http`, `fx_api_error_falls_back_to_last_known_rate_and_logs_warning`, `fx_same_currency_returns_one_without_io`, `convert_historical_uses_rate_on_transaction_date` | HTTP mocked; cache row written on miss |
| Planned log union | `test_planned_log_union.py` | `list_planned_merges_rows_and_virtual_occurrences_in_date_order`, `list_planned_respects_filter_window`, `list_planned_excludes_promoted_rows`, `list_planned_applies_overrides_to_virtual_occurrences`, `list_planned_excludes_soft_deleted_rules_and_rows` | Union correctness, window boundaries |
| Recurring overrides | `test_recurring_overrides_flow.py` | `skipped_override_removes_occurrence_from_list`, `overridden_override_mutates_amount_description_or_date`, `multi_month_skip_removes_each_targeted_occurrence`, `override_delete_restores_default_occurrence` | ADR-0013 state machine end-to-end |
| Budget resolution | `test_budget_resolution_flow.py` | `one_off_override_takes_precedence_in_target_month_only`, `recurring_override_applies_each_year_for_that_month`, `default_applies_when_no_override`, `month_summary_integrates_actual_transactions_only` | Three-tier coalesce persists across years |
| Forecast | `test_forecast_flow.py` | `forecast_includes_planned_rows_and_virtual_occurrences`, `forecast_converts_cross_currency_accounts_to_base`, `forecast_is_stable_when_called_twice_with_same_inputs`, `editing_a_planned_row_changes_forecast_output` | Determinism, FX conversion, mutation visibility |

## Fixtures / seed data

Shared seed (`seeded_conn` + builders) provides:

- 1 user row.
- 2 system categories (`Transit`, `Reconciliation`).

Each integration test opts in to a richer scenario via a local helper (not a global fixture) built on top of the T-040 builders:

- Minimum per flow (illustrative):
  - **Promotion**: 1 account (PLN), 1 category (Groceries, expense), 1 planned row.
  - **Reconciliation**: 1 account with opening_balance=100_00, 2 transactions totalling -40_00 → derived=60_00; user asserts actual=70_00 → delta=+10_00.
  - **FX fetch**: 1 account (EUR), FX cache seeded for 2026-01-01 (EUR→PLN=4.3); test adds a 2026-02-01 fetch via mock.
  - **Planned-log union**: 1 recurring rule (monthly, starts 2026-01-15, amount=50_00), 1 one-off planned on 2026-01-20; query window 2026-01-01..2026-03-31.
  - **Overrides**: 1 recurring rule + 2 override rows (`skipped` on 2026-02-15, `overridden` with amount=99_00 on 2026-03-15).
  - **Budget resolution**: 1 category + default=100_00, recurring override for month=12 amount=200_00, one-off override for (2026, 12) amount=300_00.
  - **Forecast**: 2 accounts (PLN, EUR), 1 recurring rule, horizon=90 days, FX rate seeded.

Temp DB handling:

- One DB file per test file via `tmp_path` → `tmp_db_path` fixture.
- `pytest-xdist` safe: no shared file paths, no module-level state. Confirmed by `pytest -n auto tests/integration`.

## Validation / acceptance

Command:

```sh
pytest tests/integration -m integration -q
```

Full gate (contributes to the 90% coverage number in T-043):

```sh
pytest --cov=src/budget_planner --cov-branch --cov-fail-under=90 tests/unit tests/integration
```

**Audit assertions are mandatory.** Every mutation path in these tests ends with:

```python
rows = conn.execute("SELECT entity_type, entity_id, operation FROM audit_log").fetchall()
assert (expected_entity_type, expected_entity_id, expected_operation) in rows
```

Promotion specifically asserts audit rows for **both** the `planned_transactions.update` and the `transactions.create`.

## Risks & gotchas

- SQLite file contention under parallel runs — tests must receive the DB via `tmp_path` fixtures only; no `/tmp/budget.db` style constants.
- HTMX fragment assertions belong in T-042/E2E; integration tests should **not** go through the FastAPI `TestClient` (that is the next layer).
- `respx` or Protocol-based HTTP doubles only; no real network. Fail loudly if `httpx` sees a non-mocked URL (`respx`'s `assert_all_called=True`).
- Clock — freeze with `freezegun`/`time-machine` for FX and forecast tests to keep `latest rate` deterministic.
- Coverage of `src/budget_planner/web/` is not the target of this file; routers get coverage in T-042 and `TestClient`-level tests under `tests/integration/web/` if introduced later.
- `foreign_keys=ON` must be set on every new connection — enforce in the `conn` fixture, not in test bodies.

## Handoff notes

Phase 5 polish tasks assume:

- Any new mutation written during polish must slot into the existing audit-coverage parametrised test — if it doesn't, Phase 5 adds the parameter.
- The temp-DB fixture pattern is the one true path; polish must not introduce an in-memory `":memory:"` shortcut because migrations rely on file-backed `ATTACH` semantics.
- FX cache semantics are frozen here; Phase 5 cannot change the fallback contract without a new ADR superseding ADR-0006.
