"""Categories router (T-033)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from budget_planner.domain.categories import NewCategory, PatchCategory
from budget_planner.domain.enums import Direction
from budget_planner.repositories import categories as categories_repo
from budget_planner.web.deps import get_db
from budget_planner.web.htmx import trigger
from budget_planner.web.rendering import render

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_class=HTMLResponse)
def index(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> HTMLResponse:
    cats = categories_repo.list_all(conn)
    return render(request, "categories/index.html", categories=cats)


@router.get("/new", response_class=HTMLResponse)
def new_form(request: Request) -> HTMLResponse:
    return render(
        request,
        "partials/categories/_form.html",
        category=None,
        action="/categories",
        errors={},
    )


def _validate_direction(value: str) -> Direction | None:
    try:
        return Direction(value)
    except ValueError:
        return None


@router.post("")
def create_category(
    request: Request,
    name: str = Form(...),
    direction: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    errors: dict[str, str] = {}
    d = _validate_direction(direction)
    if d is None:
        errors["direction"] = "invalid direction"
    if not name.strip():
        errors["name"] = "name required"
    if errors:
        return render(
            request,
            "partials/categories/_form.html",
            category=None,
            action="/categories",
            errors=errors,
            status_code=422,
        )
    assert d is not None
    cat = categories_repo.create(conn, NewCategory(name=name.strip(), direction=d))
    html = render(request, "partials/categories/_row.html", category=cat)
    trigger(html, "budget-stale")
    return html


@router.get("/{category_id}/edit", response_class=HTMLResponse)
def edit_form(
    category_id: int, request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> HTMLResponse:
    cat = categories_repo.find_by_id(conn, category_id)
    if cat is None:
        return render(
            request,
            "partials/categories/_form.html",
            category=None,
            action="",
            errors={"category": "not found"},
            status_code=404,
        )
    return render(
        request,
        "partials/categories/_form.html",
        category=cat,
        action=f"/categories/{category_id}",
        errors={},
    )


@router.post("/{category_id}")
def update_category(
    category_id: int,
    request: Request,
    name: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    cat = categories_repo.find_by_id(conn, category_id)
    if cat is None:
        return render(
            request,
            "partials/categories/_form.html",
            category=None,
            action="",
            errors={"category": "not found"},
            status_code=404,
        )
    if not name.strip():
        return render(
            request,
            "partials/categories/_form.html",
            category=cat,
            action=f"/categories/{category_id}",
            errors={"name": "name required"},
            status_code=422,
        )
    categories_repo.update(conn, category_id, PatchCategory(name=name.strip()))
    updated = categories_repo.find_by_id(conn, category_id)
    assert updated is not None
    html = render(request, "partials/categories/_row.html", category=updated)
    trigger(html, "budget-stale")
    return html


@router.post("/{category_id}/delete")
def delete_category(category_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    cat = categories_repo.find_by_id(conn, category_id)
    if cat is None:
        return Response(status_code=404, content="not found")
    if cat.is_system:
        return Response(status_code=409, content="system categories cannot be deleted")
    categories_repo.soft_delete(conn, category_id)
    resp = Response(content="", media_type="text/html")
    trigger(resp, "budget-stale")
    return resp
