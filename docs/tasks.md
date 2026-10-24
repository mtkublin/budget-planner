# Budget Planner — Implementation Tasks

> Each task is scoped to be picked up by a subsequent agent (or human) with minimal cross-coordination. Dependencies noted inline. Tasks are grouped by phase; within a phase, parallel-safe tasks are marked `[P]`.
>
> Acceptance = passing tests + `just ci` green + relevant ADR referenced.

Legend:
- `[P]` = parallel-safe within its phase.
- `[S]` = sequential, must complete before next in phase.
- `→ T-xxx` = depends on task.

---

## Phase 0 — Repository Bootstrap

### ✅ T-001 [S] Repository scaffolding
- Initialize `pyproject.toml` with `uv` (Python 3.12).
- Dependencies: `fastapi`, `uvicorn[standard]`, `jinja2`, `pydantic`, `pydantic-settings`, `python-multipart`, `plotly`, `pandas` (for parquet export), `pyarrow`, `httpx` (FX fetch), `python-dateutil`.
- Dev dependencies: `ruff`, `mypy`, `pytest`, `pytest-cov`, `pytest-asyncio`, `playwright` (optional), `sqlfluff`, `djlint`, `bandit`, `detect-secrets`, `pre-commit`.
- Create directory skeleton:
  ```
  src/budget_planner/
    __init__.py
    config.py
    db/
    domain/
    services/
    repositories/
    web/
      routers/
      templates/
      static/
    adapters/
      fx/
      export/
  tests/
    unit/
    integration/
    e2e/
  migrations/
  docs/
  ```
- Reference: ADR-0002, ADR-0004.

### ✅ T-002 [S] Justfile + CI → T-001
- `justfile` with: `dev`, `test`, `lint`, `format`, `typecheck`, `ci`, `db-reset`, `seed`, `migrate`.
- `.github/workflows/ci.yml` running `just ci` on push/PR on `ubuntu-latest` + Python 3.12.
- Coverage artifact uploaded.
- Reference: ADR-0019, ADR-0021.

### ✅ T-003 [S] Pre-commit stack → T-001
- `.pre-commit-config.yaml` with: `ruff`, `ruff-format`, `mypy`, `sqlfluff`, `djlint`, `bandit`, `detect-secrets`, standard stdlib hooks.
- `pyproject.toml` configs for ruff, mypy (strict), coverage threshold (90%).
- `just install-hooks` recipe.
- Reference: ADR-0020.

### ✅ T-004 [S] Config module → T-001
- `src/budget_planner/config.py` using `pydantic-settings`.
- Fields: `database_url`, `base_currency` (default `PLN`), `display_timezone` (default `Europe/Warsaw`), `host` (`127.0.0.1`), `port` (`8000`), `fx_api_url`.
- `.env.example` committed; `.env` gitignored.

---

## Phase 1 — Data Layer

### ✅ T-010 [S] Migration framework → T-004
- Pick lightweight migration tool: `yoyo-migrations` (SQL-first, simple) or hand-rolled numbered `.sql` files + runner.
- **Decision**: hand-rolled numbered `.sql` files in `migrations/`; runner in `src/budget_planner/db/migrate.py`.
- `just migrate` applies all pending migrations.

### ✅ T-011 [S] Core schema migration → T-010

