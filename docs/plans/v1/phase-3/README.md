# Phase 3 — Web Layer · Plan Index

> Goal of the phase: every functional requirement in `docs/requirements.md` §2 reachable through the browser. Thin FastAPI routers, Jinja2 server-rendered templates, HTMX for fragment swaps, Tailwind (CDN) for styling, Plotly for charts. Server binds to `127.0.0.1` only.

Phase gate (from `docs/implementation_plan.md`):

- Each router under test via `TestClient` + structural assertions on key fragments (BeautifulSoup).
- HTMX partials swap correctly (verified via response headers + body shape).
- `GET /` lands on a dashboard showing current-month budget state + total fortune + next 7 days of planned txns.
- Plotly charts render on forecast + analytics.

## Tasks

| # | File | Mode | Purpose |
|---|------|------|---------|
| T-030 | [T-030-fastapi-app-skeleton.md](T-030-fastapi-app-skeleton.md) | `[S]` | FastAPI app factory, Jinja environment with shared filters, HTMX + Tailwind + Plotly CDN wiring in `base.html`, shared partials directory, `/healthz`, 127.0.0.1 bind. |
| T-031 | [T-031-transactions-router.md](T-031-transactions-router.md) | `[P]` | CRUD + filter sidebar + CSV/Parquet export for the persistent transaction log. |
| T-032 | [T-032-accounts-router.md](T-032-accounts-router.md) | `[P]` | Account list with derived balance, snapshot capture, reconciliation flow. |
| T-033 | [T-033-categories-router.md](T-033-categories-router.md) | `[P]` | Category CRUD; direction locked once used; system categories undeletable. |
| T-034 | [T-034-planned-router.md](T-034-planned-router.md) | `[P]` | Planned log (one-off + virtual recurring) with manual promotion modal. |
| T-035 | [T-035-recurring-router.md](T-035-recurring-router.md) | `[P]` | Recurring rules list, upcoming-occurrence preview, per-occurrence skip/override toggles. |
| T-036 | [T-036-budget-router.md](T-036-budget-router.md) | `[P]` | Current-month budget view + three-tier override management. |
| T-037 | [T-037-forecast-router.md](T-037-forecast-router.md) | `[P]` | Deterministic fortune forecast; horizon selector; live refresh via `HX-Trigger: forecast-stale`. |
| T-038 | [T-038-analytics-router.md](T-038-analytics-router.md) | `[P]` | Multi-chart analytics dashboard (Plotly) with groupby selector + export. |
| T-039 | [T-039-navigation-and-home.md](T-039-navigation-and-home.md) | `[S]` | Left-nav shell, home dashboard, links point to every router landed above. |

Order of execution: T-030 must land first. T-031..T-038 are parallel-safe once T-030 is green. T-039 is last — it stitches the navigation and wires the dashboard panels assembled from the other routers' partials.

## Routing table

Every endpoint across every Phase 3 router. HTML pages return `text/html`; HTMX fragment responses return a partial HTML snippet and may include `HX-Trigger` headers to invalidate siblings.

