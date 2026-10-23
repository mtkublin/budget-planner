# T-026 — Reconciliation Service

> Phase 2 — Services. Status: pending.

## Purpose

Given a user-supplied real-world account balance (from their bank), compute `delta = actual - derived` and insert a **signed** `adjustment`-direction transaction under the seeded `Reconciliation` category so the derived balance now equals the actual (ADR-0011). The adjustment is the only route by which a signed-amount transaction enters the system (ADR-0008 exception).

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-012 Seed data migration](../phase-1/T-012-seed-data-migration.md) — seeds the `Reconciliation` category (`direction=adjustment`, `is_system=True`).
  - [T-013 Repositories](../phase-1/T-013-repository-layer.md) — `repositories/accounts.py`, `repositories/categories.py`, `repositories/transactions.py`.
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `Account`, `Category`, `NewTransaction`, `Transaction`.
- Upstream Phase 2:
  - [T-021 Balance service](T-021-balance-service.md) — `derive_balance(...)`.
- ADRs:
  - [ADR-0011 Derived balance, snapshots, reconciliation](../../adr/0011-derived-balance-snapshots-reconciliation.md) — the whole flow.
  - [ADR-0008 Transaction amount sign & direction](../../adr/0008-transaction-amount-sign-and-direction.md) — adjustment is the only signed direction.
  - [ADR-0019 Soft delete + audit log](../../adr/0019-soft-delete-and-audit-log.md).
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
- Repository functions consumed:
  - `repositories.accounts.find_by_id(conn, account_id) -> Account | None`
  - `repositories.categories.find_system(conn, name="Reconciliation") -> Category | None`
  - `repositories.transactions.create(conn, NewTransaction) -> Transaction`

## Deliverables

- Module path: `src/budget_planner/services/reconciliation.py`
- Test module path: `tests/unit/services/test_reconciliation.py`
- Public function signatures:

```python
from __future__ import annotations

import datetime as dt
import sqlite3

from budget_planner.domain.transactions import Transaction


def reconcile(
    conn: sqlite3.Connection,
    account_id: int,
    actual_balance_minor: int,
    today: dt.date,
    note: str | None = None,
) -> Transaction: ...
```

`today` is injected (not read from `datetime.today()` inside the service) so tests are deterministic.

## Algorithm / step-by-step

```
1. account = repositories.accounts.find_by_id(conn, account_id)
   if account is None: raise AccountNotFoundError
   if account.deleted_at is not None: raise CannotReconcileDeletedAccountError

2. derived = services.balance.derive_balance(conn, account_id)   # as_of today omitted → "now"

3. delta = actual_balance_minor - derived      # SIGNED. May be positive, negative, or zero.

4. if delta == 0:
      raise NoAdjustmentNeededError
      # Rationale: inserting a zero-amount txn violates ADR-0008's `amount != 0`
      # validation and clutters the log. Router renders a friendly "already in
      # sync" message.

5. category = repositories.categories.find_system(conn, "Reconciliation")
   if category is None: raise MissingSystemCategoryError
   assert category.direction == Direction.adjustment

6. description = (
      f"auto-reconciliation {today.isoformat()}"
      if note is None else
      f"auto-reconciliation {today.isoformat()} — {note}"
   )

7. new_txn = NewTransaction(
      operation_date   = today,
      category_id      = category.id,
      account_id       = account_id,
      dest_account_id  = None,
      amount           = delta,                 # SIGNED (ADR-0008 adjustment exception)
      description      = description,
      promoted_from_planned_id = None,
   )

8. with conn as a single transaction:
      txn = repositories.transactions.create(conn, new_txn)
      # repository writes audit('transaction', txn.id, 'create', None, new_json)

9. Return txn.
```

Post-condition: `derive_balance(conn, account_id, as_of_date=today) == actual_balance_minor`.

## Interfaces / contracts

### Signed-amount convention for `direction=adjustment`

Repeated here because it is the entire point of this service:

| Case | Stored `amount` | Effect on derived balance |
|------|-----------------|---------------------------|
| Actual > derived (bank has more than our books expect) | **positive** delta | `+amount` on `account_id` |
| Actual < derived | **negative** delta | `+amount` on `account_id` (amount already negative) |
| Actual == derived | — | `NoAdjustmentNeededError`; no row inserted |

The derivation side (`services.balance.signed_legs`) treats `adjustment` as pass-through: whatever sign is in `amount`, that is the sign applied to the balance. This closes the loop.

```python
def reconcile(conn, account_id, actual_balance_minor, today, note=None) -> Transaction:
    """
    Compute delta = actual - derived and insert a signed adjustment txn so
    derive_balance equals actual.

    Preconditions:
      - account exists and is not soft-deleted.
      - delta != 0 (zero raises NoAdjustmentNeededError).
      - Seeded 'Reconciliation' category is present (ADR-0012/T-012).

    Post-condition:
      services.balance.derive_balance(conn, account_id, today) == actual_balance_minor

    Mutations happen inside a single DB transaction (including the audit
    log entry written by repositories.transactions.create).
    """


class AccountNotFoundError(LookupError): ...
class CannotReconcileDeletedAccountError(RuntimeError): ...
class NoAdjustmentNeededError(RuntimeError): ...
class MissingSystemCategoryError(RuntimeError): ...
```