Tables:
- `users(id, name, created_at)` — single seed row for v1.
- `accounts(id, user_id, name UNIQUE, type, currency, opening_balance, created_at, updated_at, deleted_at)`.
- `categories(id, user_id, name UNIQUE, direction CHECK IN ('income','expense','transit','adjustment'), created_at, updated_at, deleted_at)`.
- `transactions(id, user_id, operation_date, category_id, account_id, dest_account_id NULLABLE, amount, description, promoted_from_planned_id NULLABLE, created_at, updated_at, deleted_at)`.
- `planned_transactions(id, user_id, operation_date, category_id, account_id, dest_account_id NULLABLE, amount, description, recurring_rule_id NULLABLE, occurrence_date NULLABLE, promoted_to_txn_id NULLABLE, created_at, updated_at, deleted_at)`.
- `recurring_rules(id, user_id, cadence CHECK IN ('monthly','quarterly','yearly'), start_date, end_date NULLABLE, category_id, account_id, dest_account_id NULLABLE, default_amount, default_description, day_of_month NULLABLE, month_of_year NULLABLE, active, created_at, updated_at, deleted_at)`.
- `recurring_rule_overrides(id, rule_id, occurrence_date, state CHECK IN ('skipped','overridden'), amount_override NULLABLE, description_override NULLABLE, date_override NULLABLE, created_at)`.
- `budget_defaults(id, user_id, category_id UNIQUE, amount)`.
- `budget_recurring_overrides(id, user_id, category_id, month CHECK 1-12, amount, UNIQUE(category_id, month))`.
- `budget_one_off_overrides(id, user_id, category_id, year, month, amount, UNIQUE(category_id, year, month))`.
- `account_snapshots(id, account_id, taken_at, balance, note)`.
- `fx_rates(id, date, from_ccy, to_ccy, rate, UNIQUE(date, from_ccy, to_ccy))`.
- `audit_log(id, entity_type, entity_id, changed_at, operation CHECK IN ('create','update','delete','undelete'), prev_json, new_json)`.

Indexes:
- `transactions(operation_date)`, `transactions(account_id)`, `transactions(category_id)`.
- `planned_transactions(operation_date)`.
- `fx_rates(date, from_ccy, to_ccy)`.

Reference: ADR-0008, ADR-0009, ADR-0010, ADR-0011, ADR-0013.

### ✅ T-012 [S] Seed data migration → T-011
- Seed single `users` row (`id=1, name='default'`).
- Seed system categories: `Transit` (direction=transit), `Reconciliation` (direction=adjustment).
- These must be undeletable (enforced in service layer).

### ✅ T-013 [P] Repository layer → T-011
- `src/budget_planner/repositories/` — one module per entity (`transactions.py`, `accounts.py`, `categories.py`, `planned.py`, `recurring.py`, `budgets.py`, `snapshots.py`, `fx.py`).
- Each module exposes pure functions (no classes). Signature pattern:
  ```python
  def find_by_id(conn: Connection, entity_id: int) -> Entity | None: ...
  def list_filtered(conn: Connection, filters: Filters) -> list[Entity]: ...
  def create(conn: Connection, data: NewEntity) -> Entity: ...
  def update(conn: Connection, entity_id: int, data: PatchEntity) -> Entity: ...
  def soft_delete(conn: Connection, entity_id: int) -> None: ...
  ```
- All mutating functions write to `audit_log` in the same transaction.
- All read functions filter `deleted_at IS NULL` by default; accept `include_deleted: bool = False` kwarg.
- Reference: ADR-0022.

### ✅ T-014 [P] Domain types → T-011
- `src/budget_planner/domain/` — frozen dataclasses or Pydantic models for every entity + DTOs (`NewTransaction`, `PatchTransaction`, `TransactionFilter`, etc).
- `Direction` enum: `income`, `expense`, `transit`, `adjustment`.
- `Cadence` enum: `monthly`, `quarterly`, `yearly`.
- Money helpers: `to_minor_units(decimal) -> int`, `from_minor_units(int) -> Decimal`, formatter respecting currency decimals.

---

## Phase 2 — Services (Pure Business Logic)

### ✅ T-020 [P] FX service → T-013, T-014
- `src/budget_planner/services/fx.py`.
- `get_rate(conn, date, from_ccy, to_ccy) -> Decimal`:
    - Return `1.0` if `from == to`.
    - Lookup `fx_rates`; if present return.
    - Else fetch from `frankfurter.app`; insert; return.
    - On API error, return the most recent `rate` for that pair (fallback) with a log warning.
- `convert(conn, amount_minor, date, from_ccy, to_ccy) -> int`.
- Unit-tested with mocked HTTP client.
- Reference: ADR-0008.

### ✅ T-021 [P] Balance service → T-013
- `derive_balance(conn, account_id, as_of_date | None) -> int`:
  `opening_balance + Σ (signed amount of all non-deleted txns on/before as_of_date affecting this account)`.
- Signed amount rules:
    - `income` → `+amount` on `account_id`.
    - `expense` → `-amount` on `account_id`.
    - `transit` → `-amount` on `account_id`, `+amount` on `dest_account_id`.
    - `adjustment` → `+amount` on `account_id` (amount already signed per ADR).
