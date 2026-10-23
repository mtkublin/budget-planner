"""Category entity + DTOs."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any

from budget_planner.domain.enums import Direction


@dataclass(frozen=True, slots=True, kw_only=True)
class Category:
    """Persisted category row."""

    id: int
    user_id: int
    name: str
    direction: Direction
    is_system: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NewCategory:
    """Insertable fields for a new category."""

    name: str
    direction: Direction
    user_id: int = 1
    is_system: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class PatchCategory:
    """Partial update DTO.

    `direction` is omitted intentionally — once a category has transactions,
    changing direction would silently flip balances. Enforced in the service
    layer.
    """

    name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None
        }
