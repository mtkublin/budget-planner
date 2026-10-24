"""Home router (T-039).

Dashboard: current-month budget summary + fortune total + next-7-days planned.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from budget_planner.config import Settings
from budget_planner.domain.planned import PlannedFilter
from budget_planner.repositories import accounts as accounts_repo
from budget_planner.services import (
    balance as balance_service,
    budget as budget_service,
    planned as planned_service,
)
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.rendering import render

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    today = date.today()  # noqa: DTZ011
    year, month = today.year, today.month

    # Fortune: sum derived balance across live accounts in each account's currency,
    # then sum the base-currency entries only (ADR-0006 full FX conversion is T-032 scope).
    accs = accounts_repo.list_all(conn)
    totals_by_ccy: dict[str, int] = {}
    for a in accs:
        bal = balance_service.derive_balance(conn, a.id)
        totals_by_ccy[a.currency] = totals_by_ccy.get(a.currency, 0) + bal
    fortune_base = totals_by_ccy.get(settings.base_currency, 0)

    summary = budget_service.month_summary(conn, year, month)

    week_end = today + timedelta(days=7)
    upcoming = list(
        planned_service.list_planned(
            conn,
            PlannedFilter(date_from=today, date_to=week_end, promoted=False),
        )
    )

    return render(
        request,
        "home/index.html",
        today=today,
        year=year,
        month=month,
        fortune_base=fortune_base,
        totals_by_ccy=totals_by_ccy,
        summary=summary,
        upcoming=upcoming,
        base_ccy=settings.base_currency,
    )
