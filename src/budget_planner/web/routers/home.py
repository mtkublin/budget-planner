"""Home router (T-039 / T-063).

Three-panel Overview: Accounts, This month, Upcoming planned.
See ADR-0023 and docs/plans/v1/phase-6/T-063-overview-composition.md.

Services only — no business logic. FX conversion for the fortune hero
batches rates per non-base currency to keep remote calls bounded.
"""

from __future__ import annotations

import calendar
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final, Literal

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from budget_planner.config import Settings
from budget_planner.domain.money import currency_decimals
from budget_planner.domain.planned import PlannedFilter
from budget_planner.repositories import accounts as accounts_repo
from budget_planner.services import (
    balance as balance_service,
    budget as budget_service,
    fortune as fortune_service,
    fx as fx_service,
    planned as planned_service,
)
from budget_planner.web.deps import get_db, get_settings_dep
from budget_planner.web.rendering import render

router = APIRouter(tags=["home"])

PaceKind = Literal["on_track", "pacing_high", "over_budget"]

_PACE_LABELS: Final[dict[str, str]] = {
    "on_track": "on track",
    "pacing_high": "pacing high",
    "over_budget": "over budget",
}

_WINDOWS: Final[dict[str, int | None]] = {"7": 7, "30": 30, "all": None}
_DEFAULT_WINDOW: Final[str] = "30"
_UPCOMING_LOOKBACK_DAYS: Final[int] = 30  # how far back overdue rows surface


@dataclass(frozen=True, slots=True)
class AccountRow:
    """Per-account row for Panel A."""

    id: int
    name: str
    type: str | None
    currency: str
    balance_minor: int
    balance_base_minor: int


@dataclass(frozen=True, slots=True)
class CurrencyTotal:
    """Per-currency total for Panel A sub-header."""

    currency: str
    total_minor: int


@dataclass(frozen=True, slots=True)
class PaceTag:
    """Pace signal for Panel B — label + semantic kind."""

    kind: PaceKind
    label: str


@dataclass(frozen=True, slots=True)
class UpcomingRow:
    """Normalised row for Panel C."""

    operation_date: date
    description: str
    amount_minor: int
    is_overdue: bool


