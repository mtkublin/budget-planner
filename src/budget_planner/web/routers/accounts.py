"""Accounts router (T-032).

Lists accounts with derived balance + stats, create/rename/soft-delete,
snapshot capture, and reconciliation. Business logic in services; this
router parses + renders.
"""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from budget_planner.config import Settings
from budget_planner.domain.accounts import NewAccount, PatchAccount
from budget_planner.domain.money import to_minor_units
from budget_planner.domain.snapshots import NewAccountSnapshot
from budget_planner.repositories import accounts as accounts_repo, snapshots as snapshots_repo
from budget_planner.services import (
    balance as balance_service,
    reconciliation as reconciliation_service,
)
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.htmx import trigger
from budget_planner.web.rendering import render

router = APIRouter(prefix="/accounts", tags=["accounts"])

_ISO_CCY_LEN = 3


def _today() -> date:
    return date.today()  # noqa: DTZ011 — intentional naive local date


def _hydrate(conn: sqlite3.Connection, settings: Settings) -> dict[str, Any]:
    accs = accounts_repo.list_all(conn)
    cards: list[dict[str, Any]] = []
    totals_by_ccy: dict[str, int] = {}
    for a in accs:
        bal = balance_service.derive_balance(conn, a.id)
        stats = balance_service.account_stats(conn, a.id)
        cards.append({"account": a, "balance": bal, "stats": stats})
        totals_by_ccy[a.currency] = totals_by_ccy.get(a.currency, 0) + bal
    fortune_base = (
        sum(totals_by_ccy.values())
        if len(totals_by_ccy) == 1
        else sum(v for k, v in totals_by_ccy.items() if k == settings.base_currency)
    )
    return {
        "cards": cards,
        "totals_by_ccy": totals_by_ccy,
        "fortune_base": fortune_base,
    }


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    data = _hydrate(conn, settings)
    return render(request, "accounts/index.html", **data)


@router.get("/new", response_class=HTMLResponse)
def new_form(request: Request) -> HTMLResponse:
    return render(
        request,
        "partials/accounts/_form.html",
        account=None,
        action="/accounts",
        errors={},
    )


@router.post("")
def create_account(  # noqa: PLR0917
    request: Request,
    name: str = Form(...),
    currency: str = Form(...),
    opening_balance: str = Form("0"),
    type: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    errors: dict[str, str] = {}
    cur = currency.upper().strip()
    if len(cur) != _ISO_CCY_LEN or not cur.isalpha():
        errors["currency"] = "ISO 4217 code required"
    try:
        opening_dec = Decimal(opening_balance or "0")
    except InvalidOperation:
        errors["opening_balance"] = "invalid number"
        opening_dec = Decimal(0)
    if not name.strip():
        errors["name"] = "name required"
    if errors:
        return render(
            request,
            "partials/accounts/_form.html",
            account=None,
            action="/accounts",
            errors=errors,
            status_code=422,
        )
    opening = to_minor_units(opening_dec, cur)
    acc = accounts_repo.create(
        conn,
        NewAccount(name=name.strip(), currency=cur, opening_balance=opening, type=type or None),
    )
    bal = balance_service.derive_balance(conn, acc.id)
    stats = balance_service.account_stats(conn, acc.id)
    html = render(
        request,
        "partials/accounts/_card.html",
        card={"account": acc, "balance": bal, "stats": stats},
    )
    trigger(html, "balance-stale")
    return html


@router.get("/{account_id}/edit", response_class=HTMLResponse)
def edit_form(
    account_id: int, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    acc = accounts_repo.find_by_id(conn, account_id)
    if acc is None:
        return render(
            request,
            "partials/accounts/_form.html",
            account=None,
            action="",
            errors={"account": "not found"},
            status_code=404,
        )
    return render(
        request,
        "partials/accounts/_form.html",
        account=acc,
        action=f"/accounts/{account_id}",
        errors={},
    )


@router.post("/{account_id}")
def update_account(
    account_id: int,
    request: Request,
    name: str = Form(...),
    type: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    acc = accounts_repo.find_by_id(conn, account_id)
    if acc is None:
        return render(
            request,
            "partials/accounts/_form.html",
            account=None,
            action="",
            errors={"account": "not found"},
            status_code=404,
        )
    if not name.strip():
        return render(
            request,
            "partials/accounts/_form.html",
            account=acc,
            action=f"/accounts/{account_id}",
            errors={"name": "name required"},
            status_code=422,
        )
    accounts_repo.update(conn, account_id, PatchAccount(name=name.strip(), type=type or None))
    updated = accounts_repo.find_by_id(conn, account_id)
    assert updated is not None
    bal = balance_service.derive_balance(conn, account_id)
    stats = balance_service.account_stats(conn, account_id)
    html = render(
        request,
        "partials/accounts/_card.html",
        card={"account": updated, "balance": bal, "stats": stats},
    )
    trigger(html, "balance-stale")
    return html


@router.post("/{account_id}/delete")
def delete_account(account_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    accounts_repo.soft_delete(conn, account_id)
    resp = Response(content="", media_type="text/html")
    trigger(resp, "balance-stale", "forecast-stale")
    return resp


@router.post("/{account_id}/snapshot")
def take_snapshot(
    account_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    acc = accounts_repo.find_by_id(conn, account_id)
    if acc is None:
        return Response(status_code=404, content="not found")
    bal = balance_service.derive_balance(conn, account_id)
    snap = snapshots_repo.create(
        conn, NewAccountSnapshot(account_id=account_id, balance=bal, note="user snapshot")
    )
    return render(
        request,
        "partials/accounts/_snapshot_item.html",
        snapshot=snap,
        account=acc,
    )


@router.get("/{account_id}/reconcile", response_class=HTMLResponse)
def reconcile_form(
    account_id: int, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    acc = accounts_repo.find_by_id(conn, account_id)
    if acc is None:
        return render(
            request,
            "partials/accounts/_reconcile_modal.html",
            account=None,
            derived=0,
            errors={"account": "not found"},
            status_code=404,
        )
    derived = balance_service.derive_balance(conn, account_id)
    return render(
        request,
        "partials/accounts/_reconcile_modal.html",
        account=acc,
        derived=derived,
        errors={},
    )


@router.post("/{account_id}/reconcile")
def reconcile_submit(
    account_id: int,
    request: Request,
    actual_balance: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    acc = accounts_repo.find_by_id(conn, account_id)
    if acc is None:
        return Response(status_code=404, content="not found")
    try:
        actual = Decimal(actual_balance)
    except InvalidOperation:
        return render(
            request,
            "partials/accounts/_reconcile_modal.html",
            account=acc,
            derived=0,
            errors={"actual_balance": "invalid number"},
            status_code=422,
        )
    actual_minor = to_minor_units(actual, acc.currency)
    with contextlib.suppress(reconciliation_service.NoAdjustmentNeededError):
        reconciliation_service.reconcile(conn, account_id, actual_minor, _today())
    bal = balance_service.derive_balance(conn, account_id)
    stats = balance_service.account_stats(conn, account_id)
    html = render(
        request,
        "partials/accounts/_card.html",
        card={"account": acc, "balance": bal, "stats": stats},
    )
    trigger(html, "balance-stale", "forecast-stale")
    return html
