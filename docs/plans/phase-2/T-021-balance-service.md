# T-021 — Balance Service

> Phase 2 — Services. Status: pending.

## Purpose

Derive an account's balance as a pure function of its `opening_balance` plus the signed sum of non-deleted transactions affecting it on or before a given date. Balance is **never stored** on the account; it is computed on every read (ADR-0011). This service is the single arithmetic authority consumed by UI, forecasting, and reconciliation.

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-013 Repositories](../phase-1/T-013-repository-layer.md) — `repositories/accounts.py`, `repositories/transactions.py`.
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `Account`, `Transaction`, `Direction`, `AccountStats`.
- ADRs:
  - [ADR-0008 Transaction amount sign & direction](../../adr/0008-transaction-amount-sign-and-direction.md) — signed-amount rules.
  - [ADR-0009 Transit single-row model](../../adr/0009-transit-single-row-model.md) — one row, two account legs.
  - [ADR-0011 Derived balance, snapshots, reconciliation](../../adr/0011-derived-balance-snapshots-reconciliation.md) — balance is derived.
  - [ADR-0007 Timezone handling](../../adr/0007-timezone-handling.md) — `operation_date` is naive `DATE`.
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
- Repository functions consumed:
  - `repositories.accounts.find_by_id(conn, account_id) -> Account | None`
  - `repositories.transactions.list_affecting_account(conn, account_id, as_of: date | None, include_deleted=False) -> list[Transaction]`
    (returns rows where `account_id == :id OR dest_account_id == :id` and `operation_date <= :as_of` when provided).
  - `repositories.transactions.aggregate_stats(conn, account_id, direction_filter: tuple[Direction, ...] | None) -> StatsAgg` (counts + sums, used by `account_stats`).

## Deliverables

- Module path: `src/budget_planner/services/balance.py`
- Test module path: `tests/unit/services/test_balance.py`
- Public function signatures:

```python
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from budget_planner.domain.accounts import Account, AccountStats
from budget_planner.domain.transactions import Transaction
from budget_planner.domain.enums import Direction


@dataclass(frozen=True, slots=True)
class SignedLeg:
    account_id: int
    amount_minor: int  # already signed


def derive_balance(
    conn: sqlite3.Connection,
    account_id: int,
    as_of_date: dt.date | None = None,
) -> int: ...


def signed_legs(txn: Transaction) -> tuple[SignedLeg, ...]: ...


def account_stats(
    conn: sqlite3.Connection,
    account_id: int,
) -> AccountStats: ...
```

## Algorithm / step-by-step

### `signed_legs` (helper, pure, no DB)

Given one `Transaction`, return the one or two signed legs it produces:

| `direction` | legs produced | signed amount |
|-------------|---------------|---------------|
| `income` | `(account_id, +amount)` | `+amount` |
| `expense` | `(account_id, -amount)` | `-amount` |
| `transit` | `(account_id, -amount)` and `(dest_account_id, +amount)` | source negative, destination positive |
| `adjustment` | `(account_id, +amount)` | `amount` is already signed (ADR-0008 exception); pass through unchanged |

Preconditions enforced by assertion (bugs upstream, not user errors):
- `direction ∈ {income, expense, transit}` → `amount > 0`.
- `direction == transit` → `dest_account_id is not None` and (checked by validation elsewhere) same currency.
- `direction == adjustment` → `dest_account_id is None`.

Returning a tuple (not a list) keeps the result immutable.

### `derive_balance`

```python
def derive_balance(conn, account_id, as_of_date=None):
    account = repositories.accounts.find_by_id(conn, account_id)
    if account is None:
        raise AccountNotFoundError(account_id)

    txns = repositories.transactions.list_affecting_account(
        conn, account_id, as_of=as_of_date, include_deleted=False,
    )
    delta = sum(
        leg.amount_minor
        for txn in txns
        for leg in signed_legs(txn)
        if leg.account_id == account_id
    )
    return account.opening_balance + delta
```

- `opening_balance` is the only stored anchor; everything else is reconstructed.
- `as_of_date is None` means "today's balance" — the repository leaves the date filter off entirely.

### `account_stats`

Returns a frozen dataclass carrying:

```python
@dataclass(frozen=True, slots=True)
class AccountStats:
    current_balance_minor: int
    txn_count: int
    avg_inflow_minor: int   # positive legs only, averaged over count of inflow legs
    avg_outflow_minor: int  # absolute value; average of magnitudes of outflow legs
    last_activity_date: dt.date | None
```

Computation:

1. Current balance via `derive_balance(conn, account_id)`.
2. Pull transactions once; iterate and partition into inflow / outflow legs for this account.
3. Averages: `int(round(sum / n))` using `ROUND_HALF_EVEN`; `0` when the partition is empty.
4. `last_activity_date = max(operation_date)` across all legs touching this account; `None` if empty.
5. Transit and adjustment legs count towards activity but are excluded from the inflow/outflow averages (they are not spend/income signals). Decision: inflow and outflow averages consider `direction ∈ {income, expense}` only; `transit` and `adjustment` contribute to `txn_count` and `last_activity_date` but not to the averages.

