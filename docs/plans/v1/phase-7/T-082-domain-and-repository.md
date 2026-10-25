# T-082 — Domain + Repository Changes for Liability Accounts

> Phase 7 — Liability Accounts. Status: pending.

## Purpose

Thread the two new columns through the Python layers so the rest of the stack can read + write them. Domain gets two new fields on `Account`, `NewAccount`, `PatchAccount`; repository CRUD hydrates them, persists them, and preserves the ADR-0019 / ADR-0022 soft-delete + audit discipline.

## Inputs / prerequisites

- Upstream tasks: T-081 (columns exist in the schema).
- Binding standards:
  - [`ADR-0021`](../../../adr/0021-functional-style-no-oop.md) — frozen dataclasses, `slots=True`, `kw_only=True`; no OOP beyond DTOs / Protocols.
  - [`ADR-0019`](../../../adr/0019-soft-delete-and-audit-log.md) — every mutation emits an `audit_log` row in the same transaction.
  - [`ADR-0022`](../../../adr/0022-repository-layer-soft-delete-audit-discipline.md) — mutations route through `repositories._shared.mutate`; readers default-filter `deleted_at IS NULL`.
- Adjacent precedent: `src/budget_planner/domain/accounts.py` and `src/budget_planner/repositories/accounts.py` carry the current `type` field — the new fields slot in next to it.

## Deliverables

Modified files:

- `src/budget_planner/domain/accounts.py`
- `src/budget_planner/repositories/accounts.py`

Domain changes:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Account:
    id: int
    user_id: int
    name: str
    type: str | None
    currency: str
    opening_balance: int
    is_liability: bool                 # new
    credit_limit_minor: int | None     # new
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NewAccount:
    name: str
    currency: str
    opening_balance: int = 0
    type: str | None = None
    is_liability: bool = False         # new
    credit_limit_minor: int | None = None  # new
    user_id: int = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class PatchAccount:
    name: str | None = None
    type: str | None = None
    opening_balance: int | None = None
    is_liability: bool | None = None   # new
    credit_limit_minor: int | None = None  # new; distinguish "no change" vs "clear" via sentinel
