# T-004 — Config Module

> Phase 0 — Repository Bootstrap. Status: pending.

## Purpose

Replace the placeholder `src/budget_planner/config.py` with a typed, immutable settings object driven by `pydantic-settings` and `.env`. Expose a single `get_settings()` entry point so every subsequent module imports its configuration from one place: database URL, base currency, display timezone, bind host/port, FX API URL. Add a minimal `web/app.py` so `just dev` returns 200 OK on `/` — this is the Phase 0 "lands on an empty FastAPI page" exit criterion from `docs/implementation_plan.md`.

## Inputs / prerequisites

- Upstream tasks:
  - [T-001 — Repository scaffolding](T-001-repository-scaffolding.md) — package tree + empty `config.py` + empty `.env.example`.
  - [T-002 — Justfile + CI](T-002-justfile-and-ci.md) — `just dev` references `budget_planner.web.app:app`.
  - [T-003 — Pre-commit stack](T-003-precommit-stack.md) — strict ruff/mypy enforce typing + style on this module.
- ADRs that constrain the choices:
  - [`ADR-0005` — Single user, no auth, bind 127.0.0.1](../../adr/0005-single-user-no-auth-user-id-scaffold.md)
  - [`ADR-0006` — Multi-currency, base currency in config](../../adr/0006-multi-currency-model.md)
  - [`ADR-0007` — Timezone handling, display tz configurable](../../adr/0007-timezone-handling.md)
  - [`ADR-0003` — SQLite only in v1](../../adr/0003-database-sqlite-only-v1.md)
  - [`ADR-0021` — Functional style, no gratuitous OOP](../../adr/0021-functional-style-no-oop.md) (constrains API shape — plain `@lru_cache`'d function, not a class)
- Required local tools:
  - `uv >= 0.4`.
  - Everything synced via `just install` (Pydantic v2, pydantic-settings, FastAPI already pinned in T-001).

> Note on tasks.md: the T-004 line in `docs/tasks.md` cites no ADRs. The decisions that constrain this task are ADR-0005, ADR-0006, ADR-0007 (and transitively ADR-0003). Reference them in the commit and/or `docs/CHANGELOG.md`.

## Deliverables

- `src/budget_planner/config.py` — settings model + `get_settings()`.
- `src/budget_planner/web/app.py` — minimal FastAPI app wired to settings; exposes `GET /` returning a trivial response, `GET /healthz` returning `{"status": "ok"}`.
- `.env.example` — commented template with every supported variable.
- `tests/unit/test_config.py` — unit tests for defaults, env overrides, validation errors.

## Step-by-step

1. Replace `src/budget_planner/config.py` with:

   ```python
   """Application configuration — single source of truth.

   All settings are loaded from environment variables / `.env` on first access.
   Values are frozen; mutations raise `pydantic.ValidationError`.
   Access via `get_settings()`; the result is cached process-wide.
   """
   from __future__ import annotations

   from functools import lru_cache
   from pathlib import Path
   from typing import Final
   from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

   from pydantic import Field, field_validator
   from pydantic_settings import BaseSettings, SettingsConfigDict

   # Default dev DB lives under `data/` (gitignored). CI/tests override via env.
   _DEFAULT_SQLITE_PATH: Final = Path("data") / "budget.sqlite"
   _DEFAULT_DATABASE_URL: Final = f"sqlite:///{_DEFAULT_SQLITE_PATH.as_posix()}"


   class Settings(BaseSettings):
       """Immutable, env-driven settings."""

       model_config = SettingsConfigDict(
           env_file=".env",
           env_file_encoding="utf-8",
           env_prefix="BUDGET_",
           frozen=True,
           extra="forbid",
       )

       database_url: str = Field(default=_DEFAULT_DATABASE_URL)
       base_currency: str = Field(default="PLN", min_length=3, max_length=3)
       display_timezone: str = Field(default="Europe/Warsaw")
       host: str = Field(default="127.0.0.1")
       port: int = Field(default=8000, ge=1, le=65535)
       fx_api_url: str = Field(default="https://api.frankfurter.app")

       @field_validator("base_currency")
       @classmethod
       def _upper_ccy(cls, v: str) -> str:
           v_upper = v.upper()
           if not v_upper.isalpha():
               raise ValueError("base_currency must be a 3-letter ISO 4217 code")
           return v_upper

       @field_validator("display_timezone")
       @classmethod
       def _validate_tz(cls, v: str) -> str:
           try:
               ZoneInfo(v)
           except ZoneInfoNotFoundError as exc:
               raise ValueError(f"unknown timezone: {v!r}") from exc
           return v

       @field_validator("host")
       @classmethod
       def _reject_public_bind(cls, v: str) -> str:
           # ADR-0005: v1 must bind locally only.
           if v in {"0.0.0.0", "::", "::0"}:  # noqa: S104 — reject, not emit
               raise ValueError(
                   "host must be a loopback address in v1 (see ADR-0005)"
               )
           return v


   @lru_cache(maxsize=1)
   def get_settings() -> Settings:
       """Return the process-wide settings instance (cached)."""
       return Settings()
   ```

   Notes:
   - `frozen=True` + `extra="forbid"` enforce immutability and reject typos.
   - `env_prefix="BUDGET_"` namespaces every env var (`BUDGET_DATABASE_URL`, `BUDGET_BASE_CURRENCY`, …). Avoids collisions with system env.
   - The `_reject_public_bind` validator enforces ADR-0005. Loopback-only bind is a safety property, not a style preference — codify it.
   - `@lru_cache(maxsize=1)` gives a cheap, test-friendly singleton. Tests call `get_settings.cache_clear()` between env mutations.

2. Replace `src/budget_planner/web/app.py` with a minimal app:

   ```python
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
           return (
               f"Budget Planner — base_currency={cfg.base_currency} "
               f"tz={cfg.display_timezone}"
           )

       @app.get("/healthz")
       def healthz() -> dict[str, str]:
           return {"status": "ok"}

       return app


   app = create_app()
   ```

   This is deliberately bare. Phase 3 (T-030) replaces `index` with a Jinja-rendered dashboard and mounts routers. Keep `create_app` factory shape — it is what tests will use via `TestClient(create_app(settings=...))`.

3. Populate `.env.example`:

   ```dotenv
   # Budget Planner — environment configuration.
   # Copy to .env for local overrides. Never commit .env.

   # SQLite URL (default: sqlite:///data/budget.sqlite).
   # Use "sqlite:///:memory:" in tests only.
   # BUDGET_DATABASE_URL=sqlite:///data/budget.sqlite

   # Base currency for aggregates (ISO 4217, uppercase). Default PLN. See ADR-0006.
   # BUDGET_BASE_CURRENCY=PLN

   # Display timezone for rendering UTC timestamps. See ADR-0007.
   # BUDGET_DISPLAY_TIMEZONE=Europe/Warsaw

   # Local bind. v1 forbids public bind (0.0.0.0). See ADR-0005.
   # BUDGET_HOST=127.0.0.1
   # BUDGET_PORT=8000

   # FX rate source. See ADR-0006.
   # BUDGET_FX_API_URL=https://api.frankfurter.app
   ```

4. Add `tests/unit/test_config.py`:

   ```python
   from __future__ import annotations

   import pytest

   from budget_planner.config import Settings, get_settings


   @pytest.fixture(autouse=True)
   def _clear_cache() -> None:
       get_settings.cache_clear()


   def test_defaults_match_requirements() -> None:
       s = Settings(_env_file=None)
       assert s.base_currency == "PLN"
       assert s.display_timezone == "Europe/Warsaw"
       assert s.host == "127.0.0.1"
       assert s.port == 8000
       assert s.fx_api_url.startswith("https://")


   def test_env_prefix_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
       monkeypatch.setenv("BUDGET_BASE_CURRENCY", "eur")
       monkeypatch.setenv("BUDGET_DISPLAY_TIMEZONE", "UTC")
       s = Settings(_env_file=None)
       assert s.base_currency == "EUR"
       assert s.display_timezone == "UTC"


   def test_rejects_public_bind(monkeypatch: pytest.MonkeyPatch) -> None:
       monkeypatch.setenv("BUDGET_HOST", "0.0.0.0")
       with pytest.raises(ValueError, match="loopback"):
           Settings(_env_file=None)


   def test_rejects_bad_currency(monkeypatch: pytest.MonkeyPatch) -> None:
       monkeypatch.setenv("BUDGET_BASE_CURRENCY", "US1")
       with pytest.raises(ValueError, match="ISO 4217"):
           Settings(_env_file=None)


   def test_rejects_unknown_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
       monkeypatch.setenv("BUDGET_DISPLAY_TIMEZONE", "Mars/Olympus")
       with pytest.raises(ValueError, match="unknown timezone"):
           Settings(_env_file=None)


   def test_get_settings_is_cached() -> None:
       assert get_settings() is get_settings()
   ```

5. Smoke-check the server:

   ```sh
   just dev &            # pid captured by shell
   curl -sf http://127.0.0.1:8000/healthz
   curl -sf http://127.0.0.1:8000/
   kill %1
   ```

   Expected: both 200 OK; `/` echoes `base_currency=PLN tz=Europe/Warsaw`.

6. Run the full gate:

   ```sh
   uv run pre-commit run --all-files
   just ci
   ```

   `just ci` should now be green: config module covered, trivial app covered via tests (add a small `TestClient` test if coverage flags `app.py` — see "Risks" below).

7. Commit:

   ```sh
   git add src/budget_planner/config.py \
           src/budget_planner/web/app.py \
           .env.example \
           tests/unit/test_config.py
   git commit -m "feat(T-004): typed config module and minimal FastAPI boot"
   ```

## Interfaces / contracts

Public surface downstream tasks depend on:

- `budget_planner.config.Settings` — frozen Pydantic settings model.
- `budget_planner.config.get_settings() -> Settings` — process-wide cached accessor.
- `budget_planner.web.app.create_app(settings: Settings | None = None) -> FastAPI` — app factory for tests.
- `budget_planner.web.app.app` — module-level app instance for `uvicorn`.

Env var contract (all optional, defaults shown):

| Env var | Default | Notes |
|---------|---------|-------|
| `BUDGET_DATABASE_URL` | `sqlite:///data/budget.sqlite` | SQLite URL. |
| `BUDGET_BASE_CURRENCY` | `PLN` | ISO 4217, 3 upper letters. |
| `BUDGET_DISPLAY_TIMEZONE` | `Europe/Warsaw` | Must be valid `zoneinfo` name. |
| `BUDGET_HOST` | `127.0.0.1` | Loopback only (ADR-0005). |
| `BUDGET_PORT` | `8000` | 1..65535. |
| `BUDGET_FX_API_URL` | `https://api.frankfurter.app` | FX source. |

Env file resolution: Pydantic Settings reads `.env` from CWD by default — matches `just` + `uvicorn` run shape.

## Validation / acceptance

Commands that must pass:

- `uv run pytest tests/unit/test_config.py -q` — exit code 0, 6 tests passing.
- `uv run pre-commit run --all-files` — exit code 0.
- `just dev` boots and `curl -sf http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`.
- `curl -sf http://127.0.0.1:8000/` returns a 200 OK body containing `base_currency=PLN`.
- `just ci` passes locally.
- Phase 0 exit criteria satisfied:
  - `just --list` self-documents all recipes (T-002).
  - Pre-commit active on every commit (T-003).
  - CI runs `just ci` on push and passes with the empty project (ends here).

Docs updates (CLAUDE.md handoff checklist):

- Prefix the T-004 line in `docs/tasks.md` with `✅`.
- Append a dated line to `docs/CHANGELOG.md` referencing T-004 and the env var contract.
- Reference ADR-0005, ADR-0006, ADR-0007 in the commit body. No new ADR required.

## Risks & gotchas

- `pydantic-settings` v2 passes `_env_file=None` to **disable** `.env` loading in tests. Use that in `test_config.py` to avoid picking up a dev `.env`.
- `@lru_cache` can leak state across tests. The autouse fixture `_clear_cache` calls `get_settings.cache_clear()` — mandatory pattern for any future test touching settings.
- Default DB path is `data/budget.sqlite` but `data/` is gitignored and will not exist on first run. Phase 1 (T-010) creates the directory in the migration runner. Phase 0 does not actually open the DB.
- `extra="forbid"` means a typo like `BUDGET_BASE_CURENCY=EUR` raises on startup. Good signal — do not relax.
- `frozen=True` on Pydantic v2 settings is honoured; attempts to assign (`get_settings().port = 9000`) raise `ValidationError`. Document in `docs/CHANGELOG.md`.
- FastAPI's `TestClient` depends on `httpx`. Already pinned in T-001 — no action needed, but a web-layer smoke test (e.g. `assert TestClient(app).get("/healthz").status_code == 200`) is cheap coverage insurance if the coverage gate flags `app.py`.
- The `/` endpoint in Phase 0 is text-only; `djlint` is not run here (no templates). Phase 3 replaces this with a Jinja view.
- `host` validator blocks only canonical "all interfaces" strings. Explicit loopback aliases like `localhost`, `127.0.0.1`, `::1` pass. Documented in the model.
- Keep the module **functional**: no `Settings` subclassing, no DI container, no `Depends(get_settings)` wiring (that is a Phase 3 concern once routers need it).

## Handoff notes

- Phase 1 (T-010) consumes `Settings.database_url` for connection setup and creates `data/` if missing.
- Phase 2 (T-020) consumes `Settings.fx_api_url` for the frankfurter client.
- Phase 3 (T-030) wires `Depends(get_settings)` where needed and renders templates for `/`.
- When `just ci` is green after this task, the Phase 0 gate is complete and Phase 1 can start.
