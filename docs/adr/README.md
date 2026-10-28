# Architecture Decision Records

Numbered, append-only. See [ADR-0001](0001-record-architecture-decisions.md) for the process.

| # | Title |
|---|-------|
| 0001 | [Record Architecture Decisions](0001-record-architecture-decisions.md) |
| 0002 | [Web Stack — FastAPI + HTMX + Jinja2 + Tailwind (CDN) + Plotly](0002-web-stack-fastapi-htmx-jinja.md) |
| 0003 | [Database — SQLite Only in v1, DuckDB Attach Deferred](0003-database-sqlite-only-v1.md) |
| 0004 | [Package Manager — uv](0004-package-manager-uv.md) |
| 0005 | [Single User, No Auth, user_id Scaffolded](0005-single-user-no-auth-user-id-scaffold.md) |
| 0006 | [Multi-Currency Model](0006-multi-currency-model.md) |
| 0007 | [Timezone Handling](0007-timezone-handling.md) |
| 0008 | [Transaction Amount Sign & Direction](0008-transaction-amount-sign-and-direction.md) |
| 0009 | [Transit as a Single Row](0009-transit-single-row-model.md) |
| 0010 | [Account Model — Free-Text Type](0010-account-model-free-text-type.md) |
| 0011 | [Derived Balance, Manual Snapshots, Reconciliation](0011-derived-balance-snapshots-reconciliation.md) |
| 0012 | [Planned → Actual Promotion is Manual](0012-planned-manual-promotion.md) |
| 0013 | [Recurring Rules — Virtual Occurrences with Sparse Overrides](0013-recurring-virtual-occurrences-and-overrides.md) |
| 0014 | [Budget Model — Flat Categories, No Rollover, Three-Tier Resolution](0014-budget-flat-no-rollover-three-tier.md) |
| 0015 | [Forecasting — Deterministic Projection, Live via HTMX](0015-forecast-deterministic-live-htmx.md) |
| 0016 | [Task Runner — just](0016-task-runner-just.md) |
| 0017 | [Pre-commit Stack & Using Ruff Instead of Black](0017-precommit-ruff-instead-of-black.md) |
| 0018 | [CI — Single Matrix Row (Python 3.12 + Ubuntu)](0018-ci-single-matrix-row.md) |
| 0019 | [Soft Delete + Polymorphic Audit Log](0019-soft-delete-and-audit-log.md) |
| 0020 | [Import Deferred to v2, Export in v1](0020-import-deferred-export-v1.md) |
| 0021 | [Functional Style, No Gratuitous OOP](0021-functional-style-no-oop.md) |
| 0022 | [Repository Layer: Soft-Delete + Audit Discipline](0022-repository-layer-soft-delete-audit-discipline.md) |
| 0023 | [UX Redesign — Information Architecture Consolidation + Interaction Model](0023-ux-redesign-information-architecture.md) |
| 0024 | [Liability Accounts and Credit Limit](0024-liability-accounts-and-credit-limit.md) |
| 0025 | [User Preferences and Income Anchor](0025-user-preferences-and-income-anchor.md) |
| 0026 | [Quick-add FAB Visibility Scope](0026-fab-visibility-scope.md) |
| 0027 | [Frontend Toolchain Hardening — Local Tailwind, Stylelint, Partials, Visual Regression](0027-frontend-toolchain-hardening.md) |
| 0028 | [Ledger Segmented Control — Full Navigation, Not Partial Swap](0028-ledger-segmented-full-nav.md) |
| 0029 | [SQLite Connection Threading — `check_same_thread=False`, Per-Request Connection](0029-sqlite-connection-threading.md) |
| 0030 | [Shared Form Interaction Primitives](0030-shared-form-interaction-primitives.md) |
| 0031 | [Budget Page Composition v2: Income Anchor to Settings, Explicit "+ Rule" Create Affordance](0031-budget-page-composition-v2.md) |
| 0032 | [v2 Remote Deployment — Scaleway Stardust Warsaw + Scaleway Object Storage](0032-v2-remote-deployment-scaleway-stardust-warsaw.md) |
| 0033 | [v2 Authentication — Single-User Passkey (WebAuthn) + Fallback Password](0033-v2-auth-single-user-passkey.md) |
| 0034 | [v2 SQLite Durability — Continuous Replication via Litestream to Scaleway Object Storage](0034-v2-sqlite-replication-litestream.md) |
| 0035 | [v2 Infrastructure as Code — Terraform (Scaleway Provider) + Cloud-Init Bootstrap](0035-v2-infrastructure-as-code-terraform.md) |
| 0036 | [v2 Reverse Proxy & TLS — Caddy with Automatic HTTPS](0036-v2-reverse-proxy-caddy-auto-tls.md) |
| 0037 | [v2 Deployment Pipeline — GitHub Actions SSH Deploy with Immutable Image Tags](0037-v2-github-actions-deploy-pipeline.md) |
| 0038 | [Recurring Rules — Standalone Lifecycle with `next_due` + Direct Promotion](0038-recurring-standalone-lifecycle.md) (supersedes ADR-0013; amends ADR-0012) |
| 0039 | [Budget "Left to Spend per Day" Includes Recurring Commitments](0039-budget-daily-spend-includes-recurring.md) (amends ADR-0025 §F4.6, ADR-0038) |
| 0040 | [Modal Dismissal Fires on Form Submit Only, Not Side-Effect HTMX Requests](0040-modal-dismissal-scope.md) (amends ADR-0030 §5) |
| 0041 | [Budget "Period" is Last-Anchor-Income to Next-Anchor-Income, Not Calendar Month](0041-budget-period-anchor-window.md) (amends ADR-0025 §F4.6, ADR-0039) |
| 0042 | [Forecast — Budget Overlay for Unaccounted Expected Spend](0042-forecast-budget-overlay.md) (supersedes ADR-0015 §Alternatives in part) |
| 0043 | [Forecast Surface — Monthly Horizon + Breakdown Table](0043-forecast-tab-monthly-horizon-and-table.md) (amends ADR-0015) |
| 0045 | [Recurring Rules — Formula-Derived Amount (Percentage of Other Rules)](0045-recurring-formula-amount.md) (amends ADR-0013, ADR-0038) |
| 0046 | [Recurring Overrides — Soft-Consume on Promotion (Not Delete)](0046-recurring-override-soft-consume.md) (amends ADR-0038 §Promotion-flow step 6e) |
| 0047 | [Recurring Formula — Linear Combination of Terms + Chained Formulas](0047-recurring-formula-linear-combination-and-chaining.md) (supersedes ADR-0045 §Decision) |
