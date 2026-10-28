"""Today router — Rising Dough v2.

Delegates to the existing home router's data assembly, but renders the
v2 Today template (hero + Can-I-afford + Net worth + Upcoming) at the
canonical URL ``/today``. Phase 7 will retire ``/`` → ``/today`` shim.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from budget_planner.config import Settings
from budget_planner.services import (
    budget as budget_service,
    fortune as fortune_service,
)
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.rendering import render
from budget_planner.web.routers import home as home_router

router = APIRouter(tags=["today"])


@router.get("/today", response_class=HTMLResponse)
def today(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    today_d = datetime.now(ZoneInfo(settings.display_timezone)).date()
    year, month = today_d.year, today_d.month
    base_ccy = settings.base_currency

    account_rows, totals_by_ccy, fortune_base = home_router._collect_account_rows(conn, base_ccy)
    fortune = fortune_service.compute_fortune(conn, settings)
    summary = budget_service.month_summary(conn, year, month, today=today_d)
    pace = home_router._pace_tag(
        summary.totals.spent_minor, summary.totals.budgeted_minor, today_d, year, month
    )
    days_left = summary.days_until_next_income
    bar_pct = 0
    if summary.totals.budgeted_minor > 0:
        ratio = 100 * summary.totals.spent_minor / summary.totals.budgeted_minor
        bar_pct = max(0, min(100, int(ratio)))

    window_label, window_days = home_router._window_from(request)
    upcoming = home_router._list_upcoming(conn, today_d, window_days)

    return render(
        request,
        "today/index.html",
        today=today_d,
        year=year,
        month=month,
        base_ccy=base_ccy,
        fortune_base=fortune_base,
        fortune=fortune,
        account_rows=account_rows,
        totals_by_ccy=totals_by_ccy,
        summary=summary,
        pace=pace,
        days_left=days_left,
        bar_pct=bar_pct,
        upcoming=upcoming,
        window_label=window_label,
    )


@router.get("/afford", response_class=HTMLResponse)
def afford(
    request: Request,
    amount: str = "",
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    """ADR-0056 §3 — HTMX preview for the Can-I-afford input.

    Pure arithmetic: delta vs. per-day-left; no DB write.
    """
    today_d = datetime.now(ZoneInfo(settings.display_timezone)).date()
    summary = budget_service.month_summary(conn, today_d.year, today_d.month, today=today_d)
    days_left = summary.days_until_next_income or 1
    remaining_minor = max(0, summary.totals.budgeted_minor - summary.totals.spent_minor)
    left_per_day = remaining_minor // days_left

    try:
        amount_minor = round(float(amount or "0") * 100)
    except (TypeError, ValueError):
        amount_minor = 0

    new_remaining = max(0, remaining_minor - amount_minor)
    new_left_per_day = new_remaining // max(1, days_left - 1 if amount_minor else days_left)
    delta = new_left_per_day - left_per_day

    return render(
        request,
        "today/_afford_preview.html",
        amount_minor=amount_minor,
        new_left_per_day=new_left_per_day,
        delta=delta,
        base_ccy=settings.base_currency,
    )
