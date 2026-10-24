# T-014 — Domain Types

> Phase 1 — Data Layer. Status: pending.

## Purpose

Pin down every persistence shape as a frozen Python dataclass plus a matching `New*` (create) / `Patch*` (update) DTO. Centralise enums (`Direction`, `Cadence`) and money helpers so repositories and services share a single vocabulary. Immutable by construction (ADR-0021).

## Inputs / prerequisites

- Upstream task: [`T-011-core-schema-migration.md`](T-011-core-schema-migration.md) — column list is the source of truth.
- ADRs:
  - [`../../adr/0006-multi-currency-model.md`](../../adr/0006-multi-currency-model.md) — currency on account; amounts in minor units of the account currency.
  - [`../../adr/0007-timezone-handling.md`](../../adr/0007-timezone-handling.md) — UTC `datetime` for metadata; `date` for `operation_date`.
  - [`../../adr/0008-transaction-amount-sign-and-direction.md`](../../adr/0008-transaction-amount-sign-and-direction.md) — amount is positive int except for `adjustment`.
  - [`../../adr/0013-recurring-virtual-occurrences-and-overrides.md`](../../adr/0013-recurring-virtual-occurrences-and-overrides.md) — recurring rule + override DTOs.
  - [`../../adr/0014-budget-flat-no-rollover-three-tier.md`](../../adr/0014-budget-flat-no-rollover-three-tier.md) — three budget DTOs.
  - [`../../adr/0021-functional-style-no-oop.md`](../../adr/0021-functional-style-no-oop.md) — frozen dataclasses, no OOP.

## Deliverables

```
src/budget_planner/domain/__init__.py                # re-exports
src/budget_planner/domain/enums.py                   # Direction, Cadence, OverrideState, AuditOperation
src/budget_planner/domain/money.py                   # minor-unit helpers + formatter
src/budget_planner/domain/system_categories.py       # (created in T-012; re-exported here)
src/budget_planner/domain/accounts.py                # Account, NewAccount, PatchAccount
src/budget_planner/domain/categories.py              # Category, NewCategory, PatchCategory
src/budget_planner/domain/transactions.py            # Transaction, NewTransaction, PatchTransaction, TransactionFilter
src/budget_planner/domain/planned.py                 # PlannedTransaction + New/Patch/Filter
src/budget_planner/domain/recurring.py               # RecurringRule + New/Patch, RecurringOverride + New
src/budget_planner/domain/budgets.py                 # BudgetDefault / Recurring / OneOff + their New DTOs
src/budget_planner/domain/snapshots.py               # AccountSnapshot, NewAccountSnapshot
src/budget_planner/domain/fx.py                      # FxRate, NewFxRate
src/budget_planner/domain/audit.py                   # AuditEntry

tests/unit/domain/test_enums.py
tests/unit/domain/test_money.py
tests/unit/domain/test_dataclasses_frozen.py
```

### Enum values (fixed)

```python
# domain/enums.py
from enum import StrEnum

class Direction(StrEnum):
    INCOME     = "income"
    EXPENSE    = "expense"
    TRANSIT    = "transit"
    ADJUSTMENT = "adjustment"

class Cadence(StrEnum):
    MONTHLY   = "monthly"
    QUARTERLY = "quarterly"
    YEARLY    = "yearly"

class OverrideState(StrEnum):
    SKIPPED    = "skipped"
    OVERRIDDEN = "overridden"

class AuditOperation(StrEnum):
    CREATE   = "create"
    UPDATE   = "update"
    DELETE   = "delete"
    UNDELETE = "undelete"
```

`StrEnum` so the SQL CHECK constraints and audit JSON strings line up without manual `.value` sprinkles.

### Dataclasses + DTOs (full list)

| Module | Entity | New (create) | Patch (update) | Filter |
|--------|--------|--------------|----------------|--------|
| accounts | `Account` | `NewAccount` | `PatchAccount` | — |
| categories | `Category` | `NewCategory` | `PatchCategory` | — |
| transactions | `Transaction` | `NewTransaction` | `PatchTransaction` | `TransactionFilter` |
| planned | `PlannedTransaction` | `NewPlannedTransaction` | `PatchPlannedTransaction` | `PlannedFilter` |
| recurring | `RecurringRule` + `RecurringOverride` | `NewRecurringRule` + `NewRecurringOverride` | `PatchRecurringRule` | — |
| budgets | `BudgetDefault`, `BudgetRecurringOverride`, `BudgetOneOffOverride` | `NewBudgetDefault`, `NewBudgetRecurringOverride`, `NewBudgetOneOffOverride` | — (overrides are set/clear, not patched) | — |
| snapshots | `AccountSnapshot` | `NewAccountSnapshot` | — | — |
| fx | `FxRate` | `NewFxRate` | — | — |
| audit | `AuditEntry` | — | — | — |

