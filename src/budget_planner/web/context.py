"""Shared Jinja context helpers (T-069, T-094).

Pure functions used as Jinja globals so templates can derive per-request
values (such as the FAB target URL) without plumbing them through every
router. See ADR-0023 for the FAB context-routing table and ADR-0026 for
the visibility scope narrowing.
"""

from __future__ import annotations

from fastapi import Request

_DEFAULT_TARGET: str = "/transactions/new"
_PLANNED_TARGET: str = "/planned/new"
_RECURRING_TARGET: str = "/recurring/new"


def fab_target_for(request: Request) -> str | None:
    """Return the URL the FAB should hx-get for the current page, or
    ``None`` when the FAB should not render.

    Allow-list (ADR-0026):

    - ``/`` (Overview) → ``/transactions/new``.
    - ``/ledger`` or ``/ledger/...`` with ``view=planned`` → ``/planned/new``.
    - ``/ledger`` or ``/ledger/...`` with ``view=recurring`` → ``/recurring/new``.
    - ``/ledger`` or ``/ledger/...`` otherwise → ``/transactions/new``.
    - everything else → ``None`` (FAB hidden).
    """
    path = request.url.path
    if path == "/":
        return _DEFAULT_TARGET
    if path == "/ledger" or path.startswith("/ledger/"):
        view = request.query_params.get("view", "actual")
        if view == "planned":
            return _PLANNED_TARGET
        if view == "recurring":
            return _RECURRING_TARGET
        return _DEFAULT_TARGET
    return None


__all__ = ["fab_target_for"]
