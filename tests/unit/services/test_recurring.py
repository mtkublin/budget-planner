"""Tests for the recurring occurrence generator (T-022)."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

import pytest

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.recurring import RecurringOverride, RecurringRule
from budget_planner.services import recurring as rec_svc

_UTC = UTC


def _rule(
    *,
    rule_id: int = 1,
    cadence: Cadence = Cadence.MONTHLY,
    start_date: date = date(2026, 1, 15),
    end_date: date | None = None,
    day_of_month: int | None = None,
    month_of_year: int | None = None,
    active: bool = True,
    amount: int = 10_000,
    description: str = "rent",
) -> RecurringRule:
    return RecurringRule(
        id=rule_id,
        user_id=1,
        cadence=cadence,
        start_date=start_date,
        end_date=end_date,
        category_id=10,
        account_id=1,
        dest_account_id=None,
        default_amount=amount,
        default_description=description,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        active=active,
        next_due=start_date,
        last_promoted_date=None,
        created_at=datetime(2026, 1, 1, tzinfo=_UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=_UTC),
        deleted_at=None,
    )


def _override(
    *,
    override_id: int = 100,
    rule_id: int = 1,
    occurrence_date: date,
    state: OverrideState = OverrideState.SKIPPED,
    amount_override: int | None = None,
    description_override: str | None = None,
    date_override: date | None = None,
) -> RecurringOverride:
    return RecurringOverride(
        id=override_id,
        rule_id=rule_id,
        occurrence_date=occurrence_date,
        state=state,
        amount_override=amount_override,
        description_override=description_override,
        date_override=date_override,
        created_at=datetime(2026, 1, 1, tzinfo=_UTC),
    )


# ---------------------------------------------------------------------------
# cadence happy paths
# ---------------------------------------------------------------------------
def test_monthly_mid_month() -> None:
    rule = _rule(start_date=date(2026, 3, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 3, 1), date(2026, 6, 30))
    assert [o.occurrence_date for o in occs] == [
        date(2026, 3, 15),
        date(2026, 4, 15),
        date(2026, 5, 15),
        date(2026, 6, 15),
    ]


def test_monthly_end_of_month_clamp() -> None:
    rule = _rule(start_date=date(2026, 1, 31))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 4, 30))
    assert [o.occurrence_date for o in occs] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]


def test_monthly_leap_year() -> None:
    rule = _rule(start_date=date(2024, 1, 31))
    occs = rec_svc.generate_occurrences(rule, date(2024, 1, 1), date(2024, 4, 30))
    assert [o.occurrence_date for o in occs] == [
        date(2024, 1, 31),
        date(2024, 2, 29),
        date(2024, 3, 31),
        date(2024, 4, 30),
    ]


def test_quarterly() -> None:
    rule = _rule(cadence=Cadence.QUARTERLY, start_date=date(2026, 2, 10))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2027, 1, 31))
    assert [o.occurrence_date for o in occs] == [
        date(2026, 2, 10),
        date(2026, 5, 10),
        date(2026, 8, 10),
        date(2026, 11, 10),
    ]


def test_quarterly_year_boundary() -> None:
    rule = _rule(cadence=Cadence.QUARTERLY, start_date=date(2026, 11, 20))
    occs = rec_svc.generate_occurrences(rule, date(2026, 10, 1), date(2027, 3, 31))
    assert [o.occurrence_date for o in occs] == [
        date(2026, 11, 20),
        date(2027, 2, 20),
    ]


def test_yearly() -> None:
    rule = _rule(cadence=Cadence.YEARLY, start_date=date(2024, 7, 4))
    occs = rec_svc.generate_occurrences(rule, date(2024, 1, 1), date(2027, 12, 31))
    assert [o.occurrence_date for o in occs] == [
        date(2024, 7, 4),
        date(2025, 7, 4),
        date(2026, 7, 4),
        date(2027, 7, 4),
    ]


def test_yearly_feb_29() -> None:
    rule = _rule(cadence=Cadence.YEARLY, start_date=date(2024, 2, 29))
    occs = rec_svc.generate_occurrences(rule, date(2024, 1, 1), date(2028, 12, 31))
    assert [o.occurrence_date for o in occs] == [
        date(2024, 2, 29),
        date(2025, 2, 28),
        date(2026, 2, 28),
        date(2027, 2, 28),
        date(2028, 2, 29),
    ]


def test_yearly_month_of_year_before_start_month_rolls_year() -> None:
    """Yearly rule starting mid-year with month_of_year in an earlier month
    should produce the next-year occurrence first (ADR-0013 handoff note)."""
    rule = _rule(
        cadence=Cadence.YEARLY,
        start_date=date(2026, 6, 1),
        month_of_year=3,  # March — earlier than June
        day_of_month=15,
    )
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2029, 12, 31))
    assert [o.occurrence_date for o in occs] == [
        date(2027, 3, 15),
        date(2028, 3, 15),
        date(2029, 3, 15),
    ]


def test_yearly_with_month_of_year_override() -> None:
    rule = _rule(
        cadence=Cadence.YEARLY,
        start_date=date(2024, 1, 1),
        month_of_year=12,
        day_of_month=24,
    )
    occs = rec_svc.generate_occurrences(rule, date(2024, 1, 1), date(2027, 12, 31))
    assert [o.occurrence_date for o in occs] == [
        date(2024, 12, 24),
        date(2025, 12, 24),
        date(2026, 12, 24),
        date(2027, 12, 24),
    ]


# ---------------------------------------------------------------------------
# range / lifecycle
# ---------------------------------------------------------------------------
def test_range_start_before_rule_start() -> None:
    rule = _rule(start_date=date(2026, 3, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 4, 30))
    assert [o.occurrence_date for o in occs] == [date(2026, 3, 15), date(2026, 4, 15)]


def test_range_end_after_rule_end() -> None:
    rule = _rule(start_date=date(2026, 1, 15), end_date=date(2026, 3, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 6, 30))
    assert [o.occurrence_date for o in occs] == [
        date(2026, 1, 15),
        date(2026, 2, 15),
        date(2026, 3, 15),
    ]


def test_empty_intersection() -> None:
    rule = _rule(start_date=date(2026, 7, 1))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 3, 1))
    assert occs == ()


def test_inactive_rule_returns_empty() -> None:
    rule = _rule(active=False)
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 12, 31))
    assert occs == ()


# ---------------------------------------------------------------------------
# apply_overrides state machine
# ---------------------------------------------------------------------------
def test_skip_single() -> None:
    rule = _rule(start_date=date(2026, 1, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 4, 30))
    overrides = [_override(occurrence_date=date(2026, 2, 15))]
    out = rec_svc.apply_overrides(occs, overrides)
    assert [o.occurrence_date for o in out] == [
        date(2026, 1, 15),
        date(2026, 3, 15),
        date(2026, 4, 15),
    ]
    assert all(not o.is_skipped for o in out)


def test_override_amount_only() -> None:
    rule = _rule(start_date=date(2026, 1, 15), amount=10_000)
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 3, 31))
    overrides = [
        _override(
            occurrence_date=date(2026, 2, 15),
            state=OverrideState.OVERRIDDEN,
            amount_override=20_000,
        )
    ]
    out = rec_svc.apply_overrides(occs, overrides)
    feb = next(o for o in out if o.occurrence_date == date(2026, 2, 15))
    assert feb.amount == 20_000
    assert feb.is_overridden
    jan = next(o for o in out if o.occurrence_date == date(2026, 1, 15))
    assert jan.amount == 10_000
    assert not jan.is_overridden


def test_override_description_only() -> None:
    rule = _rule(start_date=date(2026, 1, 15), description="rent")
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 2, 28))
    overrides = [
        _override(
            occurrence_date=date(2026, 2, 15),
            state=OverrideState.OVERRIDDEN,
            description_override="rent +utilities",
        )
    ]
    out = rec_svc.apply_overrides(occs, overrides)
    feb = next(o for o in out if o.occurrence_date == date(2026, 2, 15))
    assert feb.description == "rent +utilities"
    assert feb.amount == 10_000  # unchanged


def test_override_date_shifts_effective_date() -> None:
    rule = _rule(start_date=date(2026, 1, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 4, 30))
    overrides = [
        _override(
            occurrence_date=date(2026, 2, 15),  # canonical key
            state=OverrideState.OVERRIDDEN,
            date_override=date(2026, 2, 25),
        )
    ]
    out = rec_svc.apply_overrides(occs, overrides)
    # Overridden occurrence keeps canonical occurrence_date but effective_date shifts.
    feb = next(o for o in out if o.occurrence_date == date(2026, 2, 15))
    assert feb.effective_date == date(2026, 2, 25)
    assert feb.is_overridden


def test_orphan_override_dropped(caplog: pytest.LogCaptureFixture) -> None:
    rule = _rule(start_date=date(2026, 1, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 2, 28))
    overrides = [
        _override(occurrence_date=date(2026, 5, 15))  # not in canonical schedule
    ]
    with caplog.at_level(logging.DEBUG, logger="budget_planner.services.recurring"):
        out = rec_svc.apply_overrides(occs, overrides)
    assert len(out) == len(occs)  # orphan silently dropped
    assert any("orphan" in r.message.lower() for r in caplog.records)


def test_no_overrides_passthrough() -> None:
    rule = _rule(start_date=date(2026, 1, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 3, 31))
    out = rec_svc.apply_overrides(occs, [])
    assert out == occs


def test_expand_composes() -> None:
    rule = _rule(start_date=date(2026, 1, 15))
    overrides = [_override(occurrence_date=date(2026, 2, 15))]
    out = rec_svc.expand(rule, overrides, date(2026, 1, 1), date(2026, 3, 31))
    assert [o.occurrence_date for o in out] == [date(2026, 1, 15), date(2026, 3, 15)]


def test_expand_empty_overrides_matches_generate() -> None:
    rule = _rule(start_date=date(2026, 1, 15))
    expand_out = rec_svc.expand(rule, [], date(2026, 1, 1), date(2026, 4, 30))
    gen_out = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 4, 30))
    assert expand_out == gen_out


def test_date_override_sort_order() -> None:
    # May override shifts to July — should sort after June canonical.
    rule = _rule(start_date=date(2026, 1, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 7, 31))
    overrides = [
        _override(
            occurrence_date=date(2026, 5, 15),
            state=OverrideState.OVERRIDDEN,
            date_override=date(2026, 7, 20),
        )
    ]
    out = rec_svc.apply_overrides(occs, overrides)
    effective_dates = [o.effective_date for o in out]
    assert effective_dates == sorted(effective_dates)
    assert date(2026, 7, 20) in effective_dates


def test_duplicate_override_warns_last_wins(caplog: pytest.LogCaptureFixture) -> None:
    rule = _rule(start_date=date(2026, 1, 15))
    occs = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 3, 31))
    overrides = [
        _override(
            override_id=1,
            occurrence_date=date(2026, 2, 15),
            state=OverrideState.OVERRIDDEN,
            amount_override=20_000,
        ),
        _override(
            override_id=2,
            occurrence_date=date(2026, 2, 15),
            state=OverrideState.OVERRIDDEN,
            amount_override=30_000,
        ),
    ]
    with caplog.at_level(logging.WARNING, logger="budget_planner.services.recurring"):
        out = rec_svc.apply_overrides(occs, overrides)
    feb = next(o for o in out if o.occurrence_date == date(2026, 2, 15))
    assert feb.amount == 30_000
    assert any("collide" in r.message.lower() for r in caplog.records)


def test_partition_invariant() -> None:
    """Occurrences in [a, b] + (b, c] equal [a, c] with same rule."""
    rule = _rule(start_date=date(2026, 1, 15))
    a_to_b = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 3, 31))
    b1_to_c = rec_svc.generate_occurrences(rule, date(2026, 4, 1), date(2026, 7, 31))
    full = rec_svc.generate_occurrences(rule, date(2026, 1, 1), date(2026, 7, 31))
    assert a_to_b + b1_to_c == full