Also:
- `Occurrence` dataclass in `domain/recurring.py` — virtual (not persisted) occurrence shape returned by the Phase 2 generator.
- `AccountStats` dataclass in `domain/accounts.py` — stats shape returned by Phase 2 balance service.

## Step-by-step

1. **Shared frozen dataclass pattern.** Example — `domain/accounts.py`:

   ```python
   from __future__ import annotations

   from dataclasses import dataclass, field
   from datetime import datetime
   from typing import Any


   @dataclass(frozen=True, slots=True, kw_only=True)
   class Account:
       id: int
       user_id: int
       name: str
       type: str | None
       currency: str                # ISO 4217
       opening_balance: int         # minor units
       created_at: datetime
       updated_at: datetime
       deleted_at: datetime | None


   @dataclass(frozen=True, slots=True, kw_only=True)
   class NewAccount:
       name: str
       currency: str
       opening_balance: int = 0
       type: str | None = None
       user_id: int = 1


   @dataclass(frozen=True, slots=True, kw_only=True)
   class PatchAccount:
       name: str | None = None
       type: str | None = None
       opening_balance: int | None = None
       # NOTE: currency is immutable per ADR-0006; omitted from Patch.

       def as_dict(self) -> dict[str, Any]:
           return {k: v for k, v in self.__dict__.items() if v is not None}
   ```

   Every DTO follows the same three rules:
   - `frozen=True, slots=True, kw_only=True` → no accidental mutation, no positional confusion.
   - `New*` DTOs carry only insertable fields; computed fields (`id`, `created_at`, `updated_at`, `deleted_at`) are set by the DB.
   - `Patch*` DTOs are all-optional + `as_dict()` returning only non-`None` fields (used by `repositories/_shared.mutate`).

2. **`Transaction` DTO** (direction derived at service level by joining `categories`):

   ```python
   @dataclass(frozen=True, slots=True, kw_only=True)
   class Transaction:
       id: int
       user_id: int
       operation_date: date
       category_id: int
       account_id: int
       dest_account_id: int | None
       amount: int                              # minor units; signed only when direction=adjustment
       description: str
       promoted_from_planned_id: int | None
       created_at: datetime
       updated_at: datetime
       deleted_at: datetime | None


   @dataclass(frozen=True, slots=True, kw_only=True)
   class NewTransaction:
       operation_date: date
       category_id: int
       account_id: int
       amount: int
       description: str = ""
       dest_account_id: int | None = None
       promoted_from_planned_id: int | None = None
       user_id: int = 1


   @dataclass(frozen=True, slots=True, kw_only=True)
   class PatchTransaction:
       operation_date: date | None = None
       category_id: int | None = None
       account_id: int | None = None
       dest_account_id: int | None = None
       amount: int | None = None
       description: str | None = None

       def as_dict(self) -> dict[str, Any]:
           return {k: v for k, v in self.__dict__.items() if v is not None}
   ```

3. **Filter DTOs.** `TransactionFilter` holds query parameters consumed by `transactions.list_filtered`:

   ```python
   @dataclass(frozen=True, slots=True, kw_only=True)
   class TransactionFilter:
       date_from: date | None = None
       date_to: date | None = None
       up_to_date: date | None = None               # convenience for balance derivation
       account_ids: tuple[int, ...] = ()
       category_ids: tuple[int, ...] = ()
       directions: tuple[Direction, ...] = ()
       amount_min: int | None = None
       amount_max: int | None = None
       description_contains: str | None = None
       # Convenience: "account_id OR dest_account_id matches". Needed by balance service.
       account_or_dest: int | None = None
       limit: int | None = None
       offset: int = 0
   ```

   `tuple` instead of `list` so the DTO stays hashable + truly immutable.

