"""Recurring rules router (T-035)."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from budget_planner.domain.enums import Cadence, OverrideState
from budget_planner.domain.money import to_minor_units
from budget_planner.domain.recurring import (
    NewRecurringOverride,
    NewRecurringRule,
    PatchRecurringRule,
    RecurringOverride,
)
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    recurring as recurring_repo,
)
from budget_planner.services import recurring as recurring_svc
from budget_planner.services._promotion import UnsupportedDirectionError, ValidationError
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


@router.get("")
def index() -> RedirectResponse:
    """Legacy page URL (T-070).

    Redirects to the unified ledger with the ``recurring`` view selected. The
    CRUD sub-routes (``/recurring/new``, ``/recurring/{id}/edit``, etc.)
    remain live for the FAB and settings tooling.
    """
    return RedirectResponse(url="/ledger?view=recurring", status_code=302)


@router.get("/new", response_class=HTMLResponse)
def new_form(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    # T-069 — slide-over wrapper for FAB launches.
    return render(
        request,
        "partials/_slideover.html",
        slide_over_title="New recurring rule",
        form_include="partials/recurring/_form.html",
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
    trigger(html, "forecast-stale", "ledger-stale")
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
    # T-114 / ADR-0030 §4 — slide-over wrapper mirrors /recurring/new.
    return render(
        request,
        "partials/_slideover.html",
        slide_over_title="Edit recurring rule",
        form_include="partials/recurring/_form.html",
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
    trigger(html, "forecast-stale", "ledger-stale")
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
    trigger(html, "forecast-stale", "ledger-stale")
    return html


@router.get("/{rule_id}/overrides/new", response_class=HTMLResponse)
def new_override_form(
    rule_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Generic override form. Picks (year, month, amount); server resolves
    the exact ``occurrence_date`` on submit via
    ``services.recurring.occurrence_in_month``. Defaults year + month to the
    rule's current ``next_due``.
    """
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return render(
            request,
            "partials/recurring/_override_form.html",
            rule=None,
            account=None,
            default_year=None,
            default_month=None,
            default_amount_str=None,
            errors={"rule": "not found"},
            status_code=404,
        )
    account = accounts_repo.find_by_id(conn, rule.account_id, include_deleted=True)
    default_amount_str = f"{Decimal(rule.default_amount) / Decimal(100):.2f}" if account else ""
    return render(
        request,
        "partials/recurring/_override_form.html",
        rule=rule,
        account=account,
        default_year=rule.next_due.year,
        default_month=rule.next_due.month,
        default_amount_str=default_amount_str,
        errors={},
    )