def _convert_minor(
    amount_minor: int,
    from_ccy: str,
    to_ccy: str,
    rate: Decimal,
) -> int:
    """Convert ``amount_minor`` using a pre-fetched rate (ROUND_HALF_EVEN)."""
    if from_ccy == to_ccy:
        return amount_minor
    src_scale = Decimal(10) ** currency_decimals(from_ccy)
    dst_scale = Decimal(10) ** currency_decimals(to_ccy)
    major = Decimal(amount_minor) / src_scale
    converted = (major * rate) * dst_scale
    return int(converted.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _collect_account_rows(
    conn: sqlite3.Connection,
    base_ccy: str,
) -> tuple[tuple[AccountRow, ...], tuple[CurrencyTotal, ...], int]:
    """Return (per-account rows, per-currency totals, fortune in base)."""
    accs = accounts_repo.list_all(conn)
    per_ccy: dict[str, int] = {}
    native: list[tuple[int, str, str | None, str, int]] = []
    for a in accs:
        bal = balance_service.derive_balance(conn, a.id)
        per_ccy[a.currency] = per_ccy.get(a.currency, 0) + bal
        native.append((a.id, a.name, a.type, a.currency, bal))

    non_base = {ccy for ccy in per_ccy if ccy != base_ccy}
    rates: dict[str, Decimal] = {base_ccy: Decimal("1")}
    if non_base:
        today = date.today()  # noqa: DTZ011 — ADR-0007: naive dates
        with httpx.Client(timeout=5.0) as http:
            for ccy in non_base:
                try:
                    rates[ccy] = fx_service.get_rate(conn, http, today, ccy, base_ccy)
                except fx_service.FxUnavailableError:
                    rates[ccy] = Decimal("1")  # degrade gracefully; UI shows native only

    rows = tuple(
        AccountRow(
            id=aid,
            name=name,
            type=atype,
            currency=ccy,
            balance_minor=bal,
            balance_base_minor=_convert_minor(bal, ccy, base_ccy, rates[ccy]),
        )
        for (aid, name, atype, ccy, bal) in native
    )
    totals = tuple(
        CurrencyTotal(currency=ccy, total_minor=total) for ccy, total in sorted(per_ccy.items())
    )
    fortune_base = sum(r.balance_base_minor for r in rows)
    return rows, totals, fortune_base


def _pace_tag(spent: int, budgeted: int, today: date, year: int, month: int) -> PaceTag:
    """Compute pace signal from totals + elapsed fraction of the month."""
    if budgeted <= 0:
        return PaceTag(kind="on_track", label=_PACE_LABELS["on_track"])
    if spent > budgeted:
        return PaceTag(kind="over_budget", label=_PACE_LABELS["over_budget"])
    days_in_month = calendar.monthrange(year, month)[1]
    elapsed = today.day if (today.year == year and today.month == month) else days_in_month
    expected = budgeted * elapsed // days_in_month
    if spent > expected:
        return PaceTag(kind="pacing_high", label=_PACE_LABELS["pacing_high"])
    return PaceTag(kind="on_track", label=_PACE_LABELS["on_track"])


def _days_left_in_month(today: date, year: int, month: int) -> int:
    """Days remaining in ``(year, month)`` relative to ``today`` (inclusive)."""
    if today.year != year or today.month != month:
        return 0
    last_day = calendar.monthrange(year, month)[1]
    return max(0, last_day - today.day)


def _window_from(request: Request) -> tuple[str, int | None]:
    """Parse ``?window=`` → (label, days). Falls back to the default."""
    raw = request.query_params.get("window", _DEFAULT_WINDOW)
    if raw not in _WINDOWS:
        raw = _DEFAULT_WINDOW
    return raw, _WINDOWS[raw]


def _list_upcoming(
    conn: sqlite3.Connection,
    today: date,
    window_days: int | None,
) -> tuple[UpcomingRow, ...]:
    """Return un-promoted planned rows for Panel C."""
    date_from = today - timedelta(days=_UPCOMING_LOOKBACK_DAYS)
    date_to = today + timedelta(days=window_days) if window_days is not None else None
    views = planned_service.list_planned(
        conn,
        PlannedFilter(date_from=date_from, date_to=date_to, promoted=False),
    )
    return tuple(
        UpcomingRow(
            operation_date=v.operation_date,
            description=v.description,
            amount_minor=v.amount_minor,
            is_overdue=v.operation_date < today,
        )
        for v in views
    )


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> HTMLResponse:
    today = date.today()  # noqa: DTZ011 — ADR-0007: naive dates
    year, month = today.year, today.month
    base_ccy = settings.base_currency

    account_rows, totals_by_ccy, fortune_base = _collect_account_rows(conn, base_ccy)
    fortune = fortune_service.compute_fortune(conn, settings)
    summary = budget_service.month_summary(conn, year, month)
    pace = _pace_tag(summary.totals.spent_minor, summary.totals.budgeted_minor, today, year, month)
    days_left = _days_left_in_month(today, year, month)
    bar_pct = 0
    if summary.totals.budgeted_minor > 0:
        ratio = 100 * summary.totals.spent_minor / summary.totals.budgeted_minor
        bar_pct = max(0, min(100, int(ratio)))

    window_label, window_days = _window_from(request)
    upcoming = _list_upcoming(conn, today, window_days)

    return render(
        request,
        "home/index.html",
        today=today,
        year=year,
        month=month,
        base_ccy=base_ccy,
        fortune_base=fortune_base,
        fortune=fortune,
        account_rows=account_rows,
        totals_by_ccy=totals_by_ccy,
        summary=summary,
        pace=pace,
        days_left=days_left,
        bar_pct=bar_pct,
        upcoming=upcoming,
        window_label=window_label,
    )


@router.get("/overview/upcoming", response_class=HTMLResponse)
def upcoming_fragment(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    """HTMX fragment for Panel C — swapped on window change or live events.

    T-093: returns the list body plus an out-of-band swap of the segmented
    range so active state stays in sync with ``window_label`` without any
    new client JS.
    """
    today = date.today()  # noqa: DTZ011
    window_label, window_days = _window_from(request)
    upcoming = _list_upcoming(conn, today, window_days)
    return render(
        request,
        "home/_upcoming_fragment.html",
        upcoming=upcoming,
        today=today,
        window_label=window_label,
    )