## Test strategy

Fixtures: SQLite temp DB with Phase 1 schema; T-012 seed data loaded (so the `Reconciliation` category exists).

Seed state per test:

```
accounts:  1 Checking PLN opening=100_000
txns:      2026-01-10 income  Salary   30_000   -> derived == 130_000
```

Cases:

1. **Positive delta** (`actual=140_000, derived=130_000`): service inserts a txn with `amount == +10_000`, direction=adjustment. Post `derive_balance == 140_000`.
2. **Negative delta** (`actual=120_000`): txn with `amount == -10_000`. Post `derive_balance == 120_000`.
3. **Zero delta** (`actual=130_000`): raises `NoAdjustmentNeededError`; no row inserted; audit log unchanged.
4. **Unknown account**: raises `AccountNotFoundError`.
5. **Deleted account**: soft-delete account 1 then reconcile → `CannotReconcileDeletedAccountError`.
6. **System category missing**: delete the seeded Reconciliation row (hard; test-only) → `MissingSystemCategoryError`. (Verifies the service fails loudly rather than inventing a category.)
7. **Audit entry written**: assert `audit_log` has exactly one new row with `entity_type='transaction'`, `operation='create'`, `prev_json IS NULL`, and `new_json` containing the signed amount.
8. **Description formatting**: without note → `"auto-reconciliation 2026-10-23"`; with note `"bank mobile app"` → `"auto-reconciliation 2026-10-23 — bank mobile app"`.
9. **`operation_date` is `today`**: injected date is used verbatim; no `datetime.now()` sneakery.
10. **Post-condition round-trip**: for an arbitrary `actual_balance_minor`, after `reconcile(...)`, `derive_balance == actual_balance_minor`. Property-test over a handful of integers.
11. **Repeated reconciliation**: run `reconcile(..., 140_000)` twice — the second call sees `derived==140_000` already and raises `NoAdjustmentNeededError` (no duplicate adjustment).
12. **Interaction with transit**: account 1 is a transit source for a 20_000 transit on `2026-01-15` (dest = another PLN account). Verify `derive_balance` reflects the transit, then reconcile to a specific actual and confirm the adjustment is just the delta.
13. **Negative balance accounts**: start with `opening_balance=0` and reconcile to `-50_000` (credit card style). Adjustment stored as `-50_000`.
14. **Idempotency failure**: patch the repository to raise after inserting the row but before commit → full rollback; no partial state.

Mocking boundaries: none, except the rollback test (patch `repositories.transactions.create` to raise mid-transaction).

## Risks & gotchas

- **Signed amount is the whole exception.** Elsewhere `amount` is positive and sign is derived from `direction`. For `adjustment`, the stored `amount` carries the sign directly. Any schema CHECK constraint on `amount > 0` must be gated by `direction != 'adjustment'` (verify in T-011). Service tests should include a `amount < 0` case explicitly (test 2).
- **"Direction=adjustment" is the only path signing is allowed.** The service hard-codes the system `Reconciliation` category. If a user ever creates another category with `direction=adjustment`, that is still legal in the schema but this service always uses the seeded one. Document.
- **`today` injection**: do not read `datetime.date.today()` inside the service. Pass from the router (computed in `Europe/Warsaw`, ADR-0007). Tests become trivial.
- **Snapshot-based drift**: snapshots (`account_snapshots`) are **advisory**, not an input to reconciliation. A snapshot taken a week ago is irrelevant to today's `delta`. ADR-0011 is explicit; reinforce by not accepting a snapshot id in this service's signature.
- **Zero amount**: never insert a zero-amount txn. The schema CHECK should also reject it (`amount != 0`). The service's `NoAdjustmentNeededError` is a nicer UX before the schema trips.
- **Rounding**: `actual_balance_minor` is an integer. `derived` is an integer. `delta` is an integer. No `Decimal` here.
- **Cross-currency**: the actual balance is in the account's own currency (ADR-0006). The service does not touch FX. If a user mis-enters a value in base currency, that is a UI validation concern, not this service's.
- **Audit single-transaction guarantee**: `repositories.transactions.create` writes to the audit log inside the same DB transaction. Any future "silent audit" refactor must preserve this. The rollback test (14) is the regression guard.

## Handoff notes

Phase 3 consumers:

- **Accounts router (T-032)**:
  - `GET /accounts/{id}/reconcile` — render form prefilled with the current derived balance for the user to adjust.
  - `POST /accounts/{id}/reconcile` — call `reconcile(conn, id, form.actual_balance_minor, today, form.note)` → redirect to the account page with a flash message naming the delta. Zero-delta responses render "already in sync" without creating a txn.
- **Analytics / budget routers**: adjustments are excluded from income/expense statistics (filter `direction != 'adjustment'`). The budget service (T-024) and analytics (T-038) already apply this filter via the repository.
- No router calls this service outside of `accounts`.
