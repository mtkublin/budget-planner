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

### ✅ T-050 [P] README
- Prereqs (uv, just, Python 3.12).
- Quick start (`just install`, `just migrate`, `just seed`, `just dev`).
- Link to `docs/`.

### ✅ T-051 [P] Error handling + flash messages
- Validation errors shown inline via HTMX partials.
- Server errors returned with 4xx/5xx + user-facing message, logged with context.

### ✅ T-052 [P] Accessibility pass
- Semantic HTML in templates.
- Form labels associated.
- Keyboard-navigable.

### ✅ T-053 [P] Visual polish
- Consistent spacing, typography scale, color tokens via CSS custom properties layered on top of Tailwind.
- Avoid default template look (see global web/design-quality rule).

---

## Phase 6 — UX Redesign (IA Consolidation + Interaction Model)

> Collapses 9 top-level nav items into 4 + a Settings drawer. Adds Command palette (⌘K) + Quick-add FAB + keyboard shortcuts. No data-model change; pure web-layer refactor. Decision: [ADR-0023](../../adr/0023-ux-redesign-information-architecture.md). Detailed plan + ASCII mockups: [`phase-6/README.md`](phase-6/README.md), [`phase-6/mockups.md`](phase-6/mockups.md).

### ✅ T-060 [S] ADR-0023 + Phase 6 docs scaffolding
- Write [`docs/adr/0023-ux-redesign-information-architecture.md`](../../adr/0023-ux-redesign-information-architecture.md).
- Add Phase 6 directory + 12 task stub files under `docs/plans/v1/phase-6/`.
- Rename prior "Phase 6 — Deferred to v2" to Phase 7 (below).

### ✅ T-061 [S] Base shell refactor → T-060
- Left rail + `#drawer-root` + `#modal-root` + FAB slot in `base.html`.
- Preserve Jinja block names (`title`, `head_extra`, `nav`, `main`, `scripts`).
- Reuse editorial/Swiss tokens from T-053.
- Reference: ADR-0023.

### ✅ T-062 [S] Nav partial rewrite (4-item left rail) → T-061
- `partials/_nav.html`: Overview, Ledger, Accounts, Budget + Settings affordance at bottom.
- `aria-current="page"` on active; 2 px accent left-border; `data-shortcut` attrs.
- Reference: ADR-0023.

### ✅ T-063 [P] Overview composition → T-062
- Three-panel layout: Accounts list + sum, Budget-left headline, Upcoming planned with overdue muting.
- New fragment `/overview/upcoming?window=7|30|all`.
- Reuse `services.balance.derive_balance`, `services.budget.month_summary`, `services.planned.list_planned`.
- Reference: ADR-0023.

### ✅ T-064 [P] Ledger unification → T-062
- New `routers/ledger.py` + `templates/ledger/{index,_table}.html` with Actual|Planned|Recurring segmented control.
- Fragment `/ledger/table?view=…` dispatches to existing repository queries.
- Alias old fragment routes.
- Reference: ADR-0023.

### ✅ T-065 [P] Accounts polish → T-061
- Per-card 90-day sparkline (pure SVG), inline Reconcile button, Show snapshots disclosure.
- Reference: ADR-0023.

### ✅ T-066 [P] Budget consolidation → T-061
- `/budget` with three stacked sections: Monthly summary, Rules editor, Breakdown.
- Reuse analytics figures from current `/analytics`.
- Reference: ADR-0023.

### ✅ T-067 [P] Settings drawer → T-061
- New `routers/settings.py` + `templates/settings/{_categories,_fx,_prefs}.html`.
- Slide-over right, 480 px, three internal tabs (Categories, FX, Preferences).
- Reference: ADR-0023.

### ✅ T-068 [P] Command palette + keyboard shortcuts → T-062
- `partials/_palette.html` + `static/js/palette.js` (~60 lines) + `static/js/shortcuts.js` (~40 lines) + `partials/_shortcuts.html` cheatsheet.
- Keyboard map: `g o/l/a/b/s`, `n`, `/`, `[ ]`, `?`, `⌘K`, `⎋`.
- Reference: ADR-0023.

### ✅ T-069 [P] Quick-add FAB + slide-over form → T-064
- Fixed bottom-right 56×56 accent FAB; `n` key opens.
- Context-aware against active Ledger segmented tab.
- Reference: ADR-0023.

