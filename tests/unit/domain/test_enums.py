from __future__ import annotations

from budget_planner.domain.enums import (
    AuditOperation,
    Cadence,
    Direction,
    OverrideState,
)


def test_direction_values_match_check_constraint() -> None:
    assert {d.value for d in Direction} == {
        "income",
        "expense",
        "transit",
        "adjustment",
    }


def test_cadence_values_match_check_constraint() -> None:
    assert {c.value for c in Cadence} == {"monthly", "quarterly", "yearly"}


def test_override_state_values_match_check_constraint() -> None:
    assert {s.value for s in OverrideState} == {"skipped", "overridden"}


def test_audit_operation_values_match_check_constraint() -> None:
    assert {o.value for o in AuditOperation} == {
        "create",
        "update",
        "delete",
        "undelete",
    }


def test_direction_is_str() -> None:
    # StrEnum stringifies to the raw value, matching SQL CHECK literals.
    assert str(Direction.INCOME) == "income"
    assert f"{Direction.EXPENSE}" == "expense"
    # And direct comparison with the SQL literal works both ways.
    assert Direction.TRANSIT.value == "transit"
