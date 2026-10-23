# T-023 — Planned Log Service

> Phase 2 — Services. Status: pending.

## Purpose

Produce a unified "planned log" view that UNIONs persisted `planned_transactions` rows with the virtual occurrences generated from active `recurring_rules` (ADR-0013). Also implements the **manual** planned → actual promotion (ADR-0012): insert a `transactions` row with `promoted_from_planned_id` set, stamp `planned_transactions.promoted_to_txn_id`, and record both audit entries inside a single DB transaction.

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-013 Repositories](../phase-1/T-013-repository-layer.md) — `repositories/planned.py`, `repositories/recurring.py`, `repositories/transactions.py`.
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `PlannedTransaction`, `NewTransaction`, `PlannedFilter`.
- Upstream Phase 2:
  - [T-022 Recurring occurrence generator](T-022-recurring-occurrence-generator.md) — `expand(...)`.
- ADRs:
  - [ADR-0012 Planned manual promotion](../../adr/0012-planned-manual-promotion.md).
  - [ADR-0013 Recurring virtual occurrences & overrides](../../adr/0013-recurring-virtual-occurrences-and-overrides.md).
  - [ADR-0008 Transaction amount sign & direction](../../adr/0008-transaction-amount-sign-and-direction.md).
  - [ADR-0019 Soft delete + audit log](../../adr/0019-soft-delete-and-audit-log.md).
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
- Repository functions consumed:
  - `repositories.planned.list_filtered(conn, filters: PlannedFilter) -> list[PlannedTransaction]`
  - `repositories.planned.find_by_id(conn, planned_id) -> PlannedTransaction | None`
  - `repositories.planned.set_promoted_link(conn, planned_id, txn_id) -> PlannedTransaction`
  - `repositories.recurring.list_active_rules(conn, in_range=(a, b)) -> list[RecurringRule]`
  - `repositories.recurring.list_overrides_for_rule(conn, rule_id) -> list[RecurringRuleOverride]`
  - `repositories.transactions.create(conn, NewTransaction) -> Transaction`

## Deliverables

- Module path: `src/budget_planner/services/planned.py`
- Test module path: `tests/unit/services/test_planned.py`
- Public function signatures:

```python
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from budget_planner.domain.planned import PlannedFilter, PlannedTransaction
from budget_planner.domain.transactions import NewTransaction, Transaction
from budget_planner.services.recurring import Occurrence


@dataclass(frozen=True, slots=True)
class PlannedView:
    kind: str                       # "persisted" | "virtual"
    operation_date: dt.date
    account_id: int
    dest_account_id: int | None
    category_id: int
    amount_minor: int
    description: str
    persisted_id: int | None        # None for virtual
    recurring_rule_id: int | None   # set on virtual rows + rule-linked persisted rows
    occurrence_date: dt.date | None # canonical date (useful for overrides UI)
    is_overridden: bool
    is_promoted: bool               # persisted only; always False for virtual


@dataclass(frozen=True, slots=True)
class PromotionEdits:
    operation_date: dt.date | None = None
    amount_minor: int | None = None
    description: str | None = None


def list_planned(
    conn: sqlite3.Connection,
    filters: PlannedFilter,
) -> tuple[PlannedView, ...]: ...


def promote_to_actual(
    conn: sqlite3.Connection,
    planned_id: int,
    edits: PromotionEdits,
) -> Transaction: ...
```

## Algorithm / step-by-step

### `list_planned` — UNION persisted + virtual

```
1. Resolve the date window from filters.operation_date_from/to; both default
   to the current month if absent (document in docstring).
2. Pull persisted planned rows: repositories.planned.list_filtered(conn, filters).
   - These include rows with recurring_rule_id (promoted/edited occurrences
     materialised into planned_transactions) AND one-offs.
3. Pull active recurring rules intersecting the window.
   For each rule r:
     overrides = repositories.recurring.list_overrides_for_rule(conn, r.id)
     occs = services.recurring.expand(r, overrides, range_start, range_end)
     - Deduplicate against step 2: if a persisted row has
       (recurring_rule_id == r.id AND occurrence_date == occ.occurrence_date),
       prefer the persisted row (user has materialised that occurrence).
     Emit PlannedView(kind="virtual") for the remaining occurrences.
4. Map step 2 rows to PlannedView(kind="persisted").
5. Apply remaining filter predicates (category_id, account_id, description
   substring, amount range) — in-process filtering is simpler and the record
   volume is bounded.
6. Sort by (operation_date ASC, kind='persisted' first, persisted_id ASC) for
   deterministic UI ordering.
7. Return tuple.
```

