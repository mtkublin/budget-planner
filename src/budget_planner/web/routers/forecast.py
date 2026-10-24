"""Forecast router (T-037)."""

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

_DEFAULT_HORIZON = 30
_MAX_HORIZON = 365


def _parse_horizon(request: Request) -> int:
    try:
        val = int(request.query_params.get("horizon_days", _DEFAULT_HORIZON))
    except (TypeError, ValueError):
        return _DEFAULT_HORIZON
    return max(1, min(val, _MAX_HORIZON))


def _series_to_plotly(series: forecast_service.ForecastSeries) -> dict[str, object]:
    xs = [d.on_date.isoformat() for d in series.days]
    totals = [d.totals_base_minor / 100 for d in series.days]
    return {
        "data": [
            {
                "x": xs,
                "y": totals,
                "type": "scatter",
                "mode": "lines",
                "name": "Projected fortune",
            }
        ],
        "layout": {
            "title": f"Forecast · {series.start_date} → {series.end_date}",
            "yaxis": {"title": f"{series.base_currency} (major)"},
            "margin": {"t": 40, "r": 20, "b": 40, "l": 60},
        },
    }


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    horizon = _parse_horizon(request)
    today = date.today()  # noqa: DTZ011
    with httpx.Client(timeout=5.0) as client:
        series = forecast_service.forecast(conn, client, today, horizon, settings.base_currency)
    plotly_json = json.dumps(_series_to_plotly(series))
    return render(
        request,
        "forecast/index.html",
        horizon=horizon,
        series=series,
        plotly_json=plotly_json,
    )


@router.get("/chart", response_class=HTMLResponse)
def chart_fragment(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    horizon = _parse_horizon(request)
    today = date.today()  # noqa: DTZ011
    with httpx.Client(timeout=5.0) as client:
        series = forecast_service.forecast(conn, client, today, horizon, settings.base_currency)
    plotly_json = json.dumps(_series_to_plotly(series))
    return render(
        request,
        "partials/forecast/_chart.html",
        plotly_json=plotly_json,
        series=series,
    )
