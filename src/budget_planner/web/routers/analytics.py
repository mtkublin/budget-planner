"""Analytics router (T-038).

Simple aggregate dashboard: spend by category, cash-flow by account, income vs
expense trend. Uses `services.balance.signed_legs` + direct repository scans
for grouping; no new SQL added.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from budget_planner.config import Settings
from budget_planner.domain.enums import Direction
from budget_planner.domain.transactions import TransactionFilter
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    transactions as transactions_repo,
)
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.rendering import render

router = APIRouter(prefix="/analytics", tags=["analytics"])


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
    ys = [v / 100 for v in data.values()]
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
    income = [data[m]["income"] / 100 for m in months]
    expense = [data[m]["expense"] / 100 for m in months]
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


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    spend = _spend_by_category(conn)
    cashflow = _cashflow_by_account(conn)
    monthly = _income_vs_expense_by_month(conn)
    return render(
        request,
        "analytics/index.html",
        spend_json=json.dumps(_bar(spend, "Spend by category", settings.base_currency)),
        cashflow_json=json.dumps(_bar(cashflow, "Cashflow by account", settings.base_currency)),
        monthly_json=json.dumps(_income_expense_lines(monthly, settings.base_currency)),
    )
