"""Plan hub — Rising Dough v2 (ADR-0051 §5).

Renders a tabbed shell (Budget · Year · Forecast · Analytics) with the
period header above tabs. Each tab assembles data from the existing
service helpers and renders a v2 template.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from budget_planner.config import Settings
from budget_planner.services import budget as budget_service
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.rendering import render

router = APIRouter(tags=["plan"])

PlanTab = Literal["budget", "year", "forecast", "analytics"]
_VALID: tuple[PlanTab, ...] = ("budget", "year", "forecast", "analytics")


@router.get("/plan", response_class=HTMLResponse)
def plan(
    request: Request,
    tab: str = "budget",
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    tab_norm: PlanTab = tab if tab in _VALID else "budget"
    today_d = datetime.now(ZoneInfo(settings.display_timezone)).date()
    year, month = today_d.year, today_d.month
    base_ccy = settings.base_currency

    ctx: dict[str, Any] = {
        "tab": tab_norm,
        "today": today_d,
        "year": year,
        "month": month,
        "base_ccy": base_ccy,
    }

    if tab_norm == "budget":
        ctx["summary"] = budget_service.month_summary(conn, year, month, today=today_d)
    elif tab_norm == "year":
        ctx["cells"] = []  # heatmap stub (T-R31)
    elif tab_norm == "forecast":
        ctx["points"] = []  # SVG chart stub (Phase 5)
    else:
        ctx["bundle"] = {"spend_by_category": [], "largest_items": []}

    return render(request, "plan/index.html", **ctx)


@router.get("/budget-legacy", include_in_schema=False)
def _redirect_budget() -> RedirectResponse:
    return RedirectResponse(url="/plan?tab=budget", status_code=302)
