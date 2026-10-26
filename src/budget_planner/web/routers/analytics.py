"""Analytics router (T-038 → T-070).

The three analytics figures (spend by category, cash-flow by account, income
vs expense trend) now live under ``/budget`` as part of the Breakdown
section (T-066). ``/analytics`` returns ``302`` to the Budget breakdown
anchor for one release; after that the whole module becomes removable.

Keeping the module (and the ``/analytics`` prefix) makes the redirect
discoverable from the router registry and keeps bookmarks working. The
aggregation helpers that used to live here were duplicated into
``routers.budget`` as part of T-066 and are no longer needed here.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def index() -> RedirectResponse:
    """Legacy page URL (T-070).

    Redirects to the Budget page's breakdown section. Kept at ``302`` for one
    release per ADR-0023; a follow-up task flips to ``301`` and removes this
    module in a Phase 7 cleanup.
    """
    return RedirectResponse(url="/budget#budget-breakdown", status_code=302)
