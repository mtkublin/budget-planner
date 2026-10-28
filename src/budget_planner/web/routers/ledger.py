"""Ledger router (T-064).

Unifies ``/transactions``, ``/planned``, and ``/recurring`` behind a single
``/ledger`` page + ``/ledger/table`` fragment with a ``view`` query parameter.
Routers stay thin: dispatch picks the service/repository per view and renders
one template. See ADR-0023 for the information-architecture decision.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from budget_planner.domain.planned import PlannedFilter
from budget_planner.domain.transactions import TransactionFilter
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    recurring as recurring_repo,
    transactions as transactions_repo,
)
from budget_planner.services import planned as planned_service, recurring_formula as formula_svc
from budget_planner.web.deps import get_db
from budget_planner.web.ledger_types import LedgerFilters, ViewKind, coerce_view, view_kinds
from budget_planner.web.rendering import render

router = APIRouter(prefix="/ledger", tags=["ledger"])

_PAGE_SIZE_DEFAULT = 50
_PAGE_SIZE_MAX = 500


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


def parse_filters(request: Request) -> LedgerFilters:
    """Parse the shared ledger filter from the request's query params."""
    q = request.query_params
    account_id = _parse_int(q.get("account_id"))
    category_id = _parse_int(q.get("category_id"))
    page = max(1, _parse_int(q.get("page")) or 1)
    size = _parse_int(q.get("page_size")) or _PAGE_SIZE_DEFAULT
    size = max(1, min(size, _PAGE_SIZE_MAX))
    description = q.get("q") or None
    return LedgerFilters(
        date_from=_parse_date(q.get("date_from")),
        date_to=_parse_date(q.get("date_to")),
        account_ids=(account_id,) if account_id is not None else (),
        category_ids=(category_id,) if category_id is not None else (),
        direction=q.get("direction") or None,
        search=description,
        page=page,
        page_size=size,
    )


def _hydrate_txn_rows(conn: sqlite3.Connection, rows: list[Any]) -> list[dict[str, Any]]:
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


def _hydrate_planned_rows(conn: sqlite3.Connection, views: list[Any]) -> list[dict[str, Any]]:
    cats = {c.id: c for c in categories_repo.list_all(conn, include_deleted=True)}
    accts = {a.id: a for a in accounts_repo.list_all(conn, include_deleted=True)}
    out: list[dict[str, Any]] = []
    for v in views:
        cat = cats.get(v.category_id)
        acc = accts.get(v.account_id)
        key = (
            f"p-{v.persisted_id}"
            if v.persisted_id is not None
            else f"v-{v.recurring_rule_id}-{v.operation_date.strftime('%Y%m%d')}"
        )
        out.append(
            {
                "key": key,
                "kind": v.kind,
                "operation_date": v.operation_date,
                "amount_minor": v.amount_minor,
                "description": v.description,
                "is_promoted": v.is_promoted,
                "persisted_id": v.persisted_id,
                "recurring_rule_id": v.recurring_rule_id,
                "account": acc,
                "category": cat,
                "currency": acc.currency if acc else "",
            }
        )
    return out


