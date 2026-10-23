"""Recurring rules + overrides + virtual occurrence shape (ADR-0013)."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from typing import Any

from budget_planner.domain.enums import Cadence, OverrideState


@dataclass(frozen=True, slots=True, kw_only=True)
class RecurringRule:
    """Persisted recurring rule."""

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
class NewRecurringRule:
    """Insertable fields for a new recurring rule."""

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
    """Partial update DTO."""

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

    def as_dict(self) -> dict[str, Any]:
        return {
            f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None
        }


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
