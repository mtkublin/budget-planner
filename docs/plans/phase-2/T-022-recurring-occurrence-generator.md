# T-022 — Recurring Occurrence Generator

> Phase 2 — Services. Status: pending.

## Purpose

Expand a `RecurringRule` into a deterministic, pure sequence of virtual `Occurrence`s inside a `[range_start, range_end]` window, then apply the sparse `recurring_rule_overrides` state machine (`skipped` | `overridden`) to produce the final list. Occurrences are never materialised into any table (ADR-0013). This generator is the single source of truth for every forward-looking view (planned log, forecast).

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-013 Repositories](../phase-1/T-013-repository-layer.md) — `repositories/recurring.py` (reader of rules + overrides).
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `RecurringRule`, `RecurringRuleOverride`, `Cadence`, `OverrideState`.
- ADRs:
  - [ADR-0013 Recurring virtual occurrences & overrides](../../adr/0013-recurring-virtual-occurrences-and-overrides.md).
  - [ADR-0007 Timezone handling](../../adr/0007-timezone-handling.md) — all dates are naive `date`.
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
- Repository functions consumed by downstream callers (T-023, T-025):
  - `repositories.recurring.list_active_rules(conn, in_range: tuple[date, date]) -> list[RecurringRule]`
  - `repositories.recurring.list_overrides_for_rule(conn, rule_id: int) -> list[RecurringRuleOverride]`
  - This service itself touches **no DB**; callers resolve rules + overrides and hand them in.

## Deliverables

- Module path: `src/budget_planner/services/recurring.py`
- Test module path: `tests/unit/services/test_recurring.py`
- Public function signatures:

```python
from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.recurring import RecurringRule, RecurringRuleOverride


@dataclass(frozen=True, slots=True)
class Occurrence:
    rule_id: int
    occurrence_date: dt.date
    account_id: int
    dest_account_id: int | None
    category_id: int
    amount_minor: int
    description: str
    is_overridden: bool  # True iff an `overridden` row applied


def generate_occurrences(
    rule: RecurringRule,
    range_start: dt.date,
    range_end: dt.date,
) -> tuple[Occurrence, ...]: ...


def apply_overrides(
    occurrences: Sequence[Occurrence],
    overrides: Iterable[RecurringRuleOverride],
) -> tuple[Occurrence, ...]: ...


def expand(
    rule: RecurringRule,
    overrides: Iterable[RecurringRuleOverride],
    range_start: dt.date,
    range_end: dt.date,
) -> tuple[Occurrence, ...]:
    """Convenience: generate_occurrences(...) then apply_overrides(...)."""
```

## Algorithm / step-by-step

### Canonical schedule by cadence

Inputs on `RecurringRule`:
- `cadence`: `monthly` | `quarterly` | `yearly`.
- `start_date: date` — first canonical occurrence.
- `end_date: date | None` — inclusive upper bound of the rule's lifespan.
- `day_of_month: int | None` — day-of-month anchor; defaults to `start_date.day` when absent.
- `month_of_year: int | None` — only used by `yearly`; defaults to `start_date.month`.
- `active: bool` — treated as a hard filter at the caller level (`list_active_rules`), but double-checked here for safety.

Produce occurrence dates by cadence:

| Cadence | Step | Anchor day | Edge rule |
|---------|------|-----------|-----------|
| `monthly` | +1 month | `day_of_month ?? start.day` | If target month has no such day, clamp to that month's last day (Jan 31 monthly → Feb 28, Feb 29 on leap year, Apr 30, …). |
| `quarterly` | +3 months | same as monthly | Same clamp. |
| `yearly` | +1 year | `(month_of_year, day_of_month)` or `(start.month, start.day)` | Feb 29 yearly → Feb 28 on non-leap years. Clamp otherwise unchanged. |

Clamp helper (pseudo):

```python
def clamp_to_eom(year: int, month: int, day: int) -> dt.date:
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day, last))
```

Preferred implementation: use `dateutil.relativedelta.relativedelta(months=step, day=anchor_day)` — `relativedelta`'s `day=` kwarg performs the end-of-month clamp automatically. If `python-dateutil` is already a project dep (it is — see `pyproject.toml` in T-001), use it. Otherwise write the clamp by hand; keep it in one place.

### Boundary semantics

