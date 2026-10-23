"""Account entity + DTOs + stats."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
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
    """Derived stats returned by the Phase 2 balance service.

    - ``balance`` / ``base_balance`` are minor units; ``base_balance`` is set
      by callers that convert through FX (service returns ``balance`` in it
      until that conversion happens, so unit tests do not depend on FX).
    - ``avg_inflow_minor`` / ``avg_outflow_minor`` cover only
      ``income`` / ``expense`` legs (transit + adjustment skipped — see
      T-021 plan).
    - ``last_txn_date`` is ISO ``YYYY-MM-DD`` for easy template rendering.
    """

    account_id: int
    balance: int
    base_balance: int
    txn_count: int
    last_txn_date: str | None
    avg_inflow_minor: int = 0
    avg_outflow_minor: int = 0

    @property
    def last_activity_date(self) -> date | None:
        """Parse ``last_txn_date`` into a ``date`` for typed consumers."""
        if self.last_txn_date is None:
            return None
        return date.fromisoformat(self.last_txn_date)
