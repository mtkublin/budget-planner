"""T-038 analytics router.

Post-T-070 the top-level ``/analytics`` page redirects to the Budget
breakdown anchor; the three figures previously lived here now render under
``/budget`` (covered by ``test_budget.py``). The remaining test here nails
down the redirect contract.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_index_redirects_to_budget_breakdown(client: TestClient) -> None:
    """``/analytics`` returns 302 to ``/budget#budget-breakdown``."""
    r = client.get("/analytics", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/budget#budget-breakdown"
