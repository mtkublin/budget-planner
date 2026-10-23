# T-040 — Unit tests

> Phase 4 — Testing. Status: pending.

## Purpose

Lock down the pure-function surface of Phase 1 (repositories) and Phase 2 (services) with fast, isolated unit tests. These tests carry the bulk of coverage toward the 90% gate (T-043) and give downstream phases a stable regression net. Mocks only at the HTTP boundary; everything else exercises real pure code.

## Inputs / prerequisites

- Upstream code under test:
  - Repositories: [`src/budget_planner/repositories/`](../../../src/budget_planner/repositories/) — modules per T-013 (`transactions.py`, `accounts.py`, `categories.py`, `planned.py`, `recurring.py`, `budgets.py`, `snapshots.py`, `fx.py`).
  - Services: [`src/budget_planner/services/`](../../../src/budget_planner/services/) — modules per T-020..T-028 (`fx.py`, `balance.py`, `recurring.py`, `planned.py`, `budget.py`, `forecast.py`, `reconcile.py`, `export.py`, `audit.py`).
  - Domain: [`src/budget_planner/domain/`](../../../src/budget_planner/domain/) — frozen dataclasses + money helpers (T-014).
- ADRs: [ADR-0008](../../adr/0008-transaction-amount-sign-and-direction.md), [ADR-0011](../../adr/0011-derived-balance-snapshots-reconciliation.md), [ADR-0013](../../adr/0013-recurring-virtual-occurrences-and-overrides.md), [ADR-0014](../../adr/0014-budget-flat-no-rollover-three-tier.md), [ADR-0015](../../adr/0015-forecast-deterministic-live-htmx.md), [ADR-0019](../../adr/0019-soft-delete-and-audit-log.md), [ADR-0021](../../adr/0021-functional-style-no-oop.md).
- Testing stack already provisioned in T-001: `pytest`, `pytest-cov`, `pytest-asyncio`, (optional `playwright`), `httpx`, `freezegun` or `time-machine` (choose one; freezegun preferred as it is in widest Python 3.12 use — add to dev deps in T-001 scope if missing — if not, use `monkeypatch` + a `clock()` helper injected into services).

## Deliverables

Test files under `tests/unit/`:

```
tests/unit/
├── domain/
│   ├── test_money.py                 # to_minor_units / from_minor_units / format
│   ├── test_enums.py                 # Direction, Cadence invariants
│   └── test_dtos.py                  # frozen-ness, equality, validation
├── repositories/
│   ├── test_accounts_repo.py
│   ├── test_categories_repo.py
│   ├── test_transactions_repo.py
│   ├── test_planned_repo.py
│   ├── test_recurring_repo.py
│   ├── test_budgets_repo.py
│   ├── test_snapshots_repo.py
│   └── test_fx_repo.py
└── services/
    ├── test_audit_service.py
    ├── test_fx_service.py
    ├── test_balance_service.py
    ├── test_recurring_service.py
    ├── test_planned_service.py
    ├── test_budget_service.py
    ├── test_forecast_service.py
    ├── test_reconcile_service.py
    └── test_export_service.py
```

Shared fixtures:

- `tests/conftest.py` — `tmp_db_path`, `conn`, `migrated_conn`.
- `tests/fixtures/seed.py` — `seeded_conn`, builder helpers (`make_account`, `make_category`, `make_transaction`, `make_rule`, `make_fx_rate`).
- `tests/fixtures/http.py` — `fx_http_mock` (patches `httpx.Client.get` or injects a `FxFetcher` Protocol test double).

Config diffs in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "-ra --strict-markers --strict-config"
testpaths = ["tests"]
markers = [
  "unit: pure-function tests, no I/O beyond temp SQLite",
  "integration: cross-layer tests against a temp DB",
  "e2e: smoke flows through the FastAPI app",
  "slow: opt-in, not run by default",
]

[tool.coverage.run]
source = ["src/budget_planner"]
branch = true
omit = [
  "src/budget_planner/web/templates/*",
  "src/budget_planner/__main__.py",
]

