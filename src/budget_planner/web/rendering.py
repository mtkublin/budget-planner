"""Template rendering helpers shared by every router.

Keeping this out of `templating.py` so filters remain pure and testable.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse


def render(
    request: Request,
    template_name: str,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    """Render a Jinja template, injecting `request` + `url_for` + settings."""
    env = request.app.state.jinja_env
    settings = request.app.state.settings
    base_ctx: dict[str, Any] = {
        "request": request,
        "settings": settings,
        "url_for": request.url_for,
    }
    base_ctx.update(context)
    html: str = env.get_template(template_name).render(**base_ctx)
    return HTMLResponse(html, status_code=status_code)


def render_str(request: Request, source: str, **context: Any) -> str:
    """Render an inline template source string (test helper mostly)."""
    env = request.app.state.jinja_env
    settings = request.app.state.settings
    base_ctx: dict[str, Any] = {
        "request": request,
        "settings": settings,
        "url_for": request.url_for,
    }
    base_ctx.update(context)
    rendered: str = env.from_string(source).render(**base_ctx)
    return rendered
