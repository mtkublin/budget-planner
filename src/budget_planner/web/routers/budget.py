"""Budget router (T-036 / T-066).

T-066 consolidates `/budget` into three stacked sections:

1. Monthly summary — current month default, month selector top-right.
2. Rules editor — per-category default / recurring(month) / one-off(year, month).
3. Breakdown — three Plotly figures lifted from ``/analytics``.

Thin router per ADR-0021: services do the aggregation, the router only shapes
the response. The three breakdown aggregates intentionally re-use the same
pure helpers that back ``/analytics`` so both pages stay in lock-step until
T-070 redirects ``/analytics`` here.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from budget_planner.config import Settings
from budget_planner.domain.budgets import (
    NewBudgetDefault,
    NewBudgetOneOffOverride,
    NewBudgetRecurringOverride,
)
from budget_planner.domain.enums import Direction
from budget_planner.domain.money import to_minor_units
from budget_planner.domain.transactions import TransactionFilter
from budget_planner.repositories import (
    accounts as accounts_repo,
    budgets as budgets_repo,
    categories as categories_repo,
    transactions as transactions_repo,
)
from budget_planner.services import budget as budget_service
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.htmx import trigger
from budget_planner.web.rendering import render

router = APIRouter(prefix="/budget", tags=["budget"])

_MONTHS_IN_YEAR = 12
_MINOR_UNITS_PER_MAJOR = 100


@dataclass(frozen=True, slots=True)
class RulesRow:
    """One row of the Rules editor table."""

    category_id: int
    category_name: str
    default_minor: int
    recurring_minor: int | None
    one_off_minor: int | None


def _year_month(request: Request) -> tuple[int, int]:
    q = request.query_params
    today = date.today()  # noqa: DTZ011
    year = int(q.get("year", today.year))
    month = int(q.get("month", today.month))
    return year, month


def _rules_rows(conn: sqlite3.Connection, year: int, month: int) -> tuple[RulesRow, ...]:
    """Collect the per-category three-tier editable rows for the Rules section."""
    cats = [c for c in categories_repo.list_all(conn) if not c.is_system]
    defaults = {d.category_id: d.amount for d in budgets_repo.list_defaults(conn)}
    recurring = {
        r.category_id: r.amount for r in budgets_repo.list_recurring(conn) if r.month == month
    }
    one_off = {
        o.category_id: o.amount
        for o in budgets_repo.list_one_off(conn, year=year)
        if o.month == month
    }
    rows = [
        RulesRow(
            category_id=cat.id,
            category_name=cat.name,
            default_minor=defaults.get(cat.id, 0),
            recurring_minor=recurring.get(cat.id),
            one_off_minor=one_off.get(cat.id),
        )
        for cat in cats
    ]
    rows.sort(key=lambda r: r.category_name.casefold())
    return tuple(rows)


# ---------------------------------------------------------------------------
# Breakdown aggregates (duplicated with routers.analytics for one release; T-070
# will redirect /analytics → /budget#breakdown and this becomes the sole owner).
# ---------------------------------------------------------------------------


def _spend_by_category(conn: sqlite3.Connection) -> dict[str, int]:
    cats = {c.id: c for c in categories_repo.list_all(conn, include_deleted=True)}
    txns = transactions_repo.list_filtered(conn, TransactionFilter(directions=(Direction.EXPENSE,)))
    totals: dict[str, int] = defaultdict(int)
    for t in txns:
        name = cats[t.category_id].name if t.category_id in cats else "?"
        totals[name] += t.amount
    return dict(totals)


def _cashflow_by_account(conn: sqlite3.Connection) -> dict[str, int]:
    accs = {a.id: a for a in accounts_repo.list_all(conn, include_deleted=True)}
    txns = transactions_repo.list_filtered(conn, TransactionFilter())
    cats = {c.id: c for c in categories_repo.list_all(conn, include_deleted=True)}
    totals: dict[str, int] = defaultdict(int)
    for t in txns:
        acc = accs.get(t.account_id)
        if acc is None:
            continue
        cat = cats.get(t.category_id)
        if cat is None:
            continue
        if cat.direction == Direction.INCOME:
            totals[acc.name] += t.amount
        elif cat.direction == Direction.EXPENSE:
            totals[acc.name] -= t.amount
    return dict(totals)


def _income_vs_expense_by_month(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    cats = {c.id: c for c in categories_repo.list_all(conn, include_deleted=True)}
    txns = transactions_repo.list_filtered(conn, TransactionFilter())
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"income": 0, "expense": 0})
    for t in txns:
        cat = cats.get(t.category_id)
        if cat is None:
            continue
        key = t.operation_date.strftime("%Y-%m")
        if cat.direction == Direction.INCOME:
            monthly[key]["income"] += t.amount
        elif cat.direction == Direction.EXPENSE:
            monthly[key]["expense"] += t.amount
    return dict(monthly)


def _bar(data: dict[str, int], title: str, currency: str) -> dict[str, Any]:
    xs = list(data.keys())
    ys = [v / _MINOR_UNITS_PER_MAJOR for v in data.values()]
    return {
        "data": [{"x": xs, "y": ys, "type": "bar", "name": title}],
        "layout": {
            "title": title,
            "yaxis": {"title": currency},
            "margin": {"t": 40, "r": 20, "b": 60, "l": 60},
        },
    }


def _income_expense_lines(data: dict[str, dict[str, int]], currency: str) -> dict[str, Any]:
    months = sorted(data.keys())
    income = [data[m]["income"] / _MINOR_UNITS_PER_MAJOR for m in months]
    expense = [data[m]["expense"] / _MINOR_UNITS_PER_MAJOR for m in months]
    return {
        "data": [
            {"x": months, "y": income, "name": "income", "type": "bar"},
            {"x": months, "y": expense, "name": "expense", "type": "bar"},
        ],
        "layout": {
            "title": "Income vs expense (monthly)",
            "barmode": "group",
            "yaxis": {"title": currency},
            "margin": {"t": 40, "r": 20, "b": 60, "l": 60},
        },
    }


def _breakdown_payloads(conn: sqlite3.Connection, base_ccy: str) -> dict[str, str]:
    """Build the three JSON payloads for the Breakdown section."""
    spend = _spend_by_category(conn)
    cashflow = _cashflow_by_account(conn)
    monthly = _income_vs_expense_by_month(conn)
    return {
        "spend_json": json.dumps(_bar(spend, "Spend by category", base_ccy)),
        "cashflow_json": json.dumps(_bar(cashflow, "Cashflow by account", base_ccy)),
        "monthly_json": json.dumps(_income_expense_lines(monthly, base_ccy)),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _render_index(
    request: Request,
    conn: sqlite3.Connection,
    settings: Settings,
) -> HTMLResponse:
    year, month = _year_month(request)
    summary = budget_service.month_summary(conn, year, month)
    rules = _rules_rows(conn, year, month)
    breakdown = _breakdown_payloads(conn, settings.base_currency)
    return render(
        request,
        "budget/index.html",
        year=year,
        month=month,
        summary=summary,
        rules=rules,
        base_ccy=settings.base_currency,
        spend_json=breakdown["spend_json"],
        cashflow_json=breakdown["cashflow_json"],
        monthly_json=breakdown["monthly_json"],
    )


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    return _render_index(request, conn, settings)


@router.get("/manage", response_class=HTMLResponse)
def manage(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    """Legacy entrypoint kept live for one release (T-070 will redirect).

    Renders the same consolidated page as ``/budget`` so the Rules editor
    section is reachable at both URLs.
    """
    return _render_index(request, conn, settings)


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
