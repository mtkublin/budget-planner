"""Account snapshot entity + New DTO (ADR-0011)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountSnapshot:
    """Append-only balance snapshot."""

    id: int
    account_id: int
    taken_at: datetime
    balance: int
    note: str


@dataclass(frozen=True, slots=True, kw_only=True)
class NewAccountSnapshot:
    """Insertable fields for a new snapshot."""

    account_id: int
    balance: int
    note: str = ""