### ✅ T-070 [S] Legacy URL redirects → T-064, T-066, T-067
- 302: `/transactions`, `/planned`, `/recurring`, `/categories`, `/analytics` → new homes.
- Preserve HTMX fragment aliases for one release.
- Reference: ADR-0023.

### ✅ T-071 [S] Accessibility re-audit on new surfaces → T-063..T-069
- Focus trap in drawer + palette; shared focus-manager; `aria-current` on new nav; reduced-motion branches.
- Topmost-overlay stack rule (drawer + modal + palette coexist).
- Reference: ADR-0023, ADR-0019 (T-052 baseline).

### ✅ T-072 [S] README + CHANGELOG update → T-071
- README: nav screenshot description, keyboard map, migration note, ADR-0023 link.
- CHANGELOG entry on landing day.

---

## Phase 7 — Liability accounts (credit cards)

Adds behavioural classification + credit limit to accounts (ADR-0024, F2.1a). Scope: accounts surface + fortune reporting. See `docs/plans/v1/phase-7/README.md`.

### ✅ T-080 [S] ADR-0024 + Phase 7 docs scaffolding
- ADR-0024, F2.1a in `docs/requirements.md`, Phase 7 README + task stubs.

### ✅ T-081 [S] Migration `0004_add_liability_columns.sql` → T-080
- `accounts.is_liability INTEGER NOT NULL DEFAULT 0 CHECK (0,1)`; `accounts.credit_limit_minor INTEGER CHECK (NULL or > 0)`.
- Idempotent additive migration; existing rows default to assets.
- Reference: `docs/plans/v1/phase-7/T-081-migration-liability-columns.md`.

### ✅ T-082 [S] Domain + repository → T-081
- `Account`, `NewAccount`, `PatchAccount` gain `is_liability: bool` + `credit_limit_minor: int | None`.
- `PatchAccount.clear_credit_limit` sentinel distinguishes "no change" from "clear to NULL".
- Repository CRUD, hydrator, audit payloads thread the two new fields.
- Reference: `docs/plans/v1/phase-7/T-082-domain-and-repository.md`.

### ✅ T-083 [S] Fortune service → T-082
- New `services/fortune.py` with `compute_fortune(conn, settings) -> FortuneTotals`.
- Both `/` and `/accounts` routers call the service; `derive_balance` / `signed_legs` untouched.
- Reference: `docs/plans/v1/phase-7/T-083-fortune-service.md`.

### ✅ T-084 [S] Web form + templates → T-083
- Account form: "Credit card (liability)" checkbox + conditional credit-limit input.
- Account card: pill, utilization strip, over-limit badge.
- Overview + Accounts: Assets / Liabilities / Net worth split.
- Reference: `docs/plans/v1/phase-7/T-084-web-form-and-templates.md`.

### ✅ T-085 [S] Transaction-form soft warning → T-084
- `GET /transactions/_limit_preview` HTMX fragment previews post-transaction utilization for a liability account.
- Soft-only: form continues to submit when `over_by > 0`.
- Reference: `docs/plans/v1/phase-7/T-085-transaction-form-soft-warning.md`.

### ✅ T-086 [S] Seed + e2e journey → T-084
- `seed.seed()` adds demo "Bank (PLN)" + "Visa (PLN)" accounts, idempotent on re-seed.
- `tests/e2e/test_credit_card_journey.py` exercises the full user flow end-to-end.
- Reference: `docs/plans/v1/phase-7/T-086-seed-and-e2e-journey.md`.

---

## Phase 8 — Post-redesign UX fixes

Driven by field-use report 2026-10-27. Scope: UX bugfix + polish only. See `docs/plans/v1/phase-8/README.md` for the root-cause analysis.

> **ID note:** these use `T-090..T-094` as successors to Phase 7 (last `T-086`). Phase 9 (user preferences, directory `phase-9/`) currently uses `T-090..T-096` and will be renumbered by its own agent to avoid collision.

### ✅ T-090 [S] Shell + rail layout fit → T-061, T-062
- `.app-shell__main` gains `min-width: 0`; wide tables scroll inside their surface, not the page.
- `.rail-nav` tightened so Settings footer fits at 720 px high.
- Reference: `docs/plans/v1/phase-8/T-090-shell-and-rail-fit.md`.

