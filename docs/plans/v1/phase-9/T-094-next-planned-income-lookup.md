# T-094 — Next-Planned-Income Lookup on `services/planned.py`

> Phase 9 — Left Daily Spend. Status: pending.

## Purpose

Add a thin pure function that answers "what is the earliest planned entry (persisted or virtual) in category X with `operation_date > today`?" so the budget service (T-095) can compute the "days until next income" denominator without re-implementing the planned-log UNION. Reuses `list_planned(...)` end-to-end — one source of truth for persisted + virtual + override dedup (ADR-0013).

## Inputs / prerequisites

- Upstream tasks: T-023 (planned log service).
- Binding standards: [`ADR-0013`](../../../adr/0013-recurring-virtual-occurrences-and-overrides.md), [`ADR-0021`](../../../adr/0021-functional-style-no-oop.md).
- Adjacent precedents:
  - `src/budget_planner/services/planned.py` — existing `list_planned` + `PlannedFilter` filter shape.
  - `src/budget_planner/services/forecast.py` — upstream consumer of the same UNION pattern; good reference for horizon handling.

## Deliverables

Extend `src/budget_planner/services/planned.py` with one new public function:

```python
def next_planned_for_category(
    conn: Connection,
    category_id: int,
    after: date,
    horizon_days: int = 400,
) -> PlannedView | None: ...
```

Semantics:

- Returns the earliest `PlannedView` whose `operation_date > after` and whose `category_id == category_id`, searching the window `(after, after + horizon_days]`.
- Internally calls `list_planned(conn, PlannedFilter(category_ids=(category_id,), date_from=after + timedelta(days=1), date_to=after + timedelta(days=horizon_days), promoted=False))`.
- Returns the first element of the sorted list (`list_planned` is already sorted by `(operation_date, kind, id)` per T-023), or `None` if empty.
- Does not re-sort; relies on the existing contract of `list_planned`.

New tests under `tests/unit/services/test_planned_next_for_category.py`:

- `test_returns_none_when_empty`
- `test_returns_persisted_hit`
- `test_returns_virtual_hit`
- `test_persisted_wins_over_virtual_on_same_date` (dedup regression)
- `test_skips_promoted_rows` (`promoted=False` filter)
- `test_excludes_soft_deleted_persisted`
- `test_ignores_rows_at_or_before_after` (boundary — `after + 0d` excluded, `after + 1d` included)
- `test_horizon_limits_search`
- `test_returns_none_for_unknown_category_id`

## Step-by-step

1. **Signature.** Add the function at the bottom of the public API, keyword-only for `horizon_days`.
2. **Date math.** Use `datetime.timedelta(days=1)` for the exclusive lower bound; use `horizon_days` for the inclusive upper bound. Validate `horizon_days >= 1` (raise `ValueError` otherwise — defensive, callers always pass sane defaults).
3. **Filter construction.** Build a `PlannedFilter` with `category_ids=(category_id,)` + the two date bounds + `promoted=False`.
4. **Return.** `return result[0] if result else None`.
5. **Public export.** Add the function name to `__all__` in `services/planned.py`.

## Validation / acceptance

- `pytest tests/unit/services/test_planned_next_for_category.py -q` — all tests pass.
- `pytest --cov=src/budget_planner/services/planned` is unchanged or improved vs. baseline (new branches covered by the new tests).
- `just lint` + `just typecheck` green.

## Risks & gotchas

- **`PlannedFilter` field names.** Confirm the current signature in `src/budget_planner/domain/planned.py` before writing — field name is `category_ids` (tuple) and date fields are `date_from` / `date_to`. If any have drifted, update the plan and the call site in lockstep.
- **Promoted exclusion.** The point of this lookup is to find a *future* income; promoted rows are already in `transactions` and the planned side is a stump. `promoted=False` is correct. Do not pass `None` or omit the filter — the test `test_skips_promoted_rows` guards this.
- **Soft-deleted persisted rows.** `list_planned` already filters `deleted_at IS NULL` via the repository default. The test is defence in depth.
- **Horizon length.** 400 days is enough for a yearly cadence plus a leap-year buffer. Do not raise it — longer horizons slow `list_planned` because the virtual expansion scales with range.

## Handoff notes

- Hand-off to T-095 (budget service): import `next_planned_for_category`; pass the resolved anchor category id + today's date.
- Commit shape: `feat(T-094): next_planned_for_category helper on planned service`.