Dedup key: `(recurring_rule_id, occurrence_date)` on the persisted side. The `occurrence_date` column is only populated on persisted rows that originated from a rule; one-offs carry `NULL`.

### `promote_to_actual` — manual promotion

```
1. planned = repositories.planned.find_by_id(conn, planned_id)
   if planned is None: raise PlannedNotFoundError
   if planned.promoted_to_txn_id is not None: raise AlreadyPromotedError
   if planned.deleted_at is not None: raise CannotPromoteDeletedError

2. Build NewTransaction by merging planned defaults with edits:
      operation_date = edits.operation_date or planned.operation_date
      amount_minor   = edits.amount_minor   or planned.amount_minor
      description    = edits.description    or planned.description
      account_id, dest_account_id, category_id come from planned (immutable
      on promotion — a currency change would require creating a new planned
      row, not editing on promote).

3. With conn as a single transaction (BEGIN ... COMMIT):
      a. txn = repositories.transactions.create(conn, new_txn_with promoted_from_planned_id=planned_id)
         -> repository writes audit('transaction', txn.id, 'create', None, new_json)
      b. repositories.planned.set_promoted_link(conn, planned_id, txn.id)
         -> repository writes audit('planned_transaction', planned_id, 'update', prev_json, new_json)
   On any exception: rollback, re-raise.

4. Return txn.
```

Virtual occurrences cannot be promoted directly (they have no `planned_id`). The web layer first materialises a virtual occurrence into a `planned_transactions` row (via a separate `materialise_occurrence` helper if needed — see Handoff notes) and then promotes the resulting persisted row. Deferred to T-034 web layer; this service only operates on persisted ids.

### Validation during promotion

- `amount_minor != 0`.
- If the resulting direction is in `{income, expense, transit}`, `amount_minor > 0`.
- If direction is `transit`, `dest_account_id is not None` and (lookup from accounts repo) `source.currency == dest.currency` (ADR-0006). Service calls into `repositories.accounts.find_by_id` for both.
- If direction is `adjustment`, promotion is not supported (reconciliation is its own flow — T-026). Raise `UnsupportedDirectionError`.

## Interfaces / contracts

```python
def list_planned(conn, filters) -> tuple[PlannedView, ...]:
    """
    Deterministic UNION of persisted planned rows and virtual recurring
    occurrences for the window described in `filters`. Dedup key for
    rule-linked rows: (recurring_rule_id, occurrence_date). Virtual rows
    carry persisted_id=None. Pure w.r.t. the given DB snapshot.
    """


def promote_to_actual(conn, planned_id, edits) -> Transaction:
    """
    Insert a transactions row with promoted_from_planned_id=planned_id and
    stamp planned_transactions.promoted_to_txn_id. Both mutations and both
    audit entries happen in a single DB transaction.

    Raises:
      PlannedNotFoundError, AlreadyPromotedError, CannotPromoteDeletedError,
      UnsupportedDirectionError, ValidationError.
    """
```

```python
class PlannedNotFoundError(LookupError): ...
class AlreadyPromotedError(RuntimeError): ...
class CannotPromoteDeletedError(RuntimeError): ...
class UnsupportedDirectionError(RuntimeError): ...
class ValidationError(ValueError): ...
```

## Test strategy

Fixtures: SQLite temp DB with the Phase 1 schema, seeded with:

```
accounts:  1 Checking PLN, 2 Savings PLN
categories: 10 Groceries (expense), 11 Rent (expense), 12 Transit (transit),
            13 Salary (income), 14 Reconciliation (adjustment)
recurring_rules:
   R1 cadence=monthly  start=2026-01-05  default_amount=200_000 (rent)
   R2 cadence=yearly   start=2026-07-04  default_amount= 50_000 (insurance)
recurring_rule_overrides:
   O1 rule=R1 occurrence_date=2026-03-05 state=skipped
   O2 rule=R1 occurrence_date=2026-04-05 state=overridden amount_override=210_000
planned_transactions:
   P1 one-off 2026-02-20 expense category=10 Groceries amount=12_345
   P2 recurring-linked 2026-01-05 rule_id=R1 occurrence_date=2026-01-05 amount=200_000
      (user already materialised this occurrence to tweak the description)
```