| Method | Path | Router | Response | Service(s) called |
|--------|------|--------|----------|-------------------|
| GET | `/` | T-039 | full page (home dashboard) | `budget.month_summary`, `balance.derive_balance` ×N, `planned.list_planned` (next 7d) |
| GET | `/healthz` | T-030 | `200 ok` JSON | — |
| GET | `/transactions` | T-031 | full page | `transactions.list_filtered` (via repo) |
| GET | `/transactions/table` | T-031 | HTMX fragment (table body + pagination) | `transactions.list_filtered` |
| GET | `/transactions/new` | T-031 | HTMX fragment (form) | `categories.list`, `accounts.list` |
| POST | `/transactions` | T-031 | HTMX fragment (row + oob flashes) | `transactions.create`; emits `HX-Trigger: balance-stale, forecast-stale` |
| GET | `/transactions/{id}/edit` | T-031 | HTMX fragment (form) | `transactions.find_by_id` |
| POST | `/transactions/{id}` | T-031 | HTMX fragment (row swap) | `transactions.update`; emits `HX-Trigger: balance-stale, forecast-stale` |
| POST | `/transactions/{id}/delete` | T-031 | HTMX fragment (row removal) | `transactions.soft_delete`; emits `HX-Trigger: balance-stale, forecast-stale` |
| GET | `/transactions/export` | T-031 | file download (csv/parquet) | `export.export_csv` \| `export.export_parquet` |
| GET | `/accounts` | T-032 | full page | `accounts.list`, `balance.derive_balance`, `balance.account_stats` |
| GET | `/accounts/new` | T-032 | HTMX fragment (form) | — |
| POST | `/accounts` | T-032 | HTMX fragment (card insert) | `accounts.create` |
| GET | `/accounts/{id}/edit` | T-032 | HTMX fragment (form) | `accounts.find_by_id` |
| POST | `/accounts/{id}` | T-032 | HTMX fragment (card swap) | `accounts.update` (currency locked) |
| POST | `/accounts/{id}/delete` | T-032 | HTMX fragment (card removal) | `accounts.soft_delete`; emits `HX-Trigger: balance-stale, forecast-stale` |
| POST | `/accounts/{id}/snapshot` | T-032 | HTMX fragment (toast + snapshot row) | `snapshots.create` |
| GET | `/accounts/{id}/reconcile` | T-032 | HTMX fragment (modal form) | `balance.derive_balance` |
| POST | `/accounts/{id}/reconcile` | T-032 | HTMX fragment (closes modal, swaps card) | `reconciliation.reconcile`; emits `HX-Trigger: balance-stale, forecast-stale` |
| GET | `/categories` | T-033 | full page | `categories.list` |
| GET | `/categories/new` | T-033 | HTMX fragment (form) | — |
| POST | `/categories` | T-033 | HTMX fragment (row insert) | `categories.create` |
| GET | `/categories/{id}/edit` | T-033 | HTMX fragment (form) | `categories.find_by_id` |
| POST | `/categories/{id}` | T-033 | HTMX fragment (row swap) | `categories.update` (direction locked if used) |
| POST | `/categories/{id}/delete` | T-033 | HTMX fragment (row removal) | `categories.soft_delete` (block system cats) |
| GET | `/planned` | T-034 | full page | `planned.list_planned` |
| GET | `/planned/table` | T-034 | HTMX fragment (table body) | `planned.list_planned` |
| GET | `/planned/new` | T-034 | HTMX fragment (form) | `categories.list`, `accounts.list` |
| POST | `/planned` | T-034 | HTMX fragment (row insert) | `planned.create` (one-off); emits `HX-Trigger: forecast-stale` |
| GET | `/planned/{id}/edit` | T-034 | HTMX fragment (form) | `planned.find_by_id` |
| POST | `/planned/{id}` | T-034 | HTMX fragment (row swap) | `planned.update`; emits `HX-Trigger: forecast-stale` |
| POST | `/planned/{id}/delete` | T-034 | HTMX fragment (row removal) | `planned.soft_delete`; emits `HX-Trigger: forecast-stale` |
| GET | `/planned/{id}/promote` | T-034 | HTMX fragment (modal with editable amount/date/description) | `planned.find_by_id` |
| POST | `/planned/{id}/promote` | T-034 | HTMX fragment (modal close + row re-render) | `planned.promote_to_actual`; emits `HX-Trigger: balance-stale, forecast-stale` |
| GET | `/planned/export` | T-034 | file download | `export.export_csv` \| `export.export_parquet` |
| GET | `/recurring` | T-035 | full page | `recurring.list_rules`, `recurring.preview_occurrences` |
| GET | `/recurring/new` | T-035 | HTMX fragment (form) | `categories.list`, `accounts.list` |
| POST | `/recurring` | T-035 | HTMX fragment (card insert + preview) | `recurring.create`; emits `HX-Trigger: forecast-stale` |
| GET | `/recurring/{id}/edit` | T-035 | HTMX fragment (form) | `recurring.find_by_id` |
| POST | `/recurring/{id}` | T-035 | HTMX fragment (card swap + preview) | `recurring.update`; emits `HX-Trigger: forecast-stale` |
| POST | `/recurring/{id}/deactivate` | T-035 | HTMX fragment (card state swap) | `recurring.deactivate`; emits `HX-Trigger: forecast-stale` |
| POST | `/recurring/{rule_id}/overrides` | T-035 | HTMX fragment (occurrence row swap) | `recurring.upsert_override`; emits `HX-Trigger: forecast-stale` |
| POST | `/recurring/{rule_id}/overrides/{occurrence_date}/delete` | T-035 | HTMX fragment (occurrence row swap) | `recurring.delete_override`; emits `HX-Trigger: forecast-stale` |
| GET | `/budget` | T-036 | full page | `budget.month_summary` |
| GET | `/budget/table` | T-036 | HTMX fragment (table body) | `budget.month_summary` |
| GET | `/budget/manage` | T-036 | full page | `budget.list_defaults`, `budget.list_recurring_overrides`, `budget.list_one_off_overrides` |
| POST | `/budget/defaults/{category_id}` | T-036 | HTMX fragment (row swap) | `budget.set_default`; emits `HX-Trigger: budget-stale` |
| POST | `/budget/recurring/{category_id}/{month}` | T-036 | HTMX fragment (cell swap) | `budget.set_recurring_override`; emits `HX-Trigger: budget-stale` |
| POST | `/budget/one-off/{category_id}/{year}/{month}` | T-036 | HTMX fragment (cell swap) | `budget.set_one_off_override`; emits `HX-Trigger: budget-stale` |
| GET | `/forecast` | T-037 | full page (chart + table) | `forecast.forecast` |
| GET | `/forecast/fragment` | T-037 | HTMX fragment (chart + table) | `forecast.forecast` |
| GET | `/analytics` | T-038 | full page (charts) | `transactions.list_filtered`, aggregation helpers |
| GET | `/analytics/charts` | T-038 | HTMX fragment (chart grid) | aggregation helpers |
| GET | `/analytics/export` | T-038 | file download | `export.export_csv` \| `export.export_parquet` |

## Downstream consumers (Phase 4+)

- E2E tests (T-042) walk the paths listed above (add txn → see balance update → reconcile → forecast refresh).
- Polish phase (T-051, T-053) refines partials created here; routes do not change.
- Any new endpoint added after this phase requires an ADR per the docs-first policy in `CLAUDE.md`.
