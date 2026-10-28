"""Forecast router (T-037, ADR-0043).

The user-facing horizon is specified in **months** (ADR-0043) and expanded
to days at the router boundary so the pure daily projection service stays
unchanged. Chart granularity is monthly: one point per month at EOM.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from budget_planner.config import Settings
from budget_planner.services import forecast as forecast_service
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.rendering import render

router = APIRouter(prefix="/forecast", tags=["forecast"])

_DEFAULT_HORIZON_MONTHS = 12
_MIN_HORIZON_MONTHS = 1
_MAX_HORIZON_MONTHS = 60


def _parse_horizon_months(request: Request) -> int:
    try:
        val = int(request.query_params.get("horizon_months", _DEFAULT_HORIZON_MONTHS))
    except (TypeError, ValueError):
        return _DEFAULT_HORIZON_MONTHS
    return max(_MIN_HORIZON_MONTHS, min(val, _MAX_HORIZON_MONTHS))


def _monthly_to_plotly(monthly: forecast_service.MonthlySeries) -> dict[str, object]:
    xs = [m.month.isoformat() for m in monthly.months]
    totals = [m.end_balance_base_minor / 100 for m in monthly.months]
    return {
        "data": [
            {
                "x": xs,
                "y": totals,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Projected fortune (EOM)",
            }
        ],
        "layout": {
            "title": f"Forecast · {monthly.start_month} → {monthly.end_month}",
            "yaxis": {"title": f"{monthly.base_currency} (major)"},
            "xaxis": {"tickformat": "%b %Y"},
            "margin": {"t": 40, "r": 20, "b": 40, "l": 60},
        },
    }


def _compute(
    conn: sqlite3.Connection,
    settings: Settings,
    horizon_months: int,
) -> forecast_service.MonthlySeries:
    today = date.today()  # noqa: DTZ011
    with httpx.Client(timeout=5.0) as client:
        return forecast_service.forecast_monthly(
            conn, client, today, horizon_months, settings.base_currency
        )


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    horizon_months = _parse_horizon_months(request)
    monthly = _compute(conn, settings, horizon_months)
    plotly_json = json.dumps(_monthly_to_plotly(monthly))
    return render(
        request,
        "forecast/index.html",
        horizon_months=horizon_months,
        monthly=monthly,
        plotly_json=plotly_json,
    )


@router.get("/view", response_class=HTMLResponse)
def view_fragment(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    horizon_months = _parse_horizon_months(request)
    monthly = _compute(conn, settings, horizon_months)
    plotly_json = json.dumps(_monthly_to_plotly(monthly))
    return render(
        request,
        "partials/forecast/_view.html",
        plotly_json=plotly_json,
        monthly=monthly,
        horizon_months=horizon_months,
    )
