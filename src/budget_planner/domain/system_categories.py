"""Shared constants for the system-managed categories.

The ``Transit`` and ``Reconciliation`` categories are seeded by migration
``0003_seed_system_rows.sql`` and flagged ``is_system = 1``. Service-layer
guards reject rename, direction-change, and delete for any row with that
flag — see ADR-0019 and the T-012 plan under ``docs/plans/phase-1/``.
"""

from __future__ import annotations

from typing import Final

TRANSIT_CATEGORY_NAME: Final[str] = "Transit"
RECONCILIATION_CATEGORY_NAME: Final[str] = "Reconciliation"

SYSTEM_CATEGORY_NAMES: Final[frozenset[str]] = frozenset(
    {TRANSIT_CATEGORY_NAME, RECONCILIATION_CATEGORY_NAME}
)
