# ADR-0024 — Liability Accounts and Credit-Card Modelling

**Status**: accepted (2026-10-25)

**Context**

[ADR-0010](0010-account-model-free-text-type.md) kept `accounts.type` as an
optional **free-text label** so users can group accounts in the UI without
schema churn. That decision was explicit about one thing: *no business logic
branches on type*. The label is descriptive, not behavioural.

The product now needs a second shape of account — a **credit card** — with
semantics that are not just descriptive:

- The account has a **credit limit** (not an opening balance of positive money).
- Each spend reduces available credit; the outstanding balance is a debt.
- The outstanding balance must **reduce the overall fortune total** rather
  than add to it.

Collapsing "liability" into free-text `type` would re-introduce the exact
anti-pattern ADR-0010 rejected: code paths that `if account.type == "credit_card": …`
scattered across services, fragile to typos and to future variants
(loans, mortgages, lines of credit).

The existing arithmetic already handles "negative balance subtracts from
fortune" naturally — [ADR-0008](0008-transaction-amount-sign-and-direction.md)
makes an `expense` leg contribute `-amount` to the account, and the fortune
aggregator in `src/budget_planner/web/routers/home.py` sums all live account
balances. A credit-card expense therefore produces a negative balance that
reduces fortune without any new arithmetic. The real gaps are:

1. A way to **classify** an account as a liability, orthogonal to its
   descriptive label.
2. A **credit limit** field so the UI can show available credit, utilization,
   and over-limit warnings.
3. A fortune presentation that makes the liability contribution **legible**
   (today it is numerically correct but invisible as a single net number).

**Decision**

1. **Behaviour-affecting classification is a separate column, not `type`.**
   Add a new boolean column `accounts.is_liability` with a CHECK constraint
   `is_liability IN (0, 1)` and a default of `0`. `type` keeps its free-text
   semantics per ADR-0010 and continues to carry descriptive labels
   (`"bank"`, `"cash"`, `"brokerage"`, `"visa"`, …). This ADR **supersedes
   ADR-0010 in part**: ADR-0010 remains authoritative for *descriptive*
   typing; this ADR is authoritative for *behavioural* classification. The
   two coexist cleanly because they describe orthogonal concerns.

2. **Credit limit is a nullable integer in minor units.** Add
   `accounts.credit_limit_minor INTEGER` with a CHECK constraint
   `credit_limit_minor IS NULL OR credit_limit_minor > 0`. The column is
   only semantically meaningful when `is_liability = 1`; the DB stays
   permissive (consistent with the existing nullable `type`), the UI
   enforces presence when the user ticks the liability checkbox. Minor-unit
   storage matches `opening_balance` and all other amounts
   (ADR-0008 convention).

3. **Fortune aggregation is a reporting split, not an arithmetic change.**
   The dashboard and the accounts page display three figures:
   - **Assets** = Σ `derive_balance(a)` over live accounts with `is_liability = 0`.
   - **Liabilities** = Σ |`derive_balance(a)`| over live accounts with `is_liability = 1`.
   - **Net worth** = Assets − Liabilities.
   This is numerically identical to the current single sum (a negative
   balance already subtracts), so `signed_legs(...)` in
   `src/budget_planner/services/balance.py` is untouched. The split is a
   presentation concern handled by a new service module
   (`src/budget_planner/services/fortune.py`); `derive_balance` and
   `account_stats` stay as-is.

4. **No new transaction direction.** Payments from a bank account to a
   credit-card account use the existing `transit` direction
   ([ADR-0008](0008-transaction-amount-sign-and-direction.md),
   [ADR-0009](0009-transit-single-row-model.md)) — the negative leg on the
   bank and the positive leg on the credit-card both fall out of
   `signed_legs(...)`. Transits are still restricted to same-currency
   accounts (F7.5).

5. **Soft limit enforcement.** A transaction that would push the balance
   past `-credit_limit_minor` is **not** rejected. The service and
   repository layers do not know about the limit. The UI renders:
   - a utilization strip on the account card
     (`Limit X · Available Y · Z% used`),
   - a non-blocking "over limit by …" badge when
     `derive_balance(a) < -a.credit_limit_minor`,
   - an optional preview on the transaction form when the chosen account is
     a liability.
   Rationale: real cards allow over-limit spending (with fees); the planner
   is a planning aid, not a bank. Blocking at the service layer would also
   break reconciliation adjustments.

6. **ADR-0010 is superseded in part.** ADR-0010 remains the reference for
   descriptive `type`; cross-reference both ways in the ADR index.

**Consequences**

- One new boolean column (`is_liability`) and one nullable integer column
  (`credit_limit_minor`) on `accounts`. Both backfill cleanly on existing
  rows (`is_liability = 0`, `credit_limit_minor = NULL`).
- One new service module (`services/fortune.py`) extracts the aggregation
  currently duplicated across `web/routers/home.py` and
  `web/routers/accounts.py`. Both routers call the new service after the
  change.
- `derive_balance`, `account_stats`, `signed_legs`, and the entire category
  / direction model remain untouched; ADR-0008 still holds verbatim.
- Dashboard, accounts index, account card, and account form templates all
  change. The transaction form picks up an optional soft-warning preview.
- Future liability variants (loans, mortgages, overdraft facilities) reuse
  the same boolean flag and the same reporting split without further ADRs,
  provided they do not require new arithmetic. New arithmetic would need a
  follow-up ADR.
- Seed data gains one demo credit-card account so `just seed` exercises the
  split.

**Alternatives Considered**

- **Make `type` an enum**. Direct conflict with ADR-0010; also ties
  behavioural classification to a label that users want to customise.
  Rejected.
- **Sentinel string on `type`** (`type == 'credit_card'` triggers liability
  logic). Fragile to typos, hard to extend to other liability shapes, and
  smuggles behaviour into free-text — exactly what ADR-0010 forbade.
  Rejected.
- **Hard-block over-limit transactions at the service layer**. Breaks
  reconciliation (adjustment direction has to be allowed through) and
  prevents legitimate "I just overspent, let me record it" flows.
  Rejected.
- **Separate `liabilities` table**. Doubles the model (two tables,
  parallel repos, split queries). The behaviour differs by one boolean and
  one amount cap, so a single table is cleaner. Rejected.
- **Negate the balance for liabilities in the aggregator** (treat liability
  balance as positive debt and subtract). Mathematically equivalent to the
  "sum all balances" approach, but requires the aggregator to know about
  account kinds. Keeping aggregation balance-sign-driven leaves ADR-0008 as
  the single arithmetic authority. Rejected in favour of the split as a
  pure *reporting* grouping.