### ✅ T-091 [S] One-field-per-row forms (`.form-stack`) → T-053, T-069
- Shared `.form-stack` component replaces `grid grid-cols-2` on all five create/edit partials.
- Applies to Transactions, Planned, Recurring, Accounts, Categories.
- Reference: `docs/plans/v1/phase-8/T-091-form-stack-layout.md`.

### ✅ T-092 [S] Ledger segmented wiring → T-064
- Wrap `_table.html` in `<div id="ledger-table">` so segmented `hx-target` resolves. Preserves legacy inner ids.
- Secondary effect: FAB view-aware routing becomes reachable, closing the "no option to add Planned/Recurring" gap.
- Reference: `docs/plans/v1/phase-8/T-092-ledger-segmented-wiring.md`.

### ✅ T-093 [S] Overview upcoming interactions → T-063, T-069
- `+ Planned` button wired to `/planned/new` slide-over.
- Range segmented active state updated via `hx-swap-oob` on the segmented group.
- Reference: `docs/plans/v1/phase-8/T-093-overview-upcoming-interactions.md`.

### ✅ T-094 [S] FAB visibility scope + Budget rules affordance → T-069, T-092, ADR-0026
- `fab_target_for` returns `None` outside Overview + Ledger; `base.html` skips the include.
- Budget rules section gains an inline-edit hint; no new endpoint.
- New ADR-0026 narrows ADR-0023 affordance #4.
- Reference: `docs/plans/v1/phase-8/T-094-fab-scope-and-budget-affordance.md`.

---

## Phase 9 — Left Daily Spend

Metric `remaining ÷ days-until-next-income` surfaced on `/budget`; first per-user preference store (`user_preferences` table) holds the income anchor category. ADR-0025. See `docs/plans/v1/phase-9/README.md`.

### ✅ T-095 [S] ADR-0025 + requirements + Phase 9 docs scaffolding
- ADR-0025 user preferences + income anchor; F4.6 + F4.7 in `docs/requirements.md`; task stubs + CHANGELOG entry.

### ✅ T-096 [S] Migration `0005_user_preferences.sql` → T-095
- `user_preferences(user_id, key, value)` with `UNIQUE(user_id, key)`; no `deleted_at`, no audit (ADR-0025).

### ✅ T-097 [S] Domain + repository → T-096
- `domain/preferences.py` (`UserPreference`, `NewUserPreference`, `PREF_INCOME_ANCHOR_CATEGORY_ID`); `repositories/preferences.py` with `get` / `upsert` / `delete` in BEGIN/COMMIT, no `write_audit`.

### ✅ T-098 [S] Preferences service + income anchor resolver → T-097, T-033
- `services/preferences.py` with `get_` / `set_` / `resolve_income_anchor_category` + `InvalidAnchorCategoryError`. Direction + liveness defence at boundary; resolver permissive on stale references.

### ✅ T-099 [S] Next-planned-income lookup → T-023
- `services/planned.next_planned_for_category(conn, category_id, after, *, horizon_days=400)` reuses `list_planned` for persisted + virtual + dedup (ADR-0013); excludes promoted rows.

### ✅ T-100 [M] Left daily spend in `services/budget.py` → T-024, T-098, T-099
- `MonthSummary` grows `left_daily_spend_minor`, `next_income_date`, `days_until_next_income`, `anchor_category_name`. `month_summary(..., today=date)` injected per ADR-0007. Zero-budget → `None`; stale anchor / no planned hit → end-of-month fallback. Banker's rounding.

### ✅ T-101 [M] `/budget` card + anchor selector + endpoint → T-036, T-100
- New "Left to spend per day" hero section + "Income anchor" `<select>` on `/budget`. New `POST /budget/preferences/income-anchor` (empty body clears, non-income or unknown category → 422); emits `HX-Trigger: budget-stale`. `/budget` passes `today` in `settings.display_timezone`. 11 integration tests.

---

## Phase 10 — Frontend Toolchain Hardening → ADR-0027

Web-layer only. No service, repository, or data-model changes. Tasks follow ADR-0027 decisions 1–5 in order.

### ✅ T-102 [M] Local Tailwind build + CDN removal → ADR-0027 §1
- Add `package.json` with `tailwindcss` pinned; `tailwind.config.js` with content globs per ADR-0027.
- `just css` and `just css-watch` recipes.
- Build `src/budget_planner/web/static/tailwind.css`; wire into `base.html` with the existing `?v=<hash>` pattern.
- Remove the `cdn.tailwindcss.com` `<script>` from `base.html`.
- Pre-commit hook `tailwind-check` fails if generated CSS is stale vs. content globs.
- `just install` runs `npm ci` alongside `uv sync`.
- `frontend-visual-audit` sweep on `/`, `/ledger`, `/accounts`, `/budget` at 1440/1024/375 before marking done.