def _hydrate_recurring_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    # Ledger Recurring tab lists only live rules (ADR-0038 §Ledger-UI):
    # Delete behaviourally deactivates, which must remove the row from view.
    rules = sorted(
        recurring_repo.list_rules(conn, active_only=True),
        key=lambda r: (r.next_due, r.id),
    )
    cats = {c.id: c for c in categories_repo.list_all(conn, include_deleted=True)}
    accts = {a.id: a for a in accounts_repo.list_all(conn, include_deleted=True)}
    out: list[dict[str, Any]] = []
    for rule in rules:
        acc = accts.get(rule.account_id)
        cat = cats.get(rule.category_id)
        overrides = recurring_repo.list_overrides(conn, rule.id)
        # T-122: locate the override (if any) on the current `next_due` so the
        # row can bold / italicise the appropriate cells.
        override_on_next_due = next(
            (ov for ov in overrides if ov.occurrence_date == rule.next_due),
            None,
        )
        # Formula-aware default: fixed rules use `rule.default_amount`;
        # formula rules recompute from the current source-rule state for
        # the `next_due` calendar month (ADR-0045). Overrides win per the
        # unchanged ADR-0038 override precedence.
        formula_amount = formula_svc.resolve_rule_amount(conn, rule, rule.next_due)
        effective_amount_minor = (
            override_on_next_due.amount_override
            if override_on_next_due is not None and override_on_next_due.amount_override is not None
            else formula_amount
        )
        out.append(
            {
                "id": rule.id,
                "cadence": rule.cadence,
                "start_date": rule.start_date,
                "next_due": rule.next_due,
                "default_amount": rule.default_amount,
                "default_description": rule.default_description,
                "active": rule.active,
                "account": acc,
                "category": cat,
                "overrides": overrides,
                "override_on_next_due": override_on_next_due,
                "override_present": override_on_next_due is not None,
                "amount_overridden": (
                    override_on_next_due is not None
                    and override_on_next_due.amount_override is not None
                ),
                "effective_amount_minor": effective_amount_minor,
                "amount_formula": rule.amount_formula,
                "is_formula": rule.amount_formula is not None,
                "currency": acc.currency if acc else "",
            }
        )
    return out


def _actual_rows(conn: sqlite3.Connection, filters: LedgerFilters) -> list[dict[str, Any]]:
    txn_filter = TransactionFilter(
        date_from=filters.date_from,
        date_to=filters.date_to,
        account_ids=filters.account_ids,
        category_ids=filters.category_ids,
        description_contains=filters.search,
        limit=filters.page_size,
        offset=(filters.page - 1) * filters.page_size,
        order_desc=True,
    )
    return _hydrate_txn_rows(conn, transactions_repo.list_filtered(conn, txn_filter))


def _planned_rows(conn: sqlite3.Connection, filters: LedgerFilters) -> list[dict[str, Any]]:
    pl_filter = PlannedFilter(
        date_from=filters.date_from,
        date_to=filters.date_to,
        account_ids=filters.account_ids,
        category_ids=filters.category_ids,
    )
    views = list(planned_service.list_planned(conn, pl_filter))
    return _hydrate_planned_rows(conn, views)


def _render_table(
    request: Request,
    conn: sqlite3.Connection,
    view: ViewKind,
    filters: LedgerFilters,
) -> HTMLResponse:
    if view == "actual":
        rows = _actual_rows(conn, filters)
    elif view == "planned":
        rows = _planned_rows(conn, filters)
    else:
        rows = _hydrate_recurring_rows(conn)
    return render(
        request,
        "ledger/_table.html",
        view=view,
        rows=rows,
        page=filters.page,
        page_size=filters.page_size,
        has_next=(view == "actual" and len(rows) == filters.page_size),
    )


@router.get("", response_class=HTMLResponse)
def index(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    view = coerce_view(request.query_params.get("view"))
    filters = parse_filters(request)
    if view == "actual":
        rows = _actual_rows(conn, filters)
    elif view == "planned":
        rows = _planned_rows(conn, filters)
    else:
        rows = _hydrate_recurring_rows(conn)
    return render(
        request,
        "ledger/index.html",
        view=view,
        views=view_kinds(),
        rows=rows,
        filters=filters,
        categories=categories_repo.list_all(conn),
        accounts=accounts_repo.list_all(conn),
        page=filters.page,
        page_size=filters.page_size,
        has_next=(view == "actual" and len(rows) == filters.page_size),
    )


@router.get("/table", response_class=HTMLResponse)
def table_fragment(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    view = coerce_view(request.query_params.get("view"))
    filters = parse_filters(request)
    return _render_table(request, conn, view, filters)


def render_table_for(
    request: Request,
    conn: sqlite3.Connection,
    view: ViewKind,
) -> HTMLResponse:
    """Public helper used by legacy fragment aliases (``/transactions/table``,
    ``/planned/table``) so they stay structurally identical to the new
    ``/ledger/table`` output.
    """
    filters = parse_filters(request)
    return _render_table(request, conn, view, filters)


__all__ = ["parse_filters", "render_table_for", "router"]