4. **Recurring DTOs** (ADR-0013):

   ```python
   @dataclass(frozen=True, slots=True, kw_only=True)
   class RecurringRule:
       id: int
       user_id: int
       cadence: Cadence
       start_date: date
       end_date: date | None
       category_id: int
       account_id: int
       dest_account_id: int | None
       default_amount: int
       default_description: str
       day_of_month: int | None
       month_of_year: int | None
       active: bool
       created_at: datetime
       updated_at: datetime
       deleted_at: datetime | None


   @dataclass(frozen=True, slots=True, kw_only=True)
   class RecurringOverride:
       id: int
       rule_id: int
       occurrence_date: date
       state: OverrideState
       amount_override: int | None
       description_override: str | None
       date_override: date | None
       created_at: datetime


   @dataclass(frozen=True, slots=True, kw_only=True)
   class Occurrence:
       """Virtual (non-persisted) occurrence returned by the Phase 2 generator."""
       rule_id: int
       occurrence_date: date                      # canonical date; may differ from effective_date if overridden
       effective_date: date                       # date_override or occurrence_date
       category_id: int
       account_id: int
       dest_account_id: int | None
       amount: int
       description: str
       is_overridden: bool
       is_skipped: bool
   ```

5. **Budget DTOs** (ADR-0014):

   ```python
   @dataclass(frozen=True, slots=True, kw_only=True)
   class BudgetDefault:
       id: int
       user_id: int
       category_id: int
       amount: int                                 # minor units, non-negative
       created_at: datetime
       updated_at: datetime
       deleted_at: datetime | None


   @dataclass(frozen=True, slots=True, kw_only=True)
   class NewBudgetDefault:
       category_id: int
       amount: int
       user_id: int = 1


   @dataclass(frozen=True, slots=True, kw_only=True)
   class BudgetRecurringOverride:
       id: int
       user_id: int
       category_id: int
       month: int                                  # 1..12
       amount: int
       created_at: datetime
       updated_at: datetime
       deleted_at: datetime | None


   @dataclass(frozen=True, slots=True, kw_only=True)
   class NewBudgetRecurringOverride:
       category_id: int
       month: int
       amount: int
       user_id: int = 1


   @dataclass(frozen=True, slots=True, kw_only=True)
   class BudgetOneOffOverride:
       id: int
       user_id: int
       category_id: int
       year: int
       month: int
       amount: int
       created_at: datetime
       updated_at: datetime
       deleted_at: datetime | None


   @dataclass(frozen=True, slots=True, kw_only=True)
   class NewBudgetOneOffOverride:
       category_id: int
       year: int
       month: int
       amount: int
       user_id: int = 1
   ```

6. **Snapshots + FX + Audit:**

   ```python
   @dataclass(frozen=True, slots=True, kw_only=True)
   class AccountSnapshot:
       id: int
       account_id: int
       taken_at: datetime                          # UTC
       balance: int                                # minor units, signed
       note: str


   @dataclass(frozen=True, slots=True, kw_only=True)
   class NewAccountSnapshot:
       account_id: int
       balance: int
       note: str = ""


   @dataclass(frozen=True, slots=True, kw_only=True)
   class FxRate:
       id: int
       date: date
       from_ccy: str
       to_ccy: str
       rate: Decimal
       fetched_at: datetime


   @dataclass(frozen=True, slots=True, kw_only=True)
   class NewFxRate:
       date: date
       from_ccy: str
       to_ccy: str
       rate: Decimal


   @dataclass(frozen=True, slots=True, kw_only=True)
   class AuditEntry:
       id: int
       entity_type: str
       entity_id: int
       changed_at: datetime
       operation: AuditOperation
       prev_json: str | None                       # raw JSON TEXT; services parse on demand
       new_json: str | None
   ```

7. **Money helpers** (`domain/money.py`):

   ```python
   from __future__ import annotations

   from decimal import Decimal, ROUND_HALF_UP
   from typing import Final

   # ISO-4217 subset: minor-unit decimals we actually care about.
   # Default is 2; override here for JPY etc.
   _CURRENCY_DECIMALS: Final[dict[str, int]] = {
       "JPY": 0,
       "KRW": 0,
       "HUF": 2,
       "PLN": 2,
       "EUR": 2,
       "USD": 2,
       "GBP": 2,
       "CHF": 2,
   }


   def currency_decimals(currency: str) -> int:
       return _CURRENCY_DECIMALS.get(currency.upper(), 2)


   def to_minor_units(amount: Decimal, currency: str) -> int:
       """Convert a Decimal major-unit amount to signed integer minor units."""
       decimals = currency_decimals(currency)
       quant = Decimal(10) ** -decimals
       quantised = amount.quantize(quant, rounding=ROUND_HALF_UP)
       return int(quantised * (Decimal(10) ** decimals))


   def from_minor_units(amount_minor: int, currency: str) -> Decimal:
       decimals = currency_decimals(currency)
       return Decimal(amount_minor) / (Decimal(10) ** decimals)


   def format_money(amount_minor: int, currency: str) -> str:
       """Render as e.g. '1,234.56 PLN' / '1,234 JPY'."""
       decimals = currency_decimals(currency)
       value = from_minor_units(amount_minor, currency)
       sign = "-" if value < 0 else ""
       value = abs(value)
       whole, _, frac = f"{value:,.{decimals}f}".partition(".")
       return f"{sign}{whole}{('.' + frac) if frac else ''} {currency.upper()}"
   ```