- `account_stats(conn, account_id) -> AccountStats`.

### ✅ T-022 [P] Recurring occurrence generator → T-013, T-014
- `generate_occurrences(rule, start_date, end_date) -> list[Occurrence]` (pure function).
    - Expand cadence: `monthly` → month-step from `start_date`; `quarterly` → every 3 months; `yearly` → yearly.
    - Clip by `end_date` of rule and query range.
    - Return virtual `Occurrence` dataclasses carrying rule defaults.
- `apply_overrides(occurrences, overrides) -> list[Occurrence]`:
    - Drop `skipped`.
    - Mutate `overridden` with override fields.
- Reference: ADR-0015.

### ✅ T-023 [P] Planned log service → T-013, T-022
- `list_planned(conn, filters) -> list[PlannedView]`: UNION of `planned_transactions` + virtual occurrences from active rules in range.
- `promote_to_actual(conn, planned_id, edits) -> Transaction`: insert into `transactions`, update `planned_transactions.promoted_to_txn_id`, write audit entries.
- Reference: ADR-0014.

### ✅ T-024 [P] Budget service → T-013
- `resolve_budget(conn, category_id, year, month) -> int | None`: null-coalesce one-off → recurring → default.
- `month_summary(conn, year, month) -> MonthSummary`: per-category budgeted/spent/remaining + analytics (avg monthly spend overall, avg this year, delta vs previous month).
- Reference: ADR-0017.

### ✅ T-025 [P] Forecast service → T-013, T-020, T-021, T-022
- `forecast(conn, horizon_days) -> ForecastSeries`:
    - For each day in horizon, project balance per account (base-currency converted via latest FX rate).
    - Return daily series + totals.
- Deterministic, pure.
- Reference: ADR-0018.

### ✅ T-026 [P] Reconciliation service → T-013, T-021
- `reconcile(conn, account_id, actual_balance_minor) -> Transaction`:
    - Compute delta = actual − derived.
    - Insert transaction: category=Reconciliation, direction=adjustment, amount=delta (signed), description=`"auto-reconciliation {date}"`.
    - Return the created transaction.
- Reference: ADR-0013.

### ✅ T-027 [P] Export service → T-013
- `export_csv(records) -> bytes`, `export_parquet(records) -> bytes`.
- Shared across txn-log, planned-log, analytics views.

### ✅ T-028 [P] Audit helper → T-013
- `write_audit(conn, entity_type, entity_id, operation, prev_json, new_json)`.
- Called from every mutating repository function.
- Reference: ADR-0022.

---

## Phase 3 — Web Layer

### ✅ T-030 [S] FastAPI app skeleton → Phase 2 complete (minus any lagging [P] tasks)
- `src/budget_planner/web/app.py` creates FastAPI app, mounts static, templates, routers.
- Jinja env with helpers: `format_money(amount, currency)`, `format_date(date)`, `direction_badge(d)`.
- HTMX included via CDN in base template.
- Tailwind CSS via CDN.
- `base.html`, `partials/` directory for HTMX fragments.
- `just dev` → `uvicorn --reload --host 127.0.0.1 --port 8000`.

### ✅ T-031 [P] Transactions router → T-030, T-013
- `GET /transactions` — list with filter sidebar; HTMX re-renders table partial on filter change.
- `GET /transactions/new` — form fragment.
- `POST /transactions` — create.
- `GET /transactions/{id}/edit` — edit form fragment.
- `POST /transactions/{id}` — update.
- `POST /transactions/{id}/delete` — soft delete.
- `GET /transactions/export?format=csv|parquet` — download filtered view.

### ✅ T-032 [P] Accounts router → T-030, T-013, T-021, T-026
- `GET /accounts` — list with derived balance + stats.
- `POST /accounts` — create.
- `POST /accounts/{id}` — update (not currency).
- `POST /accounts/{id}/delete` — soft delete.
- `POST /accounts/{id}/snapshot` — take snapshot.
- `GET /accounts/{id}/reconcile` — reconcile form.
- `POST /accounts/{id}/reconcile` — perform reconciliation.

