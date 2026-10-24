"""Recurring rules router (T-035)."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.money import to_minor_units
from budget_planner.domain.recurring import (
    NewRecurringOverride,
    NewRecurringRule,
    PatchRecurringRule,
)
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    recurring as recurring_repo,
)
from budget_planner.web.deps import get_db
from budget_planner.web.htmx import trigger
from budget_planner.web.rendering import render

router = APIRouter(prefix="/recurring", tags=["recurring"])


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


@router.get("", response_class=HTMLResponse)
def index(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    rules = recurring_repo.list_rules(conn)
    overrides = {r.id: recurring_repo.list_overrides(conn, r.id) for r in rules}
    return render(
        request,
        "recurring/index.html",
        rules=rules,
        overrides=overrides,
        categories=categories_repo.list_all(conn),
        accounts=accounts_repo.list_all(conn),
    )


@router.get("/new", response_class=HTMLResponse)
def new_form(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    return render(
        request,
        "partials/recurring/_form.html",
        rule=None,
        action="/recurring",
        categories=categories_repo.list_all(conn),
        accounts=accounts_repo.list_all(conn),
        errors={},
    )


def _validate_cadence(value: str) -> Cadence | None:
    try:
        return Cadence(value)
    except ValueError:
        return None


@router.post("")
def create_rule(  # noqa: PLR0917
    request: Request,
    cadence: str = Form(...),
    start_date: str = Form(...),
    category_id: int = Form(...),
    account_id: int = Form(...),
    default_amount: str = Form(...),
    default_description: str = Form(""),
    day_of_month: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    errors: dict[str, str] = {}
    c = _validate_cadence(cadence)
    if c is None:
        errors["cadence"] = "invalid cadence"
    start = _parse_date(start_date)
    if start is None:
        errors["start_date"] = "invalid date"
    acc = accounts_repo.find_by_id(conn, account_id)
    cat = categories_repo.find_by_id(conn, category_id)
    if acc is None:
        errors["account_id"] = "unknown account"
    if cat is None:
        errors["category_id"] = "unknown category"
    minor: int | None = None
    if acc is not None:
        try:
            dec = Decimal(default_amount)
        except InvalidOperation:
            errors["default_amount"] = "invalid amount"
        else:
            if dec <= 0:
                errors["default_amount"] = "must be positive"
            else:
                minor = to_minor_units(dec, acc.currency)
    if errors:
        return render(
            request,
            "partials/recurring/_form.html",
            rule=None,
            action="/recurring",
            categories=categories_repo.list_all(conn),
            accounts=accounts_repo.list_all(conn),
            errors=errors,
            status_code=422,
        )
    assert c is not None and start is not None and minor is not None
    rule = recurring_repo.create_rule(
        conn,
        NewRecurringRule(
            cadence=c,
            start_date=start,
            category_id=category_id,
            account_id=account_id,
            default_amount=minor,
            default_description=default_description,
            day_of_month=_parse_int(day_of_month),
        ),
    )
    html = render(
        request,
        "partials/recurring/_row.html",
        rule=rule,
        overrides=[],
        account=acc,
        category=cat,
    )
    trigger(html, "forecast-stale")
    return html


@router.get("/{rule_id}/edit", response_class=HTMLResponse)
def edit_form(
    rule_id: int, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return render(
            request,
            "partials/recurring/_form.html",
            rule=None,
            action="",
            categories=[],
            accounts=[],
            errors={"rule": "not found"},
            status_code=404,
        )
    return render(
        request,
        "partials/recurring/_form.html",
        rule=rule,
        action=f"/recurring/{rule_id}",
        categories=categories_repo.list_all(conn),
        accounts=accounts_repo.list_all(conn),
        errors={},
    )


@router.post("/{rule_id}")
def update_rule_handler(  # noqa: PLR0917
    rule_id: int,
    request: Request,
    cadence: str = Form(...),
    start_date: str = Form(...),
    category_id: int = Form(...),
    account_id: int = Form(...),
    default_amount: str = Form(...),
    default_description: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return Response(status_code=404, content="not found")
    acc = accounts_repo.find_by_id(conn, account_id)
    c = _validate_cadence(cadence)
    start = _parse_date(start_date)
    errors: dict[str, str] = {}
    if c is None:
        errors["cadence"] = "invalid"
    if start is None:
        errors["start_date"] = "invalid date"
    if acc is None:
        errors["account_id"] = "unknown account"
    minor: int | None = None
    if acc is not None:
        try:
            dec = Decimal(default_amount)
        except InvalidOperation:
            errors["default_amount"] = "invalid amount"
        else:
            if dec <= 0:
                errors["default_amount"] = "must be positive"
            else:
                minor = to_minor_units(dec, acc.currency)
    if errors:
        return render(
            request,
            "partials/recurring/_form.html",
            rule=rule,
            action=f"/recurring/{rule_id}",
            categories=categories_repo.list_all(conn),
            accounts=accounts_repo.list_all(conn),
            errors=errors,
            status_code=422,
        )
    assert c is not None and start is not None and minor is not None
    recurring_repo.update_rule(
        conn,
        rule_id,
        PatchRecurringRule(
            cadence=c,
            start_date=start,
            category_id=category_id,
            account_id=account_id,
            default_amount=minor,
            default_description=default_description,
        ),
    )
    updated = recurring_repo.find_rule(conn, rule_id)
    assert updated is not None and acc is not None
    cat = categories_repo.find_by_id(conn, updated.category_id)
    html = render(
        request,
        "partials/recurring/_row.html",
        rule=updated,
        overrides=recurring_repo.list_overrides(conn, rule_id),
        account=acc,
        category=cat,
    )
    trigger(html, "forecast-stale")
    return html


@router.post("/{rule_id}/deactivate")
def deactivate_rule(
    rule_id: int, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return Response(status_code=404, content="not found")
    recurring_repo.deactivate_rule(conn, rule_id)
    updated = recurring_repo.find_rule(conn, rule_id)
    assert updated is not None
    acc = accounts_repo.find_by_id(conn, updated.account_id, include_deleted=True)
    cat = categories_repo.find_by_id(conn, updated.category_id, include_deleted=True)
    html = render(
        request,
        "partials/recurring/_row.html",
        rule=updated,
        overrides=recurring_repo.list_overrides(conn, rule_id),
        account=acc,
        category=cat,
    )
    trigger(html, "forecast-stale")
    return html


@router.post("/{rule_id}/overrides")
def add_override(  # noqa: PLR0917
    rule_id: int,
    request: Request,
    occurrence_date: str = Form(...),
    state: str = Form(...),
    amount_override: str = Form(""),
    description_override: str = Form(""),
    date_override: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return Response(status_code=404, content="not found")
    occ = _parse_date(occurrence_date)
    try:
        st = OverrideState(state)
    except ValueError:
        return Response(status_code=422, content="invalid state")
    if occ is None:
        return Response(status_code=422, content="invalid occurrence_date")
    amount_minor: int | None = None
    if amount_override:
        acc = accounts_repo.find_by_id(conn, rule.account_id, include_deleted=True)
        if acc is not None:
            try:
                dec = Decimal(amount_override)
                amount_minor = to_minor_units(dec, acc.currency)
            except InvalidOperation:
                return Response(status_code=422, content="invalid amount")
    recurring_repo.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_id,
            occurrence_date=occ,
            state=st,
            amount_override=amount_minor,
            description_override=description_override or None,
            date_override=_parse_date(date_override),
        ),
    )
    overrides = recurring_repo.list_overrides(conn, rule_id)
    acc = accounts_repo.find_by_id(conn, rule.account_id, include_deleted=True)
    cat = categories_repo.find_by_id(conn, rule.category_id, include_deleted=True)
    html = render(
        request,
        "partials/recurring/_row.html",
        rule=rule,
        overrides=overrides,
        account=acc,
        category=cat,
    )
    trigger(html, "forecast-stale")
    return html


@router.post("/{rule_id}/overrides/{occurrence_date}/delete")
def delete_override(
    rule_id: int,
    occurrence_date: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return Response(status_code=404, content="not found")
    occ = _parse_date(occurrence_date)
    if occ is None:
        return Response(status_code=422, content="invalid date")
    recurring_repo.delete_override(conn, rule_id, occ)
    overrides = recurring_repo.list_overrides(conn, rule_id)
    acc = accounts_repo.find_by_id(conn, rule.account_id, include_deleted=True)
    cat = categories_repo.find_by_id(conn, rule.category_id, include_deleted=True)
    html = render(
        request,
        "partials/recurring/_row.html",
        rule=rule,
        overrides=overrides,
        account=acc,
        category=cat,
    )
    trigger(html, "forecast-stale")
    return html
