"""FX rate entity + New DTO (ADR-0006 / ADR-0008)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class FxRate:
    """Append-only exchange rate for a specific (date, from_ccy, to_ccy)."""

    id: int
    date: date
    from_ccy: str
    to_ccy: str
    rate: Decimal
    fetched_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class NewFxRate:
    """Insertable fields for a new FX rate."""

    date: date
    from_ccy: str
    to_ccy: str
    rate: Decimal