### ✅ T-033 [P] Categories router → T-030, T-013
- `GET /categories` — list.
- `POST /categories` — create.
- `POST /categories/{id}` — update (not direction once used).
- `POST /categories/{id}/delete` — soft delete (block system cats).

### ✅ T-034 [P] Planned transactions router → T-030, T-023
- `GET /planned` — list including virtual occurrences; filter + export.
- `POST /planned` — create one-off.
- `POST /planned/{id}` — edit one-off.
- `POST /planned/{id}/promote` — promote to actual (modal with editable amount/date).
- `GET /planned/{id}/delete` — soft delete (one-off).

### ✅ T-035 [P] Recurring rules router → T-030, T-013, T-022
- `GET /recurring` — list rules + upcoming occurrences preview.
- `POST /recurring` — create rule.
- `POST /recurring/{id}` — edit rule.
- `POST /recurring/{id}/deactivate` — set `active=false`.
- `POST /recurring/{rule_id}/overrides` — add skip/override for a specific occurrence_date.
- `POST /recurring/{rule_id}/overrides/{occurrence_date}/delete` — remove override.

### ✅ T-036 [P] Budget router → T-030, T-024
- `GET /budget` — current month view with per-category spent/budgeted/remaining + analytics.
- `GET /budget/manage` — manage defaults + overrides.
- `POST /budget/defaults/{category_id}` — set default.
- `POST /budget/recurring/{category_id}/{month}` — set recurring override.
- `POST /budget/one-off/{category_id}/{year}/{month}` — set one-off override.

### ✅ T-037 [P] Forecast router → T-030, T-025
- `GET /forecast?horizon_days=N` — chart + table.
- Plotly JSON embedded; HTMX re-triggers on inputs changing in any router (via `HX-Trigger` response header `forecast-stale`).

### ✅ T-038 [P] Analytics router → T-030, T-013
- `GET /analytics` — multi-chart dashboard: spend by category, cash-flow by account, income vs expense trend, top categories per month.
- Groupby selector (category / account / direction / month-quarter-year).

### ✅ T-039 [S] Navigation + home → T-031..T-038
- Base template with left nav: Transactions, Accounts, Categories, Planned, Recurring, Budget, Forecast, Analytics.
- Home dashboard: snapshot of current month budget + fortune total + next 7 days of planned txns.

---

## Phase 4 — Testing

### ✅ T-040 [P] Unit tests
Per service and repository. Target ≥90% coverage. Pure-function heavy, mocks only for HTTP.

### ✅ T-041 [P] Integration tests
- Full repository stack against a temp SQLite file.
- FX service against mocked HTTP.
- Promotion flow: planned → actual.
- Reconciliation flow: before/after derived balance.

### ✅ T-042 [P] E2E smoke tests
- Create account, add transaction, see balance update.
- Set budget, record spend, see remaining.
- Add recurring rule, see virtual occurrences in planned view, promote one.
- Reconcile an account, confirm adjustment txn created.

### ✅ T-043 [S] Coverage gate
- `pytest --cov=src/budget_planner --cov-fail-under=90`.
- Added to `just test` and `just ci`.

---

## Phase 5 — Polish

### T-050 [P] README
- Prereqs (uv, just, Python 3.12).
- Quick start (`just install`, `just migrate`, `just seed`, `just dev`).
- Link to `docs/`.

### T-051 [P] Error handling + flash messages
- Validation errors shown inline via HTMX partials.
- Server errors returned with 4xx/5xx + user-facing message, logged with context.

### T-052 [P] Accessibility pass
- Semantic HTML in templates.
- Form labels associated.
- Keyboard-navigable.

### T-053 [P] Visual polish
- Consistent spacing, typography scale, color tokens via CSS custom properties layered on top of Tailwind.
- Avoid default template look (see global web/design-quality rule).

---

## Phase 6 — Deferred to v2

- CSV import with pluggable parsers.
- Auth and multi-user.
- Cross-currency transits with FX spread modelling.
- DuckDB attach for analytics speed-up.
- Trend-based forecast overlay.
- Rollover budgets.
- Hierarchical categories.
- Deployment to a hosted environment (likely Fly.io / Railway / self-hosted Docker + Caddy).
