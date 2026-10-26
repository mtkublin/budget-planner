"""Shared Jinja context helpers (T-069).

Pure functions used as Jinja globals so templates can derive per-request
values (such as the FAB target URL) without plumbing them through every
router. See ADR-0023 for the FAB context-routing table.
"""

from __future__ import annotations

from fastapi import Request

# WHY: central routing table keeps the FAB target decision in one place.
# Keys are URL path prefixes; the longest matching prefix wins so
# ``/accounts/42`` still resolves to ``/transactions/new``.
_DEFAULT_TARGET: str = "/transactions/new"
_PLANNED_TARGET: str = "/planned/new"
_RECURRING_TARGET: str = "/recurring/new"


def fab_target_for(request: Request) -> str:
    """Return the URL the FAB should hx-get for the current page.

    - ``/ledger?view=planned`` → ``/planned/new``.
    - ``/ledger?view=recurring`` → ``/recurring/new``.
    - everything else → ``/transactions/new``.
    """
    path = request.url.path
    if path == "/ledger" or path.startswith("/ledger/"):
        view = request.query_params.get("view", "actual")
        if view == "planned":
            return _PLANNED_TARGET
        if view == "recurring":
            return _RECURRING_TARGET
        return _DEFAULT_TARGET
    return _DEFAULT_TARGET


__all__ = ["fab_target_for"]