8. **Tests:**
   - `test_enums.py`: `str(Direction.INCOME) == "income"`; set of `.value` matches the SQL CHECK literals.
   - `test_money.py`: PLN 12.34 → 1234; JPY 1234 → 1234; EUR −0.01 → −1; round-trip for 500 random Decimals; format_money renders negative amounts with a leading `-`.
   - `test_dataclasses_frozen.py`: `with pytest.raises(FrozenInstanceError): a.name = "x"` for a sampled DTO per module; `hash(TransactionFilter(...))` works (hashable).

## Interfaces / contracts

Public exports from `budget_planner.domain`:

```python
# Enums
Direction, Cadence, OverrideState, AuditOperation

# System categories
TRANSIT_CATEGORY_NAME, RECONCILIATION_CATEGORY_NAME, SYSTEM_CATEGORY_NAMES

# Money helpers
to_minor_units(amount: Decimal, currency: str) -> int
from_minor_units(amount_minor: int, currency: str) -> Decimal
currency_decimals(currency: str) -> int
format_money(amount_minor: int, currency: str) -> str

# Dataclasses (all frozen, slots, kw_only)
Account, NewAccount, PatchAccount
Category, NewCategory, PatchCategory
Transaction, NewTransaction, PatchTransaction, TransactionFilter
PlannedTransaction, NewPlannedTransaction, PatchPlannedTransaction, PlannedFilter
RecurringRule, NewRecurringRule, PatchRecurringRule
RecurringOverride, NewRecurringOverride
Occurrence
BudgetDefault, NewBudgetDefault
BudgetRecurringOverride, NewBudgetRecurringOverride
BudgetOneOffOverride, NewBudgetOneOffOverride
AccountSnapshot, NewAccountSnapshot
AccountStats
FxRate, NewFxRate
AuditEntry
```

## Validation / acceptance

- `just typecheck` passes under `mypy --strict` with no warnings on `src/budget_planner/domain/`.
- `just test tests/unit/domain/` green.
- Attempting to mutate any DTO raises `FrozenInstanceError` (verified by sample test).
- All `New*` and `Patch*` DTOs are importable from `budget_planner.domain`.
- Phase-1 exit criteria do not reference domain types directly, but T-013 cannot land without this task.

## Risks & gotchas

- **`slots=True` + default fields.** With `kw_only=True`, defaults do not need to be last; use `kw_only=True` everywhere to keep call sites unambiguous.
- **`Decimal` on frozen dataclass.** `FxRate.rate` holds a `Decimal`; repositories must parse `Decimal(row["rate"])` because SQLite stores it as TEXT (T-011).
- **`datetime` is tz-aware UTC.** Hydrate with `datetime.fromisoformat(s.replace("Z", "+00:00"))`. Tests must assert `.tzinfo is not None`.
- **`date` vs `datetime` collision.** `operation_date: date`, `created_at: datetime`. mypy strict catches most mix-ups; keep the imports explicit (`from datetime import date, datetime`).
- **`PatchX.as_dict()` returns only set fields.** Setting a field to `None` means "do not change". If the schema ever needs an explicit nullable patch (e.g. clear `type` on an account), add a sentinel; v1 does not need this.
- **StrEnum vs plain `str`.** `StrEnum` is Python 3.11+. Project pins Python 3.12 (CLAUDE.md). Safe.
- **Dataclass boilerplate.** Prefer dataclasses over Pydantic for interior types; Pydantic is used only at the HTTP boundary (Phase 3) if needed.

## Handoff notes

- T-013 imports the above dataclasses and DTOs; row-to-DTO hydration lives there, not here.
- Phase 2 services consume the enums and money helpers directly:
  - `services.balance` branches on `Direction`.
  - `services.recurring` branches on `Cadence`.
  - `services.fx.convert` round-trips through `to_minor_units` / `from_minor_units`.
  - `services.budget` uses `BudgetDefault/Recurring/OneOff` for the three-tier null-coalesce.
- Phase 3 Jinja filters wrap `format_money` and `direction_badge(Direction)`.
