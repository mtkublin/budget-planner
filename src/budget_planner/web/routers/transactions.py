"""Transactions router (T-031).

Thin HTTP surface over `repositories.transactions` + `services.export`.
Parses form input, calls the service / repo, renders Jinja fragments.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from budget_planner.config import Settings
from budget_planner.domain.enums import Direction
from budget_planner.domain.money import to_minor_units
from budget_planner.domain.transactions import (
    NewTransaction,
    PatchTransaction,
    TransactionFilter,
)
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    transactions as transactions_repo,
)
from budget_planner.services import export as export_service
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.htmx import trigger
from budget_planner.web.rendering import render

router = APIRouter(prefix="/transactions", tags=["transactions"])

_PAGE_SIZE_DEFAULT = 50


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_filter(request: Request) -> TransactionFilter:
    """Parse the shared filter query params. Public — reused by T-038."""
    q = request.query_params
    account_id = _parse_int(q.get("account_id"))
    category_id = _parse_int(q.get("category_id"))
    description = q.get("q") or None
    return TransactionFilter(
        date_from=_parse_date(q.get("date_from")),
        date_to=_parse_date(q.get("date_to")),
        account_ids=(account_id,) if account_id is not None else (),
        category_ids=(category_id,) if category_id is not None else (),
        amount_min=_parse_int(q.get("min_amount")),
        amount_max=_parse_int(q.get("max_amount")),
        description_contains=description,
    )


def _page(request: Request) -> tuple[int, int]:
    page = max(1, _parse_int(request.query_params.get("page")) or 1)
    size = _parse_int(request.query_params.get("page_size")) or _PAGE_SIZE_DEFAULT
    return page, max(1, min(size, 500))


def _hydrate_rows(conn: sqlite3.Connection, rows: list[Any]) -> list[dict[str, Any]]:
    cats = {c.id: c for c in categories_repo.list_all(conn, include_deleted=True)}
    accts = {a.id: a for a in accounts_repo.list_all(conn, include_deleted=True)}
    out: list[dict[str, Any]] = []
    for r in rows:
        cat = cats.get(r.category_id)
        acc = accts.get(r.account_id)
        dest = accts.get(r.dest_account_id) if r.dest_account_id is not None else None
        out.append(
            {
                "id": r.id,
                "operation_date": r.operation_date,
                "amount": r.amount,
                "description": r.description,
                "category": cat,
                "account": acc,
                "dest_account": dest,
                "currency": acc.currency if acc else "",
            }
        )
    return out


@router.get("", response_class=HTMLResponse)
def list_page(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    flt = parse_filter(request)
    page, size = _page(request)
    paged = TransactionFilter(
        date_from=flt.date_from,
        date_to=flt.date_to,
        account_ids=flt.account_ids,
        category_ids=flt.category_ids,
        amount_min=flt.amount_min,
        amount_max=flt.amount_max,
        description_contains=flt.description_contains,
        limit=size,
        offset=(page - 1) * size,
    )
    rows = _hydrate_rows(conn, transactions_repo.list_filtered(conn, paged))
    cats = categories_repo.list_all(conn)
    accs = accounts_repo.list_all(conn)
    return render(
        request,
        "transactions/index.html",
        rows=rows,
        categories=cats,
        accounts=accs,
        filter=flt,
        page=page,
        page_size=size,
        has_next=len(rows) == size,
    )


@router.get("/table", response_class=HTMLResponse)
def table_fragment(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    """Legacy fragment alias (T-064).

    Delegates to the unified ledger fragment with ``view=actual`` so pre-T-064
    HTMX scripts keep working. The response shape (``#txn-table`` container,
    row ids ``#txn-{id}``) is preserved by the ledger template.
    """
    from budget_planner.web.routers.ledger import render_table_for  # noqa: PLC0415

    return render_table_for(request, conn, "actual")


@router.get("/new", response_class=HTMLResponse)
def new_form(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    return render(
        request,
        "partials/transactions/_form.html",
        action="/transactions",
        method="post",
        txn=None,
        categories=categories_repo.list_all(conn),
        accounts=accounts_repo.list_all(conn),
        errors={},
    )


def _validate_amount(amount: str, currency: str) -> tuple[int | None, str | None]:
    try:
        dec = Decimal(amount)
    except (InvalidOperation, TypeError):
        return None, "amount must be a decimal number"
    if dec <= 0:
        return None, "amount must be positive"
    minor = to_minor_units(dec, currency)
    return minor, None


@router.post("")
def create_txn(  # noqa: PLR0917
    request: Request,
    operation_date: str = Form(...),
    category_id: int = Form(...),
    account_id: int = Form(...),
    amount: str = Form(...),
    description: str = Form(""),
    dest_account_id: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),  # noqa: ARG001
) -> Response:
    errors: dict[str, str] = {}
    op_date = _parse_date(operation_date)
    if op_date is None:
        errors["operation_date"] = "invalid date"
    acc = accounts_repo.find_by_id(conn, account_id)
    cat = categories_repo.find_by_id(conn, category_id)
    if acc is None:
        errors["account_id"] = "unknown account"
    if cat is None:
        errors["category_id"] = "unknown category"
    minor: int | None = None
    if acc is not None:
        minor, err = _validate_amount(amount, acc.currency)
        if err is not None:
            errors["amount"] = err
    dest_id: int | None = None
    if dest_account_id and cat is not None and cat.direction == Direction.TRANSIT:
        parsed = _parse_int(dest_account_id)
        if parsed is None:
            errors["dest_account_id"] = "invalid destination"
        else:
            dest = accounts_repo.find_by_id(conn, parsed)
            if dest is None:
                errors["dest_account_id"] = "unknown destination"
            elif acc is not None and dest.currency != acc.currency:
                errors["dest_account_id"] = "cross-currency transit not supported"
            else:
                dest_id = parsed

    if errors:
        return render(
            request,
            "partials/transactions/_form.html",
            action="/transactions",
            method="post",
            txn=None,
            categories=categories_repo.list_all(conn),
            accounts=accounts_repo.list_all(conn),
            errors=errors,
            status_code=422,
        )

    assert op_date is not None and minor is not None
    new_txn = transactions_repo.create(
        conn,
        NewTransaction(
            operation_date=op_date,
            category_id=category_id,
            account_id=account_id,
            amount=minor,
            description=description,
            dest_account_id=dest_id,
        ),
    )
    row = _hydrate_rows(conn, [new_txn])[0]
    html = render(
        request,
        "partials/transactions/_row.html",
        txn=row,
    )
    trigger(html, "balance-stale", "forecast-stale")
    return html


@router.get("/{txn_id}/edit", response_class=HTMLResponse)
def edit_form(
    txn_id: int, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    txn = transactions_repo.find_by_id(conn, txn_id)
    if txn is None:
        return render(
            request,
            "partials/transactions/_form.html",
            action="",
            method="post",
            txn=None,
            categories=[],
            accounts=[],
            errors={"txn": "not found"},
            status_code=404,
        )
    return render(
        request,
        "partials/transactions/_form.html",
        action=f"/transactions/{txn_id}",
        method="post",
        txn=txn,
        categories=categories_repo.list_all(conn),
        accounts=accounts_repo.list_all(conn),
        errors={},
    )


@router.post("/{txn_id}")
def update_txn(  # noqa: PLR0917
    txn_id: int,
    request: Request,
    operation_date: str = Form(...),
    category_id: int = Form(...),
    account_id: int = Form(...),
    amount: str = Form(...),
    description: str = Form(""),
    dest_account_id: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    existing = transactions_repo.find_by_id(conn, txn_id)
    if existing is None:
        return render(
            request,
            "partials/transactions/_form.html",
            action="",
            method="post",
            txn=None,
            categories=[],
            accounts=[],
            errors={"txn": "not found"},
            status_code=404,
        )
    acc = accounts_repo.find_by_id(conn, account_id)
    errors: dict[str, str] = {}
    op_date = _parse_date(operation_date)
    if op_date is None:
        errors["operation_date"] = "invalid date"
    if acc is None:
        errors["account_id"] = "unknown account"
    minor: int | None = None
    if acc is not None:
        minor, err = _validate_amount(amount, acc.currency)
        if err is not None:
            errors["amount"] = err
    if errors:
        return render(
            request,
            "partials/transactions/_form.html",
            action=f"/transactions/{txn_id}",
            method="post",
            txn=existing,
            categories=categories_repo.list_all(conn),
            accounts=accounts_repo.list_all(conn),
            errors=errors,
            status_code=422,
        )
    assert op_date is not None and minor is not None
    dest_id_val = _parse_int(dest_account_id) if dest_account_id else None
    transactions_repo.update(
        conn,
        txn_id,
        PatchTransaction(
            operation_date=op_date,
            category_id=category_id,
            account_id=account_id,
            amount=minor,
            description=description,
            dest_account_id=dest_id_val,
        ),
    )
    updated = transactions_repo.find_by_id(conn, txn_id)
    assert updated is not None
    row = _hydrate_rows(conn, [updated])[0]
    html = render(request, "partials/transactions/_row.html", txn=row)
    trigger(html, "balance-stale", "forecast-stale")
    return html


@router.post("/{txn_id}/delete")
def delete_txn(txn_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    transactions_repo.soft_delete(conn, txn_id)
    resp = Response(content="", media_type="text/html")
    trigger(resp, "balance-stale", "forecast-stale")
    return resp


@router.get("/export")
def export(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    fmt = request.query_params.get("format", "csv")
    flt = parse_filter(request)
    rows = transactions_repo.list_filtered(conn, flt)
    hydrated = _hydrate_rows(conn, rows)
    export_rows: list[dict[str, Any]] = [
        {
            "id": r["id"],
            "operation_date": r["operation_date"],
            "amount_minor": r["amount"],
            "currency": r["currency"],
            "description": r["description"] or "",
            "category": r["category"].name if r["category"] else "",
            "account": r["account"].name if r["account"] else "",
            "dest_account": r["dest_account"].name if r["dest_account"] else "",
        }
        for r in hydrated
    ]
    columns = [
        export_service.ExportColumn(key="id", header="id", kind="int"),
        export_service.ExportColumn(key="operation_date", header="date", kind="date"),
        export_service.ExportColumn(key="amount_minor", header="amount_minor", kind="money_minor"),
        export_service.ExportColumn(key="currency", header="currency", kind="str"),
        export_service.ExportColumn(key="description", header="description", kind="str"),
        export_service.ExportColumn(key="category", header="category", kind="str"),
        export_service.ExportColumn(key="account", header="account", kind="str"),
        export_service.ExportColumn(key="dest_account", header="dest_account", kind="str"),
    ]
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    if fmt == "parquet":
        body = export_service.export_parquet(export_rows, columns)
        return Response(
            content=body,
            media_type="application/vnd.apache.parquet",
            headers={"Content-Disposition": f'attachment; filename="transactions_{stamp}.parquet"'},
        )
    body = export_service.export_csv(export_rows, columns)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="transactions_{stamp}.csv"'},
    )
