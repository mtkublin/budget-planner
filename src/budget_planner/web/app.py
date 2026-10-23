"""FastAPI application entrypoint.

Phase 0 scope: boot the app, expose `/` and `/healthz`. Routers mount in Phase 3.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from budget_planner.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    app = FastAPI(
        title="Budget Planner",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    @app.get("/", response_class=PlainTextResponse)
    def index() -> str:
        return f"Budget Planner — base_currency={cfg.base_currency} tz={cfg.display_timezone}"

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
