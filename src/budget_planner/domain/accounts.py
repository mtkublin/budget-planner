"""Account entity + DTOs + stats."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class Account:
    """Persisted account row."""

    id: int
    user_id: int
    name: str
    type: str | None
    currency: str
    opening_balance: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NewAccount:
    """Insertable fields for a new account.

    `currency` is immutable per ADR-0006; omitted from `PatchAccount`.
    """

    name: str
    currency: str
    opening_balance: int = 0
    type: str | None = None
    user_id: int = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class PatchAccount:
    """Partial update DTO. `None` values mean "do not change"."""

    name: str | None = None
    type: str | None = None
    opening_balance: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return only the fields set to a non-None value."""
        return {
            f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountStats:
    """Derived stats returned by the Phase 2 balance service."""

    account_id: int
    balance: int
    base_balance: int
    txn_count: int
    last_txn_date: str | None