- `range_start` and `range_end` are both **inclusive**.
- An occurrence is kept iff `max(rule.start_date, range_start) <= occurrence_date <= min(rule.end_date or ∞, range_end)`.
- `rule.start_date` is itself a candidate occurrence (occurrence #0).
- If `rule.active is False`, `generate_occurrences` returns `()` regardless of the window.

### Iteration structure (pure, no mutation)

```python
def generate_occurrences(rule, range_start, range_end):
    if not rule.active:
        return ()
    anchor_day = rule.day_of_month or rule.start_date.day
    step_months = {Cadence.monthly: 1, Cadence.quarterly: 3, Cadence.yearly: 12}[rule.cadence]

    hard_end = min(range_end, rule.end_date) if rule.end_date else range_end
    if hard_end < max(range_start, rule.start_date):
        return ()

    out: list[Occurrence] = []
    idx = 0
    while True:
        occ_date = _step(rule.start_date, step_months * idx, anchor_day, rule)
        if occ_date > hard_end:
            break
        if occ_date >= range_start:
            out.append(_mk_occurrence(rule, occ_date))
        idx += 1
    return tuple(out)
```

`_step` is pure; use `relativedelta` or the clamp helper. `_mk_occurrence` fills in rule defaults with `is_overridden=False`.

### `apply_overrides` — state machine

Overrides are a sparse list keyed by `(rule_id, occurrence_date)`. Rules:

| `state` | Action |
|---------|--------|
| `skipped` | Drop the matching occurrence from the output. |
| `overridden` | Replace fields: `amount_override` → `amount_minor`; `description_override` → `description`; `date_override` → `occurrence_date`. Nullable override fields leave the original value in place. Set `is_overridden = True`. |

Rules:

1. Match by `(rule_id, occurrence_date)` of the **unmodified** occurrence, i.e. before `date_override` is applied. This matters when a user overrides to shift a date — the override still keys off the original schedule date.
2. If an override references an `occurrence_date` that is not in the canonical schedule (e.g. an orphan from a previous rule edit), it is silently dropped. Log at `DEBUG` level.
3. If two overrides collide on the same `(rule_id, occurrence_date)`: that is a repository invariant violation (there is a UNIQUE constraint planned on the overrides table — confirm during T-011 execution). The service treats "last wins by sort order on `id`" defensively, logs `WARNING`.
4. Return a `tuple` sorted by final `occurrence_date` ascending; stable sort to keep tests deterministic.

### `expand`

Trivial composition. Exists so callers (T-023, T-025) don't repeat the two-call dance.

## Interfaces / contracts

```python
def generate_occurrences(
    rule: RecurringRule,
    range_start: dt.date,
    range_end: dt.date,
) -> tuple[Occurrence, ...]:
    """
    Pure. Returns the canonical schedule intersected with
    [range_start, range_end], bounded by rule.start_date and rule.end_date.

    Edge rules:
      - monthly / quarterly with day_of_month > days_in_month → clamp to EOM.
      - yearly on Feb 29 → Feb 28 on non-leap years.
      - active=False → ().
    """


def apply_overrides(
    occurrences: Sequence[Occurrence],
    overrides: Iterable[RecurringRuleOverride],
) -> tuple[Occurrence, ...]:
    """
    Pure. Applies the (skipped | overridden) state machine.
    Keyed by the ORIGINAL occurrence_date, not the overridden date.
    """
```

Invariant: `expand(rule, [], a, b) == generate_occurrences(rule, a, b)`.

## Test strategy

Parametrised, table-driven. No DB required for this service's unit tests — pass `RecurringRule` dataclasses directly.

Cadence happy paths:

1. **Monthly, mid-month**: start `2026-03-15`, range `2026-03-01..2026-06-30` → `[03-15, 04-15, 05-15, 06-15]`.
2. **Monthly end-of-month clamp**: start `2026-01-31`, range `2026-01-01..2026-04-30` → `[01-31, 02-28, 03-31, 04-30]`.
3. **Monthly on leap-year Feb**: start `2024-01-31`, range `2024-01-01..2024-04-30` → `[01-31, 02-29, 03-31, 04-30]`.
4. **Quarterly**: start `2026-02-10`, range `2026-01-01..2027-01-31` → `[02-10, 05-10, 08-10, 11-10, 02-10 (2027)]`.
5. **Quarterly year-boundary**: start `2026-11-20`, range `2026-10-01..2027-03-31` → `[11-20 (2026), 02-20 (2027)]`.
6. **Yearly**: start `2024-07-04`, range `2024-01-01..2027-12-31` → `[2024-07-04, 2025-07-04, 2026-07-04, 2027-07-04]`.
7. **Yearly Feb 29 anchor**: start `2024-02-29`, range `2024-01-01..2028-12-31` → `[2024-02-29, 2025-02-28, 2026-02-28, 2027-02-28, 2028-02-29]`.
8. **Yearly with `month_of_year` override**: `cadence=yearly, start_date=2024-01-01, month_of_year=12, day_of_month=24` → every Dec 24.

Range / lifecycle:

9. **`range_start` before `rule.start_date`**: generator starts at `rule.start_date`, not earlier.
10. **`range_end` after `rule.end_date`**: generator stops at `rule.end_date`.
11. **Empty intersection**: `rule.start_date > range_end` → `()`.
12. **`active=False`**: `()`.

Overrides state machine:

13. **Skip single**: one `skipped` on an occurrence inside the window removes exactly that date.
14. **Skip multi**: two `skipped` rows (July + September) each remove their occurrence; August is unaffected.
15. **Override amount only**: override row with only `amount_override` set → the matched occurrence's `amount_minor` changes, `description` and `occurrence_date` unchanged, `is_overridden=True`.
16. **Override description only**: analogous.
17. **Override date**: `date_override` set → `occurrence_date` on the output is the overridden date; sort order reflects the new date; the override is still **keyed** by the canonical date.
18. **Overridden-then-skipped combination**: not expressible with the schema (one state per row). Verify the service treats a single row as one atomic action, no state blending.
19. **Orphan override**: override references a date not in the canonical schedule → silently dropped; a `DEBUG` log line emitted.
20. **No-op (empty overrides list)**: output equals `generate_occurrences` output exactly.
21. **Sort stability**: date-override that shifts a May occurrence into July places it after the canonical June occurrence.

Property check (optional but recommended):

22. `len(generate_occurrences(rule, a, b)) == len(generate_occurrences(rule, a, b))` idempotency.
23. For disjoint `[a, b]` and `[c, d]` with `b < c`, concatenation equals `generate_occurrences(rule, a, d)`. (Partitioning invariant.)

Fixtures:

- `make_rule(**overrides)` factory with sensible defaults.
- `make_override(**fields)` factory.

Mocking boundaries: none. Service is a pure function over data classes.

## Risks & gotchas

- **Month-end clamp is the main hazard.** Hand-rolling `date(year, month, day)` throws `ValueError` on Feb 31. Use `relativedelta(day=anchor)` (dateutil) or a dedicated helper; never try/except around the constructor.
- **Leap years for yearly Feb 29 rules.** The Feb 29 → Feb 28 fallback must still produce Feb 29 again on the next leap year — do not stickily collapse to Feb 28 forever.
- **Override keying.** Keying overrides by canonical date (not overridden date) is the correct behaviour but counter-intuitive. Document in the docstring and cover with test 17.
- **Yearly with `month_of_year`.** The `month_of_year` field lets a rule start in one month but recur in another. Edge case: starting mid-year (`start_date=2026-06-01, month_of_year=11, day_of_month=15`) — the first occurrence inside the window is `2026-11-15`, not `2026-06-01`.
- **Infinite loop guard.** The `while True` must break when `occ_date > hard_end`. If someone accidentally returns the same date twice from `_step`, the loop never terminates. Add a defensive `idx > 10_000` assertion for the yearly 5-year horizon (safe ceiling).
- **Timezone / `datetime.date` vs `datetime.datetime`.** Everything is `date`. A caller passing a `datetime` will shadow-match in Python 3 (because `datetime` subclasses `date`) and the comparisons silently work but the override match may fail. Enforce with `isinstance` assertions in debug / development.
- **Rule edits propagate instantly** (ADR-0013). The service re-runs on every query; there is no cache to invalidate. Confirm this against performance notes in T-025.

## Handoff notes

Phase 3 consumers:

- **Planned log service (T-023)** calls `expand(rule, overrides, range_start, range_end)` once per active rule and UNIONs the result with persisted planned rows.
- **Forecast service (T-025)** calls `expand(...)` for each active rule across `[today+1, today+horizon_days]`, bucketing legs per day.
- **Recurring rules router (T-035)** uses `generate_occurrences` for the "upcoming occurrences preview" table, then calls `apply_overrides` so skipped/overridden state is visible to the user.

Routers never persist occurrences. The database never holds a materialised recurring row (except for an override — a sparse exception, not a materialisation).