## Interfaces / contracts

```python
def derive_balance(
    conn: sqlite3.Connection,
    account_id: int,
    as_of_date: dt.date | None = None,
) -> int:
    """
    Return the derived balance in minor units of the account's own currency.

    Invariants:
      - Does not mutate.
      - Ignores soft-deleted transactions.
      - When `as_of_date is None`, includes every non-deleted txn.
      - For `transit`, both source (-) and destination (+) legs are applied;
        the right side is picked based on which side matches `account_id`.
      - For `adjustment`, the stored amount sign is passed through verbatim.
    """


def account_stats(conn, account_id) -> AccountStats:
    """Current balance + descriptive stats. Pure; no caching."""
```

```python
class AccountNotFoundError(LookupError): ...
```

## Test strategy

Use a seeded SQLite fixture that exercises each direction. Suggested fixture (minor units; account currency is PLN unless noted):

```
accounts:
  1  Checking      PLN  opening 100_000      # 1 000,00 PLN
  2  Savings       PLN  opening   0
  3  EUR Cash      EUR  opening  50_000      # unused by balance tests; currency isolation

txns (operation_date / category.direction / amount):
  2026-01-05  income       Checking               50_000
  2026-01-10  expense      Checking               20_000
  2026-01-15  transit      Checking → Savings     30_000
  2026-02-01  adjustment   Checking               -5_000   # reconciliation style
```

Cases to cover (≥ 90 % coverage required):

1. **Opening-balance-only**: new account, no txns → `derive_balance == opening_balance`.
2. **Income**: adds `+amount`.
3. **Expense**: subtracts `amount`.
4. **Transit source leg**: `derive_balance(Checking)` after the transit decreases by `30_000`.
5. **Transit destination leg**: `derive_balance(Savings)` after the transit increases by `30_000`.
6. **Adjustment positive and negative**: both signs pass through; `derive_balance(Checking)` after `-5 000` adjustment reflects the subtraction.
7. **`as_of_date` filter**: `derive_balance(Checking, as_of_date=2026-01-10)` equals `opening + 50_000 - 20_000`; the later transit + adjustment are excluded.
8. **Soft-deleted exclusion**: delete the income row; derived balance drops.
9. **Isolated accounts**: transactions on account 3 (EUR) do not affect the PLN account's balance.
10. **Multiple transit legs on same account**: both legs produce the right signed sum.
11. **Unknown account**: raises `AccountNotFoundError`.
12. **`account_stats` averages**: inflow/outflow averages ignore transit + adjustment legs; `txn_count` includes them; `last_activity_date` is the max.
13. **Empty history**: `account_stats` on a new account returns zeros + `None` last activity.

Fixtures:

- `conn` with `users`, `accounts`, `categories` (seed `income`, `expense`, `transit`, `adjustment` categories), `transactions` tables.
- `seed_txns(conn, rows)` helper for terse table-driven tests.

Mocking boundaries: none. This service is DB-only; test against the real schema.

## Risks & gotchas

- **Signed vs unsigned confusion**: the stored `amount` is positive for `income` / `expense` / `transit`. Only `adjustment` is signed. A regression where someone stores a negative `expense` would be caught by schema CHECK constraints (Phase 1), but the service should still fail loudly if asserted invariants break.
- **Transit filter on `account_id OR dest_account_id`**: easy to miss the OR branch and under-count destination balances. The repository function `list_affecting_account` encapsulates that filter; the service must not re-query with only `account_id`.
- **`as_of_date` boundary**: inclusive. A transaction dated exactly `as_of_date` is included. Document and test.
- **Rounding in `account_stats`**: use `Decimal` for averages, then quantise to minor units. Never divide ints in Python 3 then cast — the test assertions should use `Decimal` arithmetic to stay stable.
- **Timezone drift**: `operation_date` is a `date`. Comparing against `datetime.now()` or `today()` with a tz-aware timestamp is a classic bug. The service never produces timestamps; callers pass `date`.
- **Cross-currency balance aggregation is NOT this service's job**. This returns balance in the account's own currency. Aggregation across accounts into base currency belongs to the forecast / fortune services (T-025).

## Handoff notes

Phase 3 consumers:

- **Accounts router (T-032)** calls `derive_balance` + `account_stats` for the account list view and the per-account page.
- **Forecast router (T-037)** uses `derive_balance(conn, account_id)` without `as_of_date` to anchor "today" for each account before layering planned/recurring projections.
- **Reconciliation service (T-026)** calls `derive_balance` to compute the delta to insert as an adjustment.
- **Home dashboard (T-039)** sums `derive_balance` across all accounts (post FX conversion in T-025).
