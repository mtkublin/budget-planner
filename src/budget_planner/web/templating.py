"""Jinja2 environment builder + shared filters/globals.

All Phase 3 routers extend the environment produced here; the goal is that
templates never need to import anything from Python other than filters
registered on `env`. See ADR-0021 (functional style) + T-030 plan.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from budget_planner.config import Settings
from budget_planner.domain.enums import Direction
from budget_planner.domain.money import (
    ISO_4217_CURRENCIES,
    currency_decimals,
    format_money,
    from_minor_units,
)
from budget_planner.web.context import fab_target_for

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _money_filter(amount_minor: int | None, currency: str) -> str:
    if amount_minor is None:
        return ""
    return format_money(int(amount_minor), currency)


def _money_major_filter(amount_minor: int | None, currency: str) -> str:
    """Render minor-units as a bare major-unit decimal (no currency suffix).

    Preserves trailing fractional zeros for the currency's precision so edit
    forms round-trip values like ``15.50`` without the dot going missing.
    """
    if amount_minor is None:
        return ""
    decimals = currency_decimals(currency)
    value = from_minor_units(int(amount_minor), currency)
    return f"{value:.{decimals}f}"


def _date_fmt_filter(value: date | datetime | str | None, pattern: str = "%Y-%m-%d") -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return value
        return parsed.strftime(pattern)
    return value.strftime(pattern)


def _dt_local_factory(tz_name: str) -> Any:
    tz = ZoneInfo(tz_name)

    def _dt_local(value: datetime | str | None, pattern: str = "%Y-%m-%d %H:%M") -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return value
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(tz).strftime(pattern)

    return _dt_local


_DIRECTION_COLORS: dict[str, str] = {
    Direction.INCOME.value: "pill-income",
    Direction.EXPENSE.value: "pill-expense",
    Direction.TRANSIT.value: "pill-transit",
    Direction.ADJUSTMENT.value: "pill-adjust",
}


def _direction_badge(direction: Direction | str | None) -> Markup:
    if direction is None:
        return Markup("")
    value = direction.value if isinstance(direction, Direction) else str(direction)
    css = _DIRECTION_COLORS.get(value, "pill-adjust")
    label = value.capitalize()
    # Values come from the Direction StrEnum or a bounded string set; label is
    # just capitalised. Safe to mark as Markup — content is derived not user.
    return Markup(  # noqa: S704
        f'<span class="pill {css}" aria-label="{label}">{label}</span>'
    )


def _csrf_token() -> str:
    # v1 single-user, no auth (ADR-0005). Keep the attr shape stable.
    return ""


def _today_local_factory(tz_name: str) -> Any:
    """Return today's date in `display_timezone` as ISO string (ADR-0030 §1)."""
    tz = ZoneInfo(tz_name)

    def _today_local() -> str:
        return datetime.now(tz).date().isoformat()

    return _today_local


def build_jinja_env(settings: Settings) -> Environment:
    """Return a fully-configured Jinja environment for the web layer."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "jinja2"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        enable_async=False,
    )
    env.filters["money"] = _money_filter
    env.filters["money_major"] = _money_major_filter
    env.filters["date_fmt"] = _date_fmt_filter
    env.filters["dt_local"] = _dt_local_factory(settings.display_timezone)
    env.filters["direction_badge"] = _direction_badge
    env.globals["direction_badge"] = _direction_badge
    env.globals["base_ccy"] = settings.base_currency
    env.globals["csrf_token"] = _csrf_token
    env.globals["Direction"] = Direction
    # T-069 — per-request FAB routing without threading state through routers.
    env.globals["fab_target_for"] = fab_target_for
    # T-110 / ADR-0030 — shared primitives: default-date-today + ISO 4217 list.
    env.globals["today_local"] = _today_local_factory(settings.display_timezone)
    env.globals["iso_4217_currencies"] = ISO_4217_CURRENCIES
    return env
