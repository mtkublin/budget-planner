"""Recurring rules + overrides + virtual occurrence shape (ADR-0013 / ADR-0038)."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from typing import Any, Final

from budget_planner.domain.enums import Cadence, OverrideState

# Sentinel for `PatchRecurringRule.next_due` so we can distinguish "no change"
# from "explicitly clear" (clearing is not allowed — `next_due` is NOT NULL —
# but the sentinel keeps the shape symmetric with other patch DTOs and lets
# admin flows pass through an unmodified value without re-asserting it).
_UNCHANGED: Final[object] = object()


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurringRule:
    """Persisted recurring rule.

    `next_due` is the authoritative "when is the next occurrence" column
    (ADR-0038). Every mutation that could shift it must keep it in sync.
    `last_promoted_date` is informational (nullable; untouched by overrides).
    """

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
    next_due: date
    last_promoted_date: date | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NewRecurringRule:
    """Insertable fields for a new recurring rule.

    `next_due` is intentionally absent: the repository computes it on
    insert from the generator (ADR-0038).
    """

    cadence: Cadence
    start_date: date
    category_id: int
    account_id: int
    default_amount: int
    end_date: date | None = None
    dest_account_id: int | None = None
    default_description: str = ""
    day_of_month: int | None = None
    month_of_year: int | None = None
    active: bool = True
    user_id: int = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class PatchRecurringRule:
    """Partial update DTO.

    `next_due` accepts an explicit admin override via the `_UNCHANGED`
    sentinel pattern — passing a `date` writes it, leaving the default
    does not touch the column.
    """

    cadence: Cadence | None = None
    start_date: date | None = None
    end_date: date | None = None
    category_id: int | None = None
    account_id: int | None = None
    dest_account_id: int | None = None
    default_amount: int | None = None
    default_description: str | None = None
    day_of_month: int | None = None
    month_of_year: int | None = None
    active: bool | None = None
    next_due: date | object = _UNCHANGED

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "next_due":
                if value is _UNCHANGED:
                    continue
                out[f.name] = value
                continue
            if value is not None:
                out[f.name] = value
        return out


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurringOverride:
    """Persisted sparse override for a single occurrence of a rule."""

    id: int
    rule_id: int
    occurrence_date: date
    state: OverrideState
    amount_override: int | None
    description_override: str | None
    date_override: date | None
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class NewRecurringOverride:
    """Insertable fields for a new sparse override."""

    rule_id: int
    occurrence_date: date
    state: OverrideState
    amount_override: int | None = None
    description_override: str | None = None
    date_override: date | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Occurrence:
    """Virtual (non-persisted) occurrence returned by the Phase 2 generator."""

    rule_id: int
    occurrence_date: date
    effective_date: date
    category_id: int
    account_id: int
    dest_account_id: int | None
    amount: int
    description: str
    is_overridden: bool
    is_skipped: bool
