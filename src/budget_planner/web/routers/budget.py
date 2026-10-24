"""Budget router (T-036)."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from budget_planner.config import Settings
from budget_planner.domain.budgets import (
    NewBudgetDefault,
    NewBudgetOneOffOverride,
    NewBudgetRecurringOverride,
)
from budget_planner.domain.money import to_minor_units
from budget_planner.repositories import (
    budgets as budgets_repo,
    categories as categories_repo,
)
from budget_planner.services import budget as budget_service
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.htmx import trigger
from budget_planner.web.rendering import render

router = APIRouter(prefix="/budget", tags=["budget"])

_MONTHS_IN_YEAR = 12


def _year_month(request: Request) -> tuple[int, int]:
    q = request.query_params
    today = date.today()  # noqa: DTZ011
    year = int(q.get("year", today.year))
    month = int(q.get("month", today.month))
    return year, month


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    year, month = _year_month(request)
    summary = budget_service.month_summary(conn, year, month)
    return render(
        request,
        "budget/index.html",
        year=year,
        month=month,
        summary=summary,
        base_ccy=settings.base_currency,
    )


@router.get("/manage", response_class=HTMLResponse)
def manage(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    cats = categories_repo.list_all(conn)
    defaults = {d.category_id: d.amount for d in budgets_repo.list_defaults(conn)}
    return render(
        request,
        "budget/manage.html",
        categories=cats,
        defaults=defaults,
        base_ccy=settings.base_currency,
    )


def _parse_decimal(value: str) -> Decimal | None:
    try:
        dec = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not dec.is_finite():
        return None
    return dec


@router.post("/defaults/{category_id}")
def set_default(
    category_id: int,
    amount: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> Response:
    cat = categories_repo.find_by_id(conn, category_id)
    if cat is None:
        return Response(status_code=404, content="not found")
    dec = _parse_decimal(amount)
    if dec is None or dec < 0:
        return Response(status_code=422, content="invalid amount")
    minor = to_minor_units(dec, settings.base_currency)
    budgets_repo.set_default(conn, NewBudgetDefault(category_id=category_id, amount=minor))
    resp = Response(content="ok", media_type="text/html")
    trigger(resp, "budget-stale")
    return resp


@router.post("/recurring/{category_id}/{month}")
def set_recurring(
    category_id: int,
    month: int,
    amount: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> Response:
    cat = categories_repo.find_by_id(conn, category_id)
    if cat is None:
        return Response(status_code=404, content="not found")
    if month < 1 or month > _MONTHS_IN_YEAR:
        return Response(status_code=422, content="invalid month")
    dec = _parse_decimal(amount)
    if dec is None or dec < 0:
        return Response(status_code=422, content="invalid amount")
    minor = to_minor_units(dec, settings.base_currency)
    budgets_repo.set_recurring(
        conn,
        NewBudgetRecurringOverride(category_id=category_id, month=month, amount=minor),
    )
    resp = Response(content="ok", media_type="text/html")
    trigger(resp, "budget-stale")
    return resp


@router.post("/one-off/{category_id}/{year}/{month}")
def set_one_off(  # noqa: PLR0917
    category_id: int,
    year: int,
    month: int,
    amount: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> Response:
    cat = categories_repo.find_by_id(conn, category_id)
    if cat is None:
        return Response(status_code=404, content="not found")
    if month < 1 or month > _MONTHS_IN_YEAR:
        return Response(status_code=422, content="invalid month")
    dec = _parse_decimal(amount)
    if dec is None or dec < 0:
        return Response(status_code=422, content="invalid amount")
    minor = to_minor_units(dec, settings.base_currency)
    budgets_repo.set_one_off(
        conn,
        NewBudgetOneOffOverride(category_id=category_id, year=year, month=month, amount=minor),
    )
    resp = Response(content="ok", media_type="text/html")
    trigger(resp, "budget-stale")
    return resp