### ✅ T-103 [S] Stylelint pre-commit hook → ADR-0027 §2
- Add `stylelint` + `stylelint-config-standard` to `package.json`.
- Project override file for allowed custom-property patterns.
- Scope to `src/budget_planner/web/static/*.css`, exclude generated `tailwind.css`.
- Pre-commit hook wired; CI step runs via `npx --no-install stylelint`.

### T-104 [M] Jinja partial extraction → ADR-0027 §3
- Create `src/budget_planner/web/templates/_partials/` with macros: `card`, `segmented`, `chip`, `slide_over_header`, `overdue_row`.
- Each macro leads with a `{# #}` block documenting inputs: name, type, nullable, default.
- Replace open-coded duplicates across Overview, Ledger, Accounts, Budget, Settings drawer, Transaction form, Planned, Recurring.
- `frontend-visual-audit` sweep confirms no visual regression.

### T-105 [M] Visual-regression suite → ADR-0027 §4
- `tests/visual/test_snapshots.py` using `pytest-playwright` + `pixelmatch`.
- Routes: `/`, `/ledger`, `/accounts`, `/budget`. Viewports: 1440×900, 1024×768, 375×812.
- Baselines in `tests/visual/baselines/<route>__<viewport>.png`, committed.
- `just test-visual` + `just test-visual-update` recipes.
- CI: opt-in behind `CI_VISUAL=1`. Default CI unchanged.

### T-106 [S] CI Node toolchain + docs sync → ADR-0027 §5–§6
- GitHub Actions workflow adds `actions/setup-node@v4` + `npm ci` before `just ci`.
- README setup instructions updated with the Node + npm step.
- Cross-link ADR-0027 from the "Frontend validation" section of `CLAUDE.md`.

### T-107 [S] Ledger segmented control → full-page nav → ADR-0028
- Supersedes implementation approach in T-092 for segmented tabs only; filter form and pagination keep their htmx partial swaps.
- `src/budget_planner/web/templates/ledger/index.html`: replace segmented `<button>` elements with `<a class="segmented__btn" href="/ledger?view={{ v }}">`; set `aria-current="page"` on the active tab; drop `hx-get`, `hx-target`, `hx-swap`, `hx-push-url`, `aria-pressed` from the segmented control. Keep `data-view` for the keyboard-shortcut discovery path.
- `src/budget_planner/web/static/js/shortcuts.js`: switch the `[` / `]` listener from clicking the segmented button to `location.assign(nextHref)`, and find the active tab via `aria-current="page"` instead of `aria-pressed`.
- Resolves the FAB staleness defect: `base.html` re-renders `fab_target_for(request)` on every tab switch, so the FAB opens the correct create form on Actual / Planned / Recurring.
- Tests:
  - `tests/integration/web/test_ledger.py` — segmented control renders anchors with correct `href`; `aria-current` moves with `view` param; filter form + pagination htmx wiring unchanged; `[data-ledger-table]` wrapper still ships from fragment endpoint.
  - `tests/integration/web/test_fab.py` — FAB `hx-get` matches `view` on each `/ledger?view=…` response (Actual → `/transactions/new`, Planned → `/planned/new`, Recurring → `/recurring/new`).
- `frontend-visual-audit` sweep on `/ledger?view=actual|planned|recurring` at 1440/1024/375 before marking done; confirm FAB opens the right slide-over on each view.
- Docs:
  - `docs/CHANGELOG.md` — one dated line.
  - `docs/plans/v1/tasks.md` — mark `✅ T-107` on completion.

---

## Phase 7 — Deferred to v2

- CSV import with pluggable parsers.
- Auth and multi-user.
- Cross-currency transits with FX spread modelling.
- DuckDB attach for analytics speed-up.
- Trend-based forecast overlay.
- Rollover budgets.
- Hierarchical categories.
- Deployment to a hosted environment (likely Fly.io / Railway / self-hosted Docker + Caddy).
- Prune legacy `/transactions`, `/planned`, `/recurring`, `/categories`, `/analytics` routes + templates once Phase 6 302s have aged one release.