@router.post("/{rule_id}/overrides")
def add_override(  # noqa: PLR0917, PLR0911
    rule_id: int,
    request: Request,
    year: int = Form(...),
    month: int = Form(...),
    amount: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return Response(status_code=404, content="not found")
    if not (1900 <= year <= 9999 and 1 <= month <= 12):  # noqa: PLR2004
        return Response(status_code=422, content="invalid year or month")
    occ = recurring_svc.occurrence_in_month(rule, year, month)
    if occ is None:
        return Response(
            status_code=422,
            content=f"rule has no occurrence in {year:04d}-{month:02d}",
        )
    acc = accounts_repo.find_by_id(conn, rule.account_id, include_deleted=True)
    if acc is None:
        return Response(status_code=422, content="rule has no live account")
    try:
        dec = Decimal(amount.replace(",", "."))
    except InvalidOperation:
        return Response(status_code=422, content="invalid amount")
    if dec <= 0:
        return Response(status_code=422, content="amount must be positive")
    amount_minor = to_minor_units(dec, acc.currency)
    recurring_repo.upsert_override(
        conn,
        NewRecurringOverride(
            rule_id=rule_id,
            occurrence_date=occ,
            state=OverrideState.OVERRIDDEN,
            amount_override=amount_minor,
            description_override=None,
            date_override=None,
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
    trigger(html, "forecast-stale", "ledger-stale")
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
    trigger(html, "forecast-stale", "ledger-stale")
    return html


# ---------------------------------------------------------------------------
# T-118 — Promote / Skip-next (ADR-0038)
# ---------------------------------------------------------------------------
def _override_on_next_due(
    conn: sqlite3.Connection,
    rule_id: int,
    next_due: date,
) -> RecurringOverride | None:
    """Return the override whose canonical ``occurrence_date == next_due``."""
    for override in recurring_repo.list_overrides(conn, rule_id):
        if override.occurrence_date == next_due:
            return override
    return None


def _render_promote_modal(
    request: Request,
    conn: sqlite3.Connection,
    rule_id: int,
    *,
    errors: dict[str, str] | None = None,
    status_code: int = 200,
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return render(
            request,
            "partials/recurring/_promote_modal.html",
            rule=None,
            account=None,
            override=None,
            prefill_date=None,
            prefill_amount_minor=None,
            prefill_description="",
            errors={"rule": "not found"},
            status_code=404,
        )
    override = _override_on_next_due(conn, rule_id, rule.next_due)
    account = accounts_repo.find_by_id(conn, rule.account_id, include_deleted=True)
    prefill_date = rule.next_due
    prefill_amount = rule.default_amount
    prefill_description = rule.default_description
    if override is not None:
        if override.date_override is not None:
            prefill_date = override.date_override
        if override.amount_override is not None:
            prefill_amount = override.amount_override
        if override.description_override is not None:
            prefill_description = override.description_override
    return render(
        request,
        "partials/recurring/_promote_modal.html",
        rule=rule,
        account=account,
        override=override,
        prefill_date=prefill_date,
        prefill_amount_minor=prefill_amount,
        prefill_description=prefill_description,
        errors=errors or {},
        status_code=status_code,
    )


@router.get("/{rule_id}/promote", response_class=HTMLResponse)
def promote_form(
    rule_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    return _render_promote_modal(request, conn, rule_id)


@router.post("/{rule_id}/promote")
def promote_submit(  # noqa: PLR0912, PLR0917
    rule_id: int,
    request: Request,
    operation_date: str = Form(""),
    amount: str = Form(""),
    description: str = Form(""),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return Response(status_code=404, content="not found")
    account = accounts_repo.find_by_id(conn, rule.account_id, include_deleted=True)
    errors: dict[str, str] = {}

    op_date: date | None = None
    if operation_date:
        op_date = _parse_date(operation_date)
        if op_date is None:
            errors["operation_date"] = "invalid date"

    amount_minor: int | None = None
    if amount:
        if account is None:
            errors["amount"] = "unknown account currency"
        else:
            try:
                dec = Decimal(amount)
            except (InvalidOperation, TypeError):
                errors["amount"] = "amount must be a decimal number"
            else:
                if dec <= 0:
                    errors["amount"] = "amount must be positive"
                else:
                    amount_minor = to_minor_units(dec, account.currency)

    if errors:
        return _render_promote_modal(request, conn, rule_id, errors=errors, status_code=422)

    edits = recurring_svc.PromotionEdits(
        operation_date=op_date,
        amount_minor=amount_minor,
        description=description or None,
    )
    try:
        recurring_svc.promote_recurring(conn, rule_id, edits)
    except recurring_svc.RecurringNotFoundError:
        return Response(status_code=404, content="not found")
    except (
        recurring_svc.InactiveRecurringError,
        recurring_svc.CannotPromoteSkippedError,
        UnsupportedDirectionError,
        ValidationError,
    ) as exc:
        return _render_promote_modal(
            request,
            conn,
            rule_id,
            errors={"promotion": str(exc)},
            status_code=422,
        )

    updated = recurring_repo.find_rule(conn, rule_id, include_deleted=True)
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
    trigger(html, "ledger-stale", "forecast-stale", "budget-stale")
    return html


@router.post("/{rule_id}/skip-next")
def skip_next(
    rule_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    rule = recurring_repo.find_rule(conn, rule_id)
    if rule is None:
        return Response(status_code=404, content="not found")
    try:
        recurring_svc.skip_and_advance(conn, rule_id)
    except recurring_svc.InactiveRecurringError:
        return Response(status_code=422, content="rule is inactive")
    updated = recurring_repo.find_rule(conn, rule_id, include_deleted=True)
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
    trigger(html, "ledger-stale", "forecast-stale", "budget-stale")
    return html
