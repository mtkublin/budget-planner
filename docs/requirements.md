# Budget Planner — Requirements

> Source: `docs/initial_reqirements.txt` + decisions captured during planning Q&A (see `docs/adr/`).
> This is the canonical requirements document; the initial text file is retained for history only.

---

## 1. Product Scope

A locally-hosted web application for personal budget planning and fortune (net-worth) tracking across multiple accounts and currencies. Single user, no authentication, served on `127.0.0.1` for local use. Designed so future deployment and multi-user support can be added without rework.

---

## 2. Functional Requirements

### 2.1 Transaction Log (persistent)

- **F1.1** Record transactions with these mandatory fields: `operation_date` (DATE), `category_id`, `amount` (positive integer in minor units of the account's currency), `description`, `account_id`.
- **F1.2** All transactions persisted in SQLite.
- **F1.3** Filterable by any field (date range, category, amount range, account, description substring).
- **F1.4** Export the current filtered view to CSV and Parquet.
- **F1.5** Edit any existing transaction; soft-delete any existing transaction. Every mutation recorded in `audit_log`.
- **F1.6** Categories drawn from a user-managed list. Each category has a `direction`: `income`, `expense`, `transit`, or `adjustment`.
- **F1.7** Transits between the user's own accounts modelled as a single transaction row with both `account_id` (source) and `dest_account_id` (destination) populated. Transits are excluded from income/expense statistics. **Transits are only allowed between accounts of the same currency.**

### 2.2 Account Management

- **F2.1** Create multiple accounts. Each account has: `name` (required, unique), `type` (optional free-text label, e.g. "bank", "cash"), `currency` (ISO 4217, immutable after creation), `opening_balance` (integer minor units).
- **F2.2** Transactions must reference an existing (non-deleted) account.
- **F2.3** View current state per account:
    - Current balance (derived from `opening_balance + Σ signed transactions`).
    - Transaction count, average inflow/outflow, last activity date.
- **F2.4** Manual balance snapshots (user clicks "take snapshot") stored in `account_snapshots` as a pure audit record (does not alter the derived balance).
- **F2.5** Reconciliation flow: user enters the true current balance from their bank; the system computes the delta and auto-inserts an adjustment transaction under the seeded "Reconciliation" category so the derived balance matches reality.

### 2.3 Planned Transaction Log

- **F3.1** Planned transactions follow the same data model as persistent transactions.
- **F3.2** Recurring rules supported with cadences: `monthly`, `quarterly`, `yearly`. Rules are the source of truth; occurrences are generated **virtually** (not materialized) when queried for any date range.
- **F3.3** One-off planned transactions supported (not tied to a rule).
- **F3.4** Filtering, export, edit, soft-delete — same semantics as the persistent log.
- **F3.5** A dedicated view for managing recurring rules (list, edit, deactivate).
- **F3.6** Per-occurrence overrides on recurring rules via `recurring_rule_overrides(rule_id, occurrence_date, state, amount_override, description_override, date_override)` with `state ∈ {skipped, overridden}`. Supports multi-occurrence skip (e.g. "skip July 2026 AND September 2026").
- **F3.7** Planned → actual promotion is **manual**. User clicks "mark executed", edits amount/date/description if needed, system inserts into the persistent transaction table and stamps `promoted_to_txn_id` on the planned entry for audit.

### 2.4 Monthly Budget

- **F4.1** Flat category list (no hierarchy).
- **F4.2** Three-tier budget resolution per category per month:
    1. `budget_defaults(category_id, amount)` — base.
    2. `budget_recurring_overrides(category_id, month 1-12, amount)` — applied every year for that month.
    3. `budget_one_off_overrides(category_id, year, month, amount)` — applied once.
    Resolved as `one_off ?? recurring ?? default`.
- **F4.3** No rollover between months. Each month resets.
- **F4.4** Per-category budget only. Total budget shown as a derived sum.
- **F4.5** Current month view includes per-category spent / budgeted / remaining, plus analytical values: average monthly spend overall, average this year, delta vs previous month.

### 2.5 Forecasting

- **F5.1** Long-term fortune forecast across accounts and in aggregate (base currency = PLN by default, configurable).
- **F5.2** **Deterministic projection**: `projected_balance(account, date) = current_balance(today) + Σ planned_txns + Σ virtual_recurring_occurrences` up to `date`. Cross-currency aggregation uses the latest cached FX rate.
- **F5.3** Live-updating via HTMX fragment swap: every edit to planned/recurring/account state triggers a server-side recomputation and chart redraw.
- **F5.4** Horizon selectable by the user (e.g. 6 months, 1 year, 5 years).

### 2.6 Analytics

- **F6.1** Analytics view over the persistent transaction log.
- **F6.2** Graphs: spend by category over time, income vs expense trend, cash-flow by account, top categories per month.
- **F6.3** Groupable by category, account, direction, month/quarter/year.
- **F6.4** All graphs interactive (Plotly).

### 2.7 Multi-Currency

- **F7.1** Each account has an immutable `currency` set at creation.
- **F7.2** Transactions inherit the currency of their account (not stored on the transaction row).
- **F7.3** A `base_currency` configured in the application config (default: `PLN`). All aggregates (fortune, budget, forecast, analytics) converted into base currency for display.
- **F7.4** FX rates fetched from the ECB via `frankfurter.app` on demand, cached in a local `fx_rates(date, from_ccy, to_ccy, rate)` table. **Historical rates used for historical transaction conversion** (a transaction on 2026-01-15 converts at the 2026-01-15 rate, not today's). Fallback to the last-known rate if the API is unreachable.
- **F7.5** Transits across currencies are **blocked at the validation layer** in v1.

---

## 3. Non-Functional Requirements

### 3.1 Technology

- Python 3.12.
- SQLite (OLTP). DuckDB attach deferred to a later iteration if analytics queries become slow.
- FastAPI + HTMX + Jinja2 (templates) + Tailwind CSS (via CDN).
- Plotly for charts.
- `uv` for dependency and virtual-environment management.
- `just` as the task runner.

### 3.2 Testing

- Unit test coverage ≥ 90% enforced in CI (bar raised above the 80% minimum requested, because the codebase is functional and pure).
- Integration tests cover: database layer, FX-rate resolver, forecast engine, planned→actual promotion, reconciliation flow.
- End-to-end smoke tests (Playwright or `httpx` + Jinja fixtures) cover the critical user flows.

### 3.3 Code Style

- Functional-first: pure functions, immutable data (dataclasses `frozen=True`), no OO beyond dataclasses / Pydantic DTOs / Protocols.
- DRY: shared repository/service layer across views; one place for query helpers.
- Type-checked with `mypy --strict`.
- Formatted and linted with `ruff` (replaces `black` + `isort` + `flake8`; `black`-compatible output).
- SQL formatted/linted with `sqlfluff`.
- Jinja templates linted with `djlint`.

### 3.4 Pre-commit

Hooks: `ruff`, `ruff-format`, `mypy`, `pytest` (fast subset), `sqlfluff`, `djlint`, `bandit`, `detect-secrets`, and the standard pre-commit stdlib hooks (trailing whitespace, EOF newline, large file check, yaml/toml validate).

### 3.5 Developer Experience

- `just dev` — run the app with hot reload.
- `just test` — run the test suite with coverage.
- `just lint` — run all linters.
- `just format` — autofix formatting.
- `just typecheck` — mypy strict.
- `just ci` — run everything CI runs.
- `just db-reset` — recreate the dev database.
- `just seed` — seed default categories, demo accounts.

### 3.6 CI

- GitHub Actions.
- Single matrix row: `ubuntu-latest` + Python 3.12.
- Runs `just ci` on push/PR.
- Coverage uploaded as artifact.

### 3.7 Data Semantics

- **Amounts**: positive integer minor units. Direction derived from `category.direction`. Exception: adjustments (reconciliation) may be signed to encode inflow/outflow.
- **Timestamps**: `created_at` / `updated_at` columns stored as UTC. User-facing dates on transactions stored as DATE (no time component). Display timezone = `Europe/Warsaw` by default, configurable.
- **Soft delete**: every mutable table has `deleted_at` nullable timestamp. All queries filter `WHERE deleted_at IS NULL` via a repository helper.
- **Audit**: shared polymorphic `audit_log(id, entity_type, entity_id, changed_at, operation, prev_json, new_json)` written on every mutation.
- **Multi-user scaffold**: every user-owned table has a nullable `user_id` column (defaults to `1`), unused in v1, ready for future auth.

### 3.9 UI / Interaction Model

- **Information architecture.** Four top-level nav items in a left rail: **Overview**, **Ledger**, **Accounts**, **Budget**. One Settings affordance at the bottom opens a slide-over drawer; Settings is not a top-level tab. Legacy routes (`/transactions`, `/planned`, `/recurring`, `/categories`, `/analytics`) continue to resolve via 302 redirects for one release before Phase 7 cleanup. See [ADR-0023](adr/0023-ux-redesign-information-architecture.md).
- **Overview `/`.** Three panels: (1) all accounts with per-account balance + base-currency summed total, (2) current-month budget stats with **amount left** as the headline number plus spent/of + days-left + pace tag, (3) upcoming planned payments with rows where `planned_date >= today` at full emphasis and rows where `planned_date < today` (overdue, un-promoted) muted + italic with an `overdue` chip. Already-promoted planned rows do not appear here.
- **Ledger `/ledger`.** One shell renders Actual | Planned | Recurring behind a segmented control; filter and column shape are shared. The fragment route `/ledger/table?view=…` dispatches to existing repository queries. Keyboard `[` and `]` cycle the segmented control.
- **Settings drawer.** `/settings?tab=categories|fx|prefs` returns the drawer HTML; drawer is injected into a persistent `#drawer-root`. Opens via gear icon or `g s`.
- **Command palette.** `⌘K` / `Ctrl K` opens an Alfred-style popover for navigation and quick actions. Vanilla JS (no framework), ~60 lines total.
- **Keyboard shortcuts.** `g o / g l / g a / g b / g s` navigate. `n` opens the context-aware Quick-add form. `/` focuses the active page's search/filter. `[` / `]` cycle Ledger segmented control. `?` opens the cheatsheet. `⎋` closes the topmost overlay. All guards against capturing keys inside `<input>` / `<textarea>` / `[contenteditable]`.
- **Quick-add FAB.** Fixed bottom-right. Click or `n`. Form shape is derived from the active Ledger tab (or defaults to actual transaction on Overview / Accounts).
- **Design direction.** Editorial / Swiss, per [ADR-0023](adr/0023-ux-redesign-information-architecture.md) continuing [T-053](plans/v1/phase-5/T-053-visual-polish.md): oklch palette, hairline elevation, tabular numerals, one display + one text + one mono face, single accent colour. No dark mode, no mobile adaptive nav, no icon system in v1.
- **Overlay stack.** Only one overlay (drawer, modal, palette) responds to Esc at a time; stack managed by `static/js/overlay-stack.js`.

---

### 3.8 Out of Scope for v1

- CSV import from banks (deferred to v2, pluggable parser pattern).
- Multi-user authentication.
- Cross-currency transits.
- ML/trend-based forecasting.
- Rollover budgets.
- Hierarchical categories.
- Background scheduling / cron jobs.

---

## 4. Deliverables

- Running local web app satisfying all functional requirements above.
- CI green on `main`.
- `docs/` kept in sync with code (ADRs for every meaningful change).
- `README.md` with run instructions.
