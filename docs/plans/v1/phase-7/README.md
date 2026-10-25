# Phase 7 — Liability Accounts (Credit Cards)

> Status: pending (docs round of this phase is T-080; code starts at T-081). Scope: accounts surface + fortune reporting. No change to transaction direction, category, or FX arithmetic.

## Overview

Phase 7 introduces a second shape of account — a **credit card** — with semantics beyond the free-text label governed by [ADR-0010](../../../adr/0010-account-model-free-text-type.md):

- A **credit limit** (not an opening balance of positive money).
- Each spend reduces available credit; the outstanding balance is a debt.
- The outstanding balance must **reduce the overall fortune total** rather than add to it.

The existing arithmetic already handles "negative balance subtracts from fortune" naturally — [ADR-0008](../../../adr/0008-transaction-amount-sign-and-direction.md) emits a negative leg for `expense` and the fortune aggregator (`web/routers/home.py:40-44`) sums all live account balances. A credit-card expense produces a negative balance that reduces fortune without any new arithmetic. The real gaps are:

1. A way to **classify** an account as a liability, orthogonal to its descriptive label.
2. A **credit limit** field so the UI can show available credit, utilization, and over-limit warnings.
3. A fortune presentation that makes the liability contribution **legible** (today it is numerically correct but invisible as a single net number).

Decision: see [`ADR-0024`](../../../adr/0024-liability-accounts-and-credit-limit.md) — adds `accounts.is_liability` (boolean) + `accounts.credit_limit_minor` (nullable positive integer), supersedes ADR-0010 **in part** for behavioural classification only. Requirement: [F2.1a](../../../requirements.md#22-account-management).

Fortune reporting splits into:

```
Assets      = Σ derive_balance(a) over live accounts with is_liability = 0
Liabilities = Σ |derive_balance(a)| over live accounts with is_liability = 1
Net worth   = Assets − Liabilities
```

Mathematically identical to the current single sum (a negative balance already subtracts). The split is a presentation concern handled by a new `services/fortune.py`; `derive_balance`, `account_stats`, `signed_legs`, and ADR-0008 are untouched.

Primary surfaces:

| Change | Where |
|---|---|
| New boolean `is_liability` + nullable `credit_limit_minor` on `accounts` | `migrations/0004_add_liability_columns.sql` |
| New service `compute_fortune(conn, settings) -> FortuneTotals` | `src/budget_planner/services/fortune.py` |
| Checkbox + conditional credit-limit input on the account form | `web/templates/partials/accounts/_form.html` |
| Utilization strip + over-limit badge on the account card | `web/templates/partials/accounts/_card.html` |
| Assets / Liabilities / Net worth block on the dashboard + accounts index | `web/templates/home/index.html`, `web/templates/accounts/index.html` |
| Optional soft-warning preview when the chosen account on the transaction form is a liability | `web/templates/partials/transactions/_form.html` |
| Seeded demo credit-card account + e2e journey | `src/budget_planner/db/seed.py`, `tests/e2e/` |

## Task table

| ID | Task | Dep |
|---|---|---|
| T-080 | ADR-0024 + requirements F2.1a + Phase 7 docs scaffolding (docs only) | — |
| T-081 | Migration `0004_add_liability_columns.sql` | T-080 |
| T-082 | Domain + repository (`Account`, `NewAccount`, `PatchAccount`; repo CRUD) | T-081 |
| T-083 | Fortune service `services/fortune.py` + both routers | T-082 |
| T-084 | Web form + templates (checkbox, limit input, utilization strip, net-worth split) | T-083 |
| T-085 | Transaction-form soft warning for liability accounts | T-084 |
| T-086 | Seed demo credit-card account + e2e journey | T-084 |

## Dependency map

- **T-080** unblocks every code task; it is the docs round itself.
- **T-081** → **T-082** → **T-083** (vertical slice through the new columns up to the aggregator).
- **T-084** closes the UI loop and is the first visible payoff.
- **T-085** and **T-086** are independent of each other and may land in parallel after T-084.

Parallel-safe set once T-084 is in: `{T-085, T-086}`.

Est. size: each task ≤ 1 day; whole phase ~1 week sequential, ~4 days with fan-out.

## Exit criteria (verification checklist)

Local, end-to-end, no new tooling:

- [ ] `just migrate` applies `0004_add_liability_columns.sql` cleanly on a fresh DB and idempotently on an existing one.
- [ ] `just seed` yields a working "Visa (PLN)" demo credit-card account with `credit_limit_minor = 1_000_000`.
- [ ] `just test` — new unit + integration tests pass. Coverage stays ≥ 90%.
- [ ] `just lint` + `just typecheck` + `just ci` all green.
- [ ] Manual: `just dev` → `/accounts/new`, tick "credit card", enter limit `10,000.00`, save → account card shows `Limit 10,000.00 · Available 10,000.00 · 0% used`.
- [ ] Add an `expense` of `500.00` on the Visa account → card balance `-500.00`; utilization strip reads `Available 9,500.00 · 5% used`; home dashboard shows `Assets − 500.00 = Net worth`.
- [ ] Create a `transit` from a bank account to the Visa for `500.00` → card balance `0.00`; utilization `0%`; liabilities line returns to `0.00`.
- [ ] Add an expense that pushes the balance below `-credit_limit_minor` → over-limit badge renders, the transaction submits successfully (soft enforcement).
- [ ] `docs/CHANGELOG.md` entry for the phase landing day.

## See also

- Decision: [`docs/adr/0024-liability-accounts-and-credit-limit.md`](../../../adr/0024-liability-accounts-and-credit-limit.md)
- Superseded (in part): [`docs/adr/0010-account-model-free-text-type.md`](../../../adr/0010-account-model-free-text-type.md) — descriptive `type` unchanged.
- Related arithmetic authority (untouched): [`docs/adr/0008-transaction-amount-sign-and-direction.md`](../../../adr/0008-transaction-amount-sign-and-direction.md).
- Sibling phase: [`../phase-9/`](../phase-9/) — Left Daily Spend (second post-v1-polish additive phase, same shape of docs-first → migration → domain/repo → service → UI → tests).
- Prior phase: [`../phase-6/`](../phase-6/) — UX redesign that defined the current accounts + dashboard composition.
