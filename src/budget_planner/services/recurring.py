"""Recurring occurrence generator (T-022).

Expand a ``RecurringRule`` into a deterministic, pure sequence of virtual
``Occurrence`` instances, then apply sparse overrides (ADR-0013).

The service touches no DB; callers resolve the rule and its overrides and
pass them in. Downstream consumers (T-023 planned log, T-025 forecast,
T-035 recurring router) call :func:`expand` as a one-liner.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Iterable, Sequence

from dateutil.relativedelta import relativedelta

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.recurring import Occurrence, RecurringOverride, RecurringRule

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 10_000

_STEP_MONTHS: dict[Cadence, int] = {
    Cadence.MONTHLY: 1,
    Cadence.QUARTERLY: 3,
    Cadence.YEARLY: 12,
}


def _step_date(start: dt.date, idx: int, step_months: int, anchor_day: int) -> dt.date:
    """Return ``start + idx * step_months`` anchored on ``anchor_day``.

    ``relativedelta(day=anchor)`` performs the end-of-month clamp automatically.
    For yearly rules with Feb-29 anchor, Feb 28 is produced in non-leap years;
    the cycle recovers to Feb 29 the next time it is possible.
    """
    return start + relativedelta(months=step_months * idx, day=anchor_day)


def _mk_occurrence(rule: RecurringRule, occ_date: dt.date) -> Occurrence:
    return Occurrence(
        rule_id=rule.id,
        occurrence_date=occ_date,
        effective_date=occ_date,
        category_id=rule.category_id,
        account_id=rule.account_id,
        dest_account_id=rule.dest_account_id,
        amount=rule.default_amount,
        description=rule.default_description,
        is_overridden=False,
        is_skipped=False,
    )


def generate_occurrences(
    rule: RecurringRule,
    range_start: dt.date,
    range_end: dt.date,
) -> tuple[Occurrence, ...]:
    """Return the canonical schedule intersected with ``[range_start, range_end]``.

    Both bounds inclusive. The rule's own ``start_date`` is a candidate
    occurrence. ``active=False`` short-circuits to ``()``. Monthly /
    quarterly / yearly cadences clamp to the end of the month when the
    anchor day exceeds the target month's day count.
    """
    if not rule.active:
        return ()

    hard_end = min(range_end, rule.end_date) if rule.end_date else range_end
    hard_start = max(range_start, rule.start_date)
    if hard_end < hard_start:
        return ()

    step_months = _STEP_MONTHS[rule.cadence]
    # Yearly rules honour an optional month_of_year by anchoring the first
    # occurrence to (month_of_year, day_of_month) on-or-after start_date.
    anchor_day = rule.day_of_month or rule.start_date.day
    base_date = rule.start_date
    if rule.cadence is Cadence.YEARLY and rule.month_of_year is not None:
        candidate = base_date + relativedelta(month=rule.month_of_year, day=anchor_day)
        if candidate < rule.start_date:
            candidate = candidate + relativedelta(years=1)
        base_date = candidate

    out: list[Occurrence] = []
    for idx in range(_MAX_ITERATIONS):
        occ_date = _step_date(base_date, idx, step_months, anchor_day)
        if occ_date > hard_end:
            break
        if occ_date >= range_start:
            out.append(_mk_occurrence(rule, occ_date))
    else:  # pragma: no cover - safety guard
        raise RuntimeError("occurrence generator did not terminate")
    return tuple(out)


def _apply_single_override(occ: Occurrence, override: RecurringOverride) -> Occurrence | None:
    """Return the overridden occurrence, or ``None`` if ``state=skipped``."""
    if override.state is OverrideState.SKIPPED:
        return None
    new_amount = override.amount_override if override.amount_override is not None else occ.amount
    new_description = (
        override.description_override
        if override.description_override is not None
        else occ.description
    )
    new_effective = (
        override.date_override if override.date_override is not None else occ.occurrence_date
    )
    return Occurrence(
        rule_id=occ.rule_id,
        occurrence_date=occ.occurrence_date,  # canonical key preserved
        effective_date=new_effective,
        category_id=occ.category_id,
        account_id=occ.account_id,
        dest_account_id=occ.dest_account_id,
        amount=new_amount,
        description=new_description,
        is_overridden=True,
        is_skipped=False,
    )


def apply_overrides(
    occurrences: Sequence[Occurrence],
    overrides: Iterable[RecurringOverride],
) -> tuple[Occurrence, ...]:
    """Apply the ``(skipped | overridden)`` state machine.

    Keyed by the ORIGINAL ``occurrence_date``, not the overridden one. Orphan
    overrides (no matching canonical occurrence) are dropped with a DEBUG log.
    Duplicates on the same key log a WARNING; last-wins by sort order on ``id``.
    """
    # Group overrides by occurrence_date, warn on duplicates.
    by_date: dict[dt.date, RecurringOverride] = {}
    seen: set[dt.date] = set()
    canonical_dates = {o.occurrence_date for o in occurrences}
    for override in sorted(overrides, key=lambda o: o.id):
        if override.occurrence_date in seen:
            logger.warning(
                "overrides collide on (rule_id=%s, occurrence_date=%s); last-wins",
                override.rule_id,
                override.occurrence_date,
            )
        seen.add(override.occurrence_date)
        if override.occurrence_date not in canonical_dates:
            logger.debug(
                "orphan override dropped: rule_id=%s date=%s",
                override.rule_id,
                override.occurrence_date,
            )
            continue
        by_date[override.occurrence_date] = override

    out: list[Occurrence] = []
    for occ in occurrences:
        match = by_date.get(occ.occurrence_date)
        if match is None:
            out.append(occ)
            continue
        updated = _apply_single_override(occ, match)
        if updated is not None:
            out.append(updated)
    # Sort by effective_date (overrides may shift dates), stable on occurrence_date.
    out.sort(key=lambda o: (o.effective_date, o.occurrence_date))
    return tuple(out)


def expand(
    rule: RecurringRule,
    overrides: Iterable[RecurringOverride],
    range_start: dt.date,
    range_end: dt.date,
) -> tuple[Occurrence, ...]:
    """``generate_occurrences(...)`` then ``apply_overrides(...)``."""
    return apply_overrides(generate_occurrences(rule, range_start, range_end), overrides)


__all__ = ["apply_overrides", "expand", "generate_occurrences"]