[tool.coverage.report]
exclude_lines = [
  "pragma: no cover",
  "raise NotImplementedError",
  "if TYPE_CHECKING:",
]
```

## Scope & test matrix

### Domain

| Module | Test file | Key test names | Asserts |
|--------|-----------|----------------|---------|
| `domain/money.py` | `test_money.py` | `to_minor_units_rounds_half_even`, `from_minor_units_restores_decimal`, `format_respects_currency_decimals_for_jpy_and_pln` | PLN=2dp, JPY=0dp, round-trip invariant |
| `domain/enums.py` | `test_enums.py` | `direction_contains_only_four_values`, `cadence_contains_only_three_values` | Enum shape; reject unknown string |
| `domain/dtos.py` | `test_dtos.py` | `new_transaction_is_frozen`, `transaction_equality_is_structural`, `patch_transaction_allows_partial_fields` | `dataclasses.FrozenInstanceError` on mutate; eq by value |

### Repositories

Each repo test file follows the same shape: create → read → update → soft-delete → list filters → audit row written.

| Module | Test file | Key test names | Asserts |
|--------|-----------|----------------|---------|
| `repositories/accounts.py` | `test_accounts_repo.py` | `create_persists_and_returns_dto`, `name_unique_constraint_raises`, `soft_delete_hides_from_default_list`, `include_deleted_returns_tombstone`, `audit_row_written_on_create_update_delete` | Round-trip, unique constraint, soft-delete filter, audit |
| `repositories/categories.py` | `test_categories_repo.py` | `create_persists`, `direction_check_constraint_rejects_bad_value`, `system_categories_cannot_be_hard_deleted_via_repo` | CHECK constraint fires; system cats guarded at service layer, repo call still writes audit |
| `repositories/transactions.py` | `test_transactions_repo.py` | `create_with_dest_account_id_persists_transit`, `list_filtered_by_date_range`, `list_filtered_by_category`, `list_filtered_by_amount_range`, `list_filtered_by_description_substring`, `soft_delete_filters_from_default_list`, `audit_includes_prev_and_new_json` | Filters compose; `prev_json` null on create, populated on update |
| `repositories/planned.py` | `test_planned_repo.py` | `create_one_off_planned_persists`, `promote_sets_promoted_to_txn_id`, `soft_delete_hides` | Promotion stamps id; audit entries on both insert and update |
| `repositories/recurring.py` | `test_recurring_repo.py` | `create_rule_persists_cadence`, `deactivate_sets_active_false`, `override_upserts_by_rule_and_date`, `list_active_excludes_deactivated` | Overrides keyed on `(rule_id, occurrence_date)` |
| `repositories/budgets.py` | `test_budgets_repo.py` | `defaults_upsert_by_category`, `recurring_override_unique_per_category_month`, `one_off_unique_per_category_year_month` | UNIQUE constraints; upsert semantics |
| `repositories/snapshots.py` | `test_snapshots_repo.py` | `insert_snapshot_persists_with_note`, `list_snapshots_by_account_ordered_desc` | Pure audit record; derived balance untouched |
| `repositories/fx.py` | `test_fx_repo.py` | `insert_rate_persists`, `unique_date_from_to_constraint`, `latest_rate_for_pair_returns_most_recent_date` | UNIQUE(date, from_ccy, to_ccy) |

### Services

| Module | Test file | Key test names | Asserts |
|--------|-----------|----------------|---------|
| `services/audit.py` | `test_audit_service.py` | `write_audit_inserts_row_with_json_payloads`, `write_audit_participates_in_outer_transaction`, `operation_values_restricted_to_crud_undelete` | Row shape; same connection txn |
| `services/fx.py` | `test_fx_service.py` | `get_rate_returns_one_when_same_currency`, `get_rate_hits_cache_without_http`, `get_rate_fetches_on_miss_and_persists`, `get_rate_falls_back_to_last_known_on_api_error`, `convert_uses_historical_rate_for_date` | Mock `httpx.Client.get`; cache hit path makes zero HTTP calls; fallback emits warning |
| `services/balance.py` | `test_balance_service.py` | `derive_balance_sums_opening_plus_income_minus_expense`, `derive_balance_handles_transit_as_minus_source_plus_dest`, `derive_balance_treats_adjustment_as_signed`, `derive_balance_respects_as_of_date`, `derive_balance_ignores_soft_deleted` | Signed-amount rules per ADR-0008 + ADR-0011 |
| `services/recurring.py` | `test_recurring_service.py` | `monthly_generator_steps_by_calendar_month`, `monthly_generator_clips_to_end_of_month_for_short_months`, `quarterly_generator_steps_every_three_months`, `yearly_generator_handles_feb_29_in_non_leap_year`, `generator_clips_by_rule_end_date_and_query_range`, `apply_overrides_drops_skipped`, `apply_overrides_mutates_overridden_fields`, `apply_overrides_preserves_defaults_for_non_overridden` | Full override state machine per ADR-0013; year-boundary wrap |
| `services/planned.py` | `test_planned_service.py` | `list_planned_unions_rows_and_virtual_occurrences`, `list_planned_respects_filter_window`, `promote_to_actual_inserts_transaction_and_stamps_planned`, `promote_to_actual_applies_edits_to_amount_and_date` | Union is sorted by `operation_date`; promotion is atomic (one txn) |
| `services/budget.py` | `test_budget_service.py` | `resolve_budget_prefers_one_off_over_recurring`, `resolve_budget_prefers_recurring_over_default`, `resolve_budget_returns_none_when_no_tier_matches`, `month_summary_computes_spent_from_actual_txns_only`, `month_summary_includes_avg_this_year_and_delta_vs_prev_month` | Three-tier null coalescing per ADR-0014 |
| `services/forecast.py` | `test_forecast_service.py` | `forecast_zero_horizon_returns_current_balance`, `forecast_projects_planned_rows`, `forecast_projects_virtual_recurring_occurrences`, `forecast_converts_to_base_currency_with_latest_fx`, `forecast_is_deterministic_same_inputs_same_output`, `forecast_ignores_soft_deleted_rows` | Pure fn; same input → same output per ADR-0015 |
| `services/reconcile.py` | `test_reconcile_service.py` | `reconcile_computes_signed_delta`, `reconcile_inserts_adjustment_transaction_under_reconciliation_category`, `reconcile_description_includes_date`, `reconcile_is_noop_when_delta_zero` | Adjustment direction, signed amount per ADR-0011 |
| `services/export.py` | `test_export_service.py` | `export_csv_header_matches_record_shape`, `export_csv_rfc4180_quoted_strings_with_commas`, `export_parquet_round_trips_via_pyarrow`, `export_empty_records_returns_header_only_bytes` | Byte-level; `pandas.read_parquet` round-trip |

## Fixtures / seed data

- Per-test SQLite: `tmp_db_path` fixture returns `tmp_path / f"budget-{uuid4().hex}.db"` → unique per worker, xdist-safe.
- `conn` fixture opens the DB with `PRAGMA foreign_keys=ON`, yields, closes.
- `migrated_conn` applies all migrations in `migrations/` on top of `conn`.
- `seeded_conn` adds the system seed (user id=1, Transit, Reconciliation categories). No sample accounts/transactions — tests opt in via builders.
- Builders (`tests/fixtures/seed.py`) accept keyword args, apply sane defaults, call the real repository functions so audit rows exist:
  - `make_account(conn, *, name="Checking", currency="PLN", opening_balance=0)`
  - `make_category(conn, *, name="Groceries", direction=Direction.expense)`
  - `make_transaction(conn, *, account_id, category_id, amount=1000, operation_date=date(2026,1,1), description="")`
  - `make_rule(conn, *, cadence=Cadence.monthly, start_date=date(2026,1,1), amount=10000, ...)`
  - `make_fx_rate(conn, *, date, from_ccy, to_ccy, rate)`
- HTTP: `fx_http_mock` fixture (yields a `respx` router) OR a `FxFetcher` Protocol injected into `fx.get_rate` — pick the Protocol path (keeps the pure-fn boundary clean and avoids a new dep).

## Validation / acceptance

Command:

```sh
pytest tests/unit -m unit -q
```

Full gate:

```sh
pytest --cov=src/budget_planner --cov-branch --cov-fail-under=90 tests/unit tests/integration
```

- Every repo mutation test asserts an audit row with correct `entity_type`, `entity_id`, `operation`, and non-null `new_json`.
- Every soft-delete test confirms the row disappears from the default list and reappears with `include_deleted=True`.
- Property-style tests for `derive_balance` and `resolve_budget` recommended but not required.
- No test touches the network. `fx_http_mock` or Protocol injection is mandatory in `test_fx_service.py`.

## Risks & gotchas

- SQLite file contention under `pytest-xdist` — always derive DB path from `tmp_path`, never hardcode.
- Floating-point drift — all amounts are integer minor units; forbid `float` in assertions on money.
- Date boundaries — recurring tests must include Feb-29 in non-leap years and month-end clipping (Jan 31 → Feb 28).
- Timezone — `created_at`/`updated_at` are UTC per ADR-0007. Freeze clock at UTC in tests; convert only when asserting user-facing display.
- Audit `prev_json` is `NULL` on `create` and the previous row on `update` — assert explicitly.
- Don't test Jinja templates in unit layer — coverage is scoped to `src/budget_planner` and omits templates.

## Handoff notes

Phase 5 (T-050..T-053) assumes:

- The pure business logic is pinned by this suite; polish changes only template + CSS without regressing semantics.
- Any new service function introduced in Phase 5 ships with a unit test file next to the existing ones.
- Builders in `tests/fixtures/seed.py` are the sanctioned way to construct test data — do not inline `INSERT` SQL in tests.