```

- `PatchAccount.credit_limit_minor` needs a distinction between "no change" and "clear to NULL". Options: (a) sentinel object `UNSET`; (b) separate boolean `clear_credit_limit`. Prefer (a) with a module-private sentinel re-used across patch DTOs if any other nullable patch field appears. For this task, implement (b) locally — one boolean — and defer the project-wide sentinel refactor.
- Keep `as_dict()` returning only non-`None` fields; add the two new fields to the fields iteration automatically via `dataclasses.fields()` (no manual listing).

Repository changes in `src/budget_planner/repositories/accounts.py`:

- Extend the `INSERT` statement in `create(...)` with both columns.
- Extend the row hydrator (whatever helper reads `row` → `Account`) to parse `is_liability` as `bool(row["is_liability"])` and `credit_limit_minor` as `row["credit_limit_minor"]` (SQLite returns `None` for `NULL`).
- `update(...)` must support the two new patch fields. Preserve the discipline: mutations route through `_shared.mutate` so `audit_log.prev_json` + `new_json` include the two new fields on every mutation.
- `soft_delete(...)` and `undelete(...)` are unchanged — they only touch `deleted_at` / `updated_at`.

New tests under `tests/unit/repositories/test_accounts.py`:

- `test_create_asset_account_defaults` — `NewAccount(name=…, currency=…)` persists with `is_liability = False` and `credit_limit_minor is None`.
- `test_create_liability_account_with_limit` — `NewAccount(..., is_liability=True, credit_limit_minor=1_000_000)` round-trips cleanly.
- `test_patch_set_credit_limit` — update an existing liability account's limit, assert the stored value changes and `audit_log.new_json` carries the new value.
- `test_patch_clear_credit_limit` — using the `clear_credit_limit=True` branch nulls the column; `audit_log.new_json` shows `null`.
- `test_patch_flip_asset_to_liability_without_limit_is_allowed_at_repo` — repository accepts the mutation; validation that enforces "liability requires positive limit" lives at the router layer (T-084).
- `test_hydrate_is_liability_zero_as_false` — fixture row with `is_liability = 0` hydrates to `False`; `1` → `True`.
- `test_list_all_includes_new_fields` — listing an asset + a liability account yields both with the correct field values.
- `test_audit_log_captures_both_new_fields_on_create_and_update` — assert JSON payload keys.

## Step-by-step

1. **Domain first.** Edit the three dataclasses, keeping field ordering intuitive (`is_liability` right after `type`, `credit_limit_minor` right after `is_liability`). Preserve `frozen=True, slots=True, kw_only=True`.
2. **Audit the hydrator.** The current reader likely builds the `Account` kwargs by name — add the two new keys and ensure the hydrator function signature does not need updating (names come from the row).
3. **Audit `_shared.mutate`.** The helper serialises the entity to JSON for the audit row; `dataclasses.asdict` already picks up the new fields, so `audit_log` payloads update for free. Add an assertion test rather than new serialisation code.
4. **Writer updates.** `create(...)` and `update(...)` both go through `mutate(...)`. Extend the parametrised SQL and the `kwargs` dict in exactly the two places that touch these columns.
5. **Patch sentinel for clearing the limit.** Add `clear_credit_limit: bool = False` to `PatchAccount`. When `True`, the repository writes `NULL` regardless of `credit_limit_minor`. This keeps `None` meaning "no change" and avoids inventing a project-wide sentinel in this task.
6. **Tests.** Add the new cases to `tests/unit/repositories/test_accounts.py`; keep them AAA-structured (Arrange / Act / Assert) per the global testing rule.

## Validation / acceptance

- `pytest tests/unit/repositories/test_accounts.py -q` — all tests pass (existing + new).
- `pytest tests/unit/domain -q` — frozen-ness tests still pass; add one that exercises the new default values.
- `pytest --cov=src/budget_planner/repositories/accounts --cov-fail-under=95` — ≥ 95% branch coverage retained.
- `just lint` + `just typecheck` green (new fields are strictly typed; `credit_limit_minor: int | None` is correctly annotated).
- `just ci` green.

## Risks & gotchas

- **Patch semantics.** `None` on a `PatchAccount` field means "no change" throughout the codebase (per `as_dict()` filter). A separate boolean (`clear_credit_limit`) is the least surprising way to express the clear operation. Do not introduce a module-level sentinel just for this task.
- **Audit log size.** `audit_log` grows by two keys per account mutation. That is intentional and matches ADR-0019 ("full previous and new entity serialised in the same transaction").
- **Boolean round-trip.** SQLite stores booleans as `0`/`1` integers (ADR-0014 for `categories.is_system` set the precedent). The hydrator must call `bool(row["is_liability"])`; do not rely on truthiness coercion through `Account(**row)`.
- **Hydrator reuse.** If `find_by_id`, `list_all`, and the audit serialiser all share one hydrator, the two new fields appear everywhere in one edit. Audit the file for parallel row-reading sites and fix the one spot — do not add parallel mappers.

## Handoff notes

- Hand-off to T-083: the fortune aggregator reads `account.is_liability` directly off hydrated `Account` instances; no new repository query needed. `account.credit_limit_minor` is irrelevant to T-083 (reporting is sign-driven, not limit-driven).
- Hand-off to T-084: form parses `is_liability` as HTML checkbox (`"on"` → `True`), parses `credit_limit` as a major-unit `Decimal` via `to_minor_units(dec, account.currency)`, and uses `PatchAccount(..., clear_credit_limit=True)` when the user unchecks the box.
- Commit shape: `feat(T-082): domain + repository fields for liability accounts (ADR-0024)`.
