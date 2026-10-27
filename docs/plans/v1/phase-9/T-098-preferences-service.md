# T-098 — Preferences Service + Income Anchor Resolver

> Phase 9 — Left Daily Spend. Status: pending.

## Purpose

Expose the "income anchor" preference as three service functions with semantic validation (direction = `INCOME`, category live) at the boundary. Decouples T-100 (budget service consumer) and T-101 (web router) from the stringly-typed preference storage. Resolver returns the fully hydrated `Category` so downstream callers can display its name without a second repository fetch.

## Inputs / prerequisites

- Upstream tasks: T-097 (repository + domain), T-033 (categories router — only for the live-category discovery surface in T-101; service itself needs only `repositories.categories`).
- Binding standards: [`ADR-0025`](../../../adr/0025-user-preferences-and-income-anchor.md), [`ADR-0021`](../../../adr/0021-functional-style-no-oop.md).
- Adjacent precedents:
  - `src/budget_planner/services/budget.py` — simple pure-function service with typed inputs + narrow error types.
  - `src/budget_planner/services/reconciliation.py` — guard-error pattern for `NotFound` / `Validation` service errors.

## Deliverables

New file: `src/budget_planner/services/preferences.py`.

Public surface:

```python
def get_income_anchor_category_id(conn: Connection, user_id: int = 1) -> int | None: ...

def set_income_anchor_category_id(
    conn: Connection,
    user_id: int,
    category_id: int | None,
) -> None: ...

def resolve_income_anchor_category(
    conn: Connection,
    user_id: int = 1,
) -> Category | None: ...

class InvalidAnchorCategoryError(ValueError): ...
```

Error semantics:

- `set_income_anchor_category_id` with `category_id = None` → `delete`s the row; always succeeds.
- `set_income_anchor_category_id` with a non-existent or soft-deleted `category_id` → raises `InvalidAnchorCategoryError`.
- `set_income_anchor_category_id` with a category whose `direction != INCOME` → raises `InvalidAnchorCategoryError`.
- `resolve_income_anchor_category` is **permissive**: a stored row that no longer resolves (soft-deleted or direction changed under its feet) returns `None`. The stale row stays in the table — the user may rebind it later. The web layer never sees the exception.

New tests:

- `tests/unit/services/test_preferences.py`:
  - `test_get_returns_none_when_unset`
  - `test_get_returns_int_when_set`
  - `test_set_persists_round_trip`
  - `test_set_none_clears`
  - `test_set_rejects_unknown_category`
  - `test_set_rejects_soft_deleted_category`
  - `test_set_rejects_wrong_direction` (parametrised over `EXPENSE`, `TRANSIT`, `ADJUSTMENT`)
  - `test_resolve_returns_category_when_live`
  - `test_resolve_returns_none_when_soft_deleted` (set + soft-delete + resolve → `None`, row stays in `user_preferences`)
  - `test_resolve_returns_none_when_unset`

## Step-by-step

1. **Imports.** `from __future__ import annotations`; `sqlite3`; `from budget_planner.domain.categories import Category`; `from budget_planner.domain.enums import Direction`; `from budget_planner.domain.preferences import PREF_INCOME_ANCHOR_CATEGORY_ID`; `preferences_repo` + `categories_repo`.
2. **`get_income_anchor_category_id`.** Fetch the preference row; parse `value` as `int`; return `None` on absence. Treat a non-integer `value` as corruption → log WARNING and return `None` (defensive — should never happen because every setter validates before writing).
3. **`set_income_anchor_category_id`.** If `category_id is None` → `preferences_repo.delete(conn, user_id, PREF_INCOME_ANCHOR_CATEGORY_ID)` and return. Otherwise fetch the category by id (`categories_repo.find_by_id`); raise `InvalidAnchorCategoryError` on `None`, soft-deleted, or `direction != INCOME`. Then `preferences_repo.upsert(conn, user_id, PREF_INCOME_ANCHOR_CATEGORY_ID, str(category_id))`.
4. **`resolve_income_anchor_category`.** Delegate to `get_income_anchor_category_id`; return `None` if unset. Otherwise `categories_repo.find_by_id(conn, category_id)`; return `None` if the row is missing, soft-deleted, or `direction != INCOME`. Log DEBUG on stale references so operators can grep for lingering bad pointers.
5. **Function size.** Each function stays well under 50 lines. No classes beyond the error.
6. **Tests.** Build categories via existing test helpers; use `pytest.raises(InvalidAnchorCategoryError)` for the three rejection cases.

## Validation / acceptance

- `pytest tests/unit/services/test_preferences.py -q` — all tests pass.
- `pytest --cov=src/budget_planner/services/preferences --cov-fail-under=95` — ≥ 95% branch coverage (the module is small; aim for 100%).
- `grep -nE "write_audit|audit_log" src/budget_planner/services/preferences.py` returns no match.
- `just lint` + `just typecheck` green.

## Risks & gotchas

- **Direction immutability.** ADR-0008 marks `category.direction` as immutable once used. The direction-change-in-flight branch is defence in depth; test it by rewriting direction via a direct SQL update in the test fixture, not via a public API that does not exist.
- **Stale-row semantics.** `resolve_*` deliberately leaves the stale preference in place. A later `set_*` call will overwrite it. Do not add silent cleanup — observability matters: an operator reading `user_preferences` should see the stale pointer and can decide to clean it manually.
- **Return-type discipline.** `get_*` returns `int | None`, `resolve_*` returns `Category | None`. Do not conflate — the budget service needs the hydrated category for the caption string.

## Handoff notes

- Hand-off to T-100 (budget service): import `resolve_income_anchor_category` only. The int-returning `get_*` is a convenience for the web router.
- Hand-off to T-101 (web): import `set_income_anchor_category_id` for the POST endpoint and `get_income_anchor_category_id` to pre-select the current value in the dropdown.
- Commit shape: `feat(T-098): income anchor preference service (ADR-0025)`.
