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
        if v in {"0.0.0.0", "::", "::0"}:  # noqa: S104 — reject, not emit  # nosec B104
            raise ValueError("host must be a loopback address in v1 (see ADR-0005)")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""
    return Settings()