Cases:

1. **UNION happy path**: `list_planned(filters=range Jan..Jun 2026)` returns P1, P2, plus virtual R1 for Feb/May/Jun (March skipped, April overridden to 210_000), plus any R2 if the window reaches July. Assert dedup prefers P2 over the virtual Jan occurrence.
2. **Skip removes a virtual occurrence**: no row for `2026-03-05`.
3. **Overridden virtual carries overridden amount**: April row has `amount_minor == 210_000` and `is_overridden == True`.
4. **Window clip**: filters narrowed to `2026-04-01..2026-04-30` returns just the overridden April row + anything persisted in April.
5. **Non-rule filters**: `category_id=10` returns only P1.
6. **Deterministic ordering**: equal dates sort persisted-first; verify by injecting a persisted P3 with same date as a virtual occurrence.
7. **Deactivated rule**: flip `R1.active=False`; `list_planned` returns no virtual R1 rows.

Promotion:

8. **Happy path, no edits**: `promote_to_actual(P1.id, PromotionEdits())` → new transactions row with amount/date/description from P1, `promoted_from_planned_id=P1.id`; P1 updated with `promoted_to_txn_id=txn.id`; two audit rows exist.
9. **Edits override amount and date**: promotion with `PromotionEdits(amount_minor=11_000, operation_date=2026-02-22)` → txn carries those values; P1's underlying row is unchanged (immutable except for `promoted_to_txn_id`).
10. **Double-promote blocked**: second call raises `AlreadyPromotedError`.
11. **Promote deleted planned**: soft-delete P1 then promote → `CannotPromoteDeletedError`.
12. **Promote adjustment**: fake planned row with Reconciliation category → `UnsupportedDirectionError`.
13. **Transit validation**: planned transit with mismatched currencies → `ValidationError`.
14. **Audit entries present**: assert `audit_log` has one `create` for the txn and one `update` for the planned row, both with the same `changed_at` wall-clock second (same transaction).
15. **Rollback on failure**: monkeypatch `repositories.planned.set_promoted_link` to raise mid-transaction; assert no `transactions` row persisted and no partial audit rows exist.

Mocking boundaries: none for list_planned (pure DB). For the rollback test, patch the specific repository call to raise.

## Risks & gotchas

- **Dedup bug — key must be `(rule_id, occurrence_date)`, not `operation_date`**. If a user has shifted the operation date on a materialised occurrence, the virtual occurrence still refers to the canonical `occurrence_date`. Matching on operation_date would double-list the row.
- **Two mutations in one DB transaction**. If either side fails, both must roll back. Wrap in `with conn:` (SQLite's context manager commits on success, rolls back on exception). Audit writes inside the repositories must participate in the same transaction (no autocommit).
- **Virtual-row amount for transit**. The leg sign is not stored on the occurrence; it is derived at balance / forecast time from `category.direction`. Keep the UI-facing shape neutral (`amount_minor` positive for income/expense/transit).
- **Occurrence overrides vs persisted edits**. If a user materialises an occurrence into `planned_transactions` AND an override row exists for the same `(rule_id, occurrence_date)`, treat the persisted row as the source of truth and ignore the override. Document.
- **Pagination not required** at the service level. Volume is bounded by the window; the router may slice the tuple.
- **Promotion creates signed-amount from direction**: the actual transaction stores unsigned `amount` with direction driving sign at read time (ADR-0008). The service does not sign the amount at promotion time.

## Handoff notes

Phase 3 consumers:

- **Planned transactions router (T-034)**:
  - `GET /planned` → `list_planned(conn, filters_from_query_string)`.
  - `POST /planned/{id}/promote` → `promote_to_actual(conn, id, PromotionEdits.from_form(request))`.
  - A separate helper (likely in the same service) materialises a virtual occurrence into a `planned_transactions` row before promotion when the user confirms promotion on a virtual row directly — specify when T-034 lands; signature likely `materialise_virtual(conn, rule_id, occurrence_date) -> PlannedTransaction`.
- **Home dashboard (T-039)** calls `list_planned` with a 7-day forward window for the "next 7 days" tile.
- **Forecast service (T-025)** does **not** call this service; it talks to the recurring generator directly to avoid conflating virtual occurrences with user-materialised planned rows twice. (Explicit non-use is important — document.)
