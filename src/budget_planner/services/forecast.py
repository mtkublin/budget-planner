"""Forecast service (T-025, T-126).

Deterministic forward-looking balance projection (ADR-0015). For each day
in ``[today, today + horizon_days]`` the service applies planned-cash
events in operation-date order on top of each account's current derived
balance, then aggregates to ``base_currency`` using TODAY's FX rate held
constant across the horizon (ADR-0006).

T-126 (ADR-0042) introduces a **budget overlay**: synthetic expense cash
events for the per-category per-month residual budget not already covered
by planned transactions or recurring occurrences. The overlay is on by
default; callers may disable it via ``include_budget_overlay=False`` to
exercise the pre-overlay projection in regression tests.

Pure w.r.t. the DB snapshot + FX cache + injected clock. The caller owns
``today`` (routers compute it in the display timezone, ADR-0007) so unit
tests remain tz-independent.
"""

from __future__ import annotations

import calendar
import datetime as dt
import logging
import sqlite3
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

import httpx

from budget_planner.domain.accounts import Account
from budget_planner.domain.enums import Direction
from budget_planner.domain.money import currency_decimals
from budget_planner.domain.planned import PlannedFilter, PlannedTransaction
from budget_planner.domain.recurring import Occurrence, RecurringRule
from budget_planner.domain.transactions import TransactionFilter
from budget_planner.repositories import (
    accounts as accounts_repo,
    categories as categories_repo,
    planned as planned_repo,
    recurring as recurring_repo,
    transactions as transactions_repo,
)
from budget_planner.services import (
    budget as budget_svc,
    fx as fx_svc,
    recurring as recurring_svc,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountBalancePoint:
    """One account's projected balance on a single horizon day."""

    account_id: int
    on_date: dt.date
    native_minor: int
    base_minor: int


@dataclass(frozen=True, slots=True, kw_only=True)
class DayPoint:
    """All active accounts' projected balances on one horizon day + the base total."""

    on_date: dt.date
    totals_base_minor: int
    by_account: tuple[AccountBalancePoint, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ForecastSeries:
    """Window + per-day projections. ``len(days) == horizon_days + 1``."""

    base_currency: str
    start_date: dt.date
    end_date: dt.date
    days: tuple[DayPoint, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class MonthlyPoint:
    """Per-month forecast aggregate (ADR-0043).

    All amounts are in ``base_currency`` minor units. ``income`` /
    ``expense`` are unsigned sums over cash events landing in the month;
    transits + adjustments are excluded (transits net to zero across
    accounts; planned adjustments are unsupported — see ADR-0011).
    """

    month: dt.date
    income_base_minor: int
    expense_base_minor: int
    net_base_minor: int
    end_balance_base_minor: int


@dataclass(frozen=True, slots=True, kw_only=True)
class MonthlySeries:
    """Monthly aggregates over the forecast horizon (ADR-0043)."""

    base_currency: str
    start_month: dt.date
    end_month: dt.date
    months: tuple[MonthlyPoint, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class _CashEvent:
    """Signed per-account cash movement scheduled on a particular date."""

    on_date: dt.date
    account_id: int
    amount_minor: int


# ---------------------------------------------------------------------------
# event emission
# ---------------------------------------------------------------------------
def _signed_events_for_direction(
    direction: Direction,
    operation_date: dt.date,
    account_id: int,
    dest_account_id: int | None,
    amount_minor: int,
) -> tuple[_CashEvent, ...]:
    """Return the per-account cash events for one planned/virtual leg.

    Mirrors ``services.balance.signed_legs`` but for forward-looking events
    (operates on dates + raw ints rather than ``Transaction`` rows). Returns
    ``()`` for adjustments — planned adjustments are unsupported (ADR-0011
    + T-023 guard); surviving rows are skipped defensively with a DEBUG log.
    """
    if direction is Direction.INCOME:
        return (
            _CashEvent(
                on_date=operation_date,
                account_id=account_id,
                amount_minor=amount_minor,
            ),
        )
    if direction is Direction.EXPENSE:
        return (
            _CashEvent(on_date=operation_date, account_id=account_id, amount_minor=-amount_minor),
        )
    if direction is Direction.TRANSIT:
        if dest_account_id is None:  # pragma: no cover - schema CHECK blocks it
            raise ValueError("transit event missing dest_account_id")
        if dest_account_id == account_id:  # pragma: no cover - schema CHECK blocks it
            raise ValueError("transit source and dest must differ")
        return (
            _CashEvent(on_date=operation_date, account_id=account_id, amount_minor=-amount_minor),
            _CashEvent(
                on_date=operation_date,
                account_id=dest_account_id,
                amount_minor=amount_minor,
            ),
        )
    logger.debug(
        "forecast skipping adjustment-direction planned leg on %s acct=%s",
        operation_date,
        account_id,
    )
    return ()


def _events_from_persisted(
    row: PlannedTransaction,
    direction: Direction,
) -> tuple[_CashEvent, ...]:
    return _signed_events_for_direction(
        direction=direction,
        operation_date=row.operation_date,
        account_id=row.account_id,
        dest_account_id=row.dest_account_id,
        amount_minor=row.amount,
    )


def _events_from_occurrence(
    occ: Occurrence,
    direction: Direction,
) -> tuple[_CashEvent, ...]:
    return _signed_events_for_direction(
        direction=direction,
        operation_date=occ.effective_date,
        account_id=occ.account_id,
        dest_account_id=occ.dest_account_id,
        amount_minor=occ.amount,
    )


# ---------------------------------------------------------------------------
# FX helpers
# ---------------------------------------------------------------------------
def _collect_fx_rates(
    conn: sqlite3.Connection,
    http: httpx.Client,
    today: dt.date,
    currencies: set[str],
    base_currency: str,
) -> dict[str, Decimal]:
    """Fetch today's rate ``ccy -> base_currency`` once per distinct currency."""
    out: dict[str, Decimal] = {}
    for ccy in currencies:
        if ccy == base_currency:
            out[ccy] = Decimal("1")
            continue
        out[ccy] = fx_svc.get_rate(conn, http, today, ccy, base_currency)
    return out


def _convert_native_to_base(
    amount_native_minor: int,
    from_ccy: str,
    base_currency: str,
    fx_rates: dict[str, Decimal],
) -> int:
    """Scale ``amount_native_minor`` to ``base_currency`` minor units.

    Uses ``ROUND_HALF_EVEN`` and preserves sign. Short-circuits on identity.
    """
    if from_ccy == base_currency:
        return amount_native_minor
    rate = fx_rates[from_ccy]
    src_decimals = currency_decimals(from_ccy)
    dst_decimals = currency_decimals(base_currency)
    src_scale = Decimal(10) ** src_decimals
    dst_scale = Decimal(10) ** dst_decimals
    major = Decimal(amount_native_minor) / src_scale
    converted = (major * rate) * dst_scale
    return int(converted.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


# ---------------------------------------------------------------------------
# event collection
# ---------------------------------------------------------------------------
def _collect_events(
    conn: sqlite3.Connection,
    today: dt.date,
    end_date: dt.date,
    directions_by_cat: dict[int, Direction],
) -> dict[dt.date, list[_CashEvent]]:
    """Return per-date cash events sourced from planned rows + virtual occurrences.

    De-dup rule: when ``(recurring_rule_id, occurrence_date)`` is already
    materialised as a persisted planned row, drop the virtual expansion.
    """
    event_start = today + dt.timedelta(days=1)
    if event_start > end_date:
        return {}

    persisted = planned_repo.list_filtered(
        conn,
        PlannedFilter(date_from=event_start, date_to=end_date, promoted=False),
    )
    dedup_keys: set[tuple[int, dt.date]] = {
        (row.recurring_rule_id, row.occurrence_date)
        for row in persisted
        if row.recurring_rule_id is not None and row.occurrence_date is not None
    }

    events: dict[dt.date, list[_CashEvent]] = {}
    for row in persisted:
        direction = directions_by_cat[row.category_id]
        for ev in _events_from_persisted(row, direction):
            events.setdefault(ev.on_date, []).append(ev)

    for rule in recurring_repo.list_rules(conn, active_only=True):
        if _rule_outside_window(rule, event_start, end_date):
            continue
        overrides = recurring_repo.list_overrides(conn, rule.id)
        direction = directions_by_cat[rule.category_id]
        for occ in recurring_svc.expand(rule, overrides, event_start, end_date):
            if (rule.id, occ.occurrence_date) in dedup_keys:
                continue
            for ev in _events_from_occurrence(occ, direction):
                events.setdefault(ev.on_date, []).append(ev)

    return events


def _rule_outside_window(
    rule: RecurringRule,
    window_start: dt.date,
    window_end: dt.date,
) -> bool:
    if rule.start_date > window_end:
        return True
    return rule.end_date is not None and rule.end_date < window_start


# ---------------------------------------------------------------------------
# budget overlay (ADR-0042)
# ---------------------------------------------------------------------------
_MONTHS_IN_YEAR = 12


def _iter_months(start: dt.date, end: dt.date) -> list[tuple[int, int]]:
    """Return ``(year, month)`` tuples whose month overlaps ``[start, end]``."""
    out: list[tuple[int, int]] = []
    year, month = start.year, start.month
    end_year, end_month = end.year, end.month
    while (year, month) <= (end_year, end_month):
        out.append((year, month))
        month += 1
        if month > _MONTHS_IN_YEAR:
            month = 1
            year += 1
    return out


def _month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, 1), dt.date(year, month, last)


def _spent_so_far(
    conn: sqlite3.Connection,
    category_id: int,
    month_start: dt.date,
    cutoff: dt.date,
) -> int:
    """Return actual expense-direction amount for ``category`` in ``[month_start, cutoff]``.

    Returns 0 when ``cutoff < month_start`` (fully future month).
    """
    if cutoff < month_start:
        return 0
    rows = transactions_repo.list_filtered(
        conn,
        TransactionFilter(
            date_from=month_start,
            date_to=cutoff,
            category_ids=(category_id,),
            directions=(Direction.EXPENSE,),
        ),
    )
    return sum(r.amount for r in rows)


def _committed_future_for_category(
    conn: sqlite3.Connection,
    category_id: int,
    window_start: dt.date,
    window_end_inclusive: dt.date,
) -> int:
    """Sum unpromoted planned + active recurring expense amounts for one category.

    Window is ``[window_start, window_end_inclusive]`` (both inclusive).
    Mirrors ``services.budget.committed_in_window`` but filtered to a single
    category and inclusive on the right — matches "events on days > today
    through month_end" semantics the overlay needs.
    """
    if window_end_inclusive < window_start:
        return 0

    total = 0

    planned_rows = planned_repo.list_filtered(
        conn,
        PlannedFilter(
            date_from=window_start,
            date_to=window_end_inclusive,
            category_ids=(category_id,),
            directions=(Direction.EXPENSE,),
            promoted=False,
        ),
    )
    total += sum(r.amount for r in planned_rows)

    for rule in recurring_repo.list_rules(conn, active_only=True):
        if rule.category_id != category_id:
            continue
        rule_start = max(rule.next_due, window_start)
        if rule_start > window_end_inclusive:
            continue
        overrides = recurring_repo.list_overrides(conn, rule.id)
        for occ in recurring_svc.expand(rule, overrides, rule_start, window_end_inclusive):
            total += occ.amount

    return total


def _distribute_overlay(
    *,
    unaccounted_minor: int,
    window_start: dt.date,
    window_end_inclusive: dt.date,
    account_id: int,
) -> list[_CashEvent]:
    """Spread ``unaccounted_minor`` evenly as expense events, residual on last day.

    Per-day amount via ``ROUND_HALF_EVEN``; the final day absorbs any
    rounding delta so the window sum equals ``unaccounted_minor`` exactly.
    Zero-amount days are omitted. Caller guarantees ``unaccounted_minor > 0``
    and ``window_end_inclusive >= window_start``.
    """
    day_count = (window_end_inclusive - window_start).days + 1
    per_day_minor = int(
        (Decimal(unaccounted_minor) / Decimal(day_count)).quantize(
            Decimal("1"), rounding=ROUND_HALF_EVEN
        )
    )
    distributed_before_last = per_day_minor * (day_count - 1)
    last_day_minor = unaccounted_minor - distributed_before_last

    events: list[_CashEvent] = []
    for i in range(day_count):
        amt = last_day_minor if i == day_count - 1 else per_day_minor
        if amt == 0:
            continue
        events.append(
            _CashEvent(
                on_date=window_start + dt.timedelta(days=i),
                account_id=account_id,
                amount_minor=-amt,
            )
        )
    return events


def _collect_budget_overlay(
    conn: sqlite3.Connection,
    today: dt.date,
    end_date: dt.date,
    directions_by_cat: dict[int, Direction],
    primary_account_id: int,
) -> list[_CashEvent]:
    """Return synthetic expense events for per-category per-month unaccounted budget.

    See ADR-0042 for the formula + distribution contract. Returns ``[]``
    when the event window is empty or no budget-eligible residual exists.
    """
    event_start = today + dt.timedelta(days=1)
    if event_start > end_date:
        return []

    expense_cat_ids = [
        cat_id for cat_id, direction in directions_by_cat.items() if direction is Direction.EXPENSE
    ]
    if not expense_cat_ids:
        return []

    events: list[_CashEvent] = []
    for year, month in _iter_months(event_start, end_date):
        month_start, month_end = _month_bounds(year, month)
        window_start = max(event_start, month_start)
        window_end = min(end_date, month_end)
        if window_start > window_end:
            continue

        for cat_id in expense_cat_ids:
            budget = budget_svc.resolve_budget(conn, cat_id, year, month)
            if budget is None:
                continue

            spent = _spent_so_far(conn, cat_id, month_start, min(today, month_end))
            committed = _committed_future_for_category(conn, cat_id, window_start, month_end)
            unaccounted = budget - spent - committed
            if unaccounted <= 0:
                continue

            events.extend(
                _distribute_overlay(
                    unaccounted_minor=unaccounted,
                    window_start=window_start,
                    window_end_inclusive=window_end,
                    account_id=primary_account_id,
                )
            )

    return events


# ---------------------------------------------------------------------------
# anchor
# ---------------------------------------------------------------------------
def _anchor_balances(
    conn: sqlite3.Connection,
    today: dt.date,
    accounts: tuple[Account, ...],
) -> dict[int, int]:
    """Day-0 native balance per account via ``services.balance.derive_balance``.

    Local import avoids a cycle: ``balance`` doesn't depend on ``forecast``
    today, but keeping this module importable from routers early in startup
    costs nothing.
    """
    from budget_planner.services import balance as balance_svc  # noqa: PLC0415

    return {a.id: balance_svc.derive_balance(conn, a.id, as_of_date=today) for a in accounts}


# ---------------------------------------------------------------------------
# day construction
# ---------------------------------------------------------------------------
def _build_day(
    on_date: dt.date,
    accounts: tuple[Account, ...],
    running_native: dict[int, int],
    fx_rates: dict[str, Decimal],
    base_currency: str,
) -> DayPoint:
    points = tuple(
        AccountBalancePoint(
            account_id=a.id,
            on_date=on_date,
            native_minor=running_native[a.id],
            base_minor=_convert_native_to_base(
                running_native[a.id], a.currency, base_currency, fx_rates
            ),
        )
        for a in accounts
    )
    total = sum(p.base_minor for p in points)
    return DayPoint(on_date=on_date, totals_base_minor=total, by_account=points)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def forecast(
    conn: sqlite3.Connection,
    http: httpx.Client,
    today: dt.date,
    horizon_days: int,
    base_currency: str,
    *,
    include_budget_overlay: bool = True,
) -> ForecastSeries:
    """Project per-account balances forward ``horizon_days`` days.

    Args:
        conn: Open SQLite connection (read-only usage).
        http: Shared ``httpx.Client`` for FX fallback (only hit on cache miss).
        today: Day 0 of the series. Routers inject the date in the display
            timezone so the forecast is tz-independent and deterministic.
        horizon_days: Non-negative count of additional days to project.
        base_currency: ISO 4217 code to aggregate ``totals_base_minor`` into.
        include_budget_overlay: When ``True`` (default), inject synthetic
            expense events for the per-category per-month residual budget
            (ADR-0042). Pass ``False`` for the pre-overlay projection used
            by targeted regression tests.

    Returns:
        ``ForecastSeries`` with ``len(days) == horizon_days + 1``.

    Invariants:
        * ``days[0].by_account[i].native_minor ==
          services.balance.derive_balance(conn, account_id, as_of_date=today)``.
        * Removing (soft-delete) a planned row before the call drops the
          projected balance after its ``operation_date`` by exactly the
          signed-leg magnitude.
        * Same inputs + same DB snapshot + same FX cache state → identical output.
    """
    if horizon_days < 0:
        raise ValueError(f"horizon_days must be >= 0, got {horizon_days}")

    end_date = today + dt.timedelta(days=horizon_days)
    active_accounts = tuple(accounts_repo.list_all(conn))
    if not active_accounts:
        return ForecastSeries(
            base_currency=base_currency,
            start_date=today,
            end_date=end_date,
            days=tuple(
                DayPoint(on_date=today + dt.timedelta(days=i), totals_base_minor=0, by_account=())
                for i in range(horizon_days + 1)
            ),
        )

    directions_by_cat = {
        c.id: c.direction for c in categories_repo.list_all(conn, include_deleted=True)
    }
    events = _collect_events(conn, today, end_date, directions_by_cat)

    if include_budget_overlay:
        primary_account_id = min(a.id for a in active_accounts)
        overlay_events = _collect_budget_overlay(
            conn, today, end_date, directions_by_cat, primary_account_id
        )
        for ev in overlay_events:
            events.setdefault(ev.on_date, []).append(ev)

    fx_rates = _collect_fx_rates(
        conn,
        http,
        today,
        {a.currency for a in active_accounts},
        base_currency,
    )

    running_native = dict(_anchor_balances(conn, today, active_accounts))
    days: list[DayPoint] = [
        _build_day(today, active_accounts, running_native, fx_rates, base_currency)
    ]

    for offset in range(1, horizon_days + 1):
        on_date = today + dt.timedelta(days=offset)
        for ev in events.get(on_date, ()):
            running_native[ev.account_id] = running_native.get(ev.account_id, 0) + ev.amount_minor
        days.append(_build_day(on_date, active_accounts, running_native, fx_rates, base_currency))

    return ForecastSeries(
        base_currency=base_currency,
        start_date=today,
        end_date=end_date,
        days=tuple(days),
    )


def _month_offset(anchor: dt.date, months: int) -> dt.date:
    """Return the first day of ``anchor``'s month shifted by ``months``."""
    year = anchor.year + (anchor.month - 1 + months) // 12
    month = (anchor.month - 1 + months) % 12 + 1
    return dt.date(year, month, 1)


def _last_day_of_month(month: dt.date) -> dt.date:
    return dt.date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])


def horizon_days_for_months(today: dt.date, horizon_months: int) -> int:
    """Convert a months-horizon into the daily horizon that covers it end-to-end."""
    last_month_start = _month_offset(today, horizon_months - 1)
    end_date = _last_day_of_month(last_month_start)
    return (end_date - today).days


def _month_flow_sums(
    conn: sqlite3.Connection,
    *,
    today: dt.date,
    end_date: dt.date,
    accounts: tuple[Account, ...],
    directions_by_cat: dict[int, Direction],
    fx_rates: dict[str, Decimal],
    base_currency: str,
) -> dict[dt.date, tuple[int, int]]:
    """Sum signed income + expense events per calendar month, in base currency.

    Returns ``{month_first_day: (income_base_minor, expense_base_minor)}``.
    Transits + adjustments are excluded (see MonthlyPoint docstring).
    """
    acct_ccy = {a.id: a.currency for a in accounts}
    sums: dict[dt.date, list[int]] = {}  # month -> [income, expense]

    def _add(on_date: dt.date, idx: int, delta: int) -> None:
        key = on_date.replace(day=1)
        bucket = sums.setdefault(key, [0, 0])
        bucket[idx] += delta

    event_start = today + dt.timedelta(days=1)
    if event_start > end_date:
        return {}

    persisted = planned_repo.list_filtered(
        conn,
        PlannedFilter(date_from=event_start, date_to=end_date, promoted=False),
    )
    dedup_keys: set[tuple[int, dt.date]] = {
        (row.recurring_rule_id, row.occurrence_date)
        for row in persisted
        if row.recurring_rule_id is not None and row.occurrence_date is not None
    }

    for row in persisted:
        direction = directions_by_cat[row.category_id]
        ccy = acct_ccy.get(row.account_id)
        if ccy is None:
            continue
        base = _convert_native_to_base(row.amount, ccy, base_currency, fx_rates)
        if direction is Direction.INCOME:
            _add(row.operation_date, 0, base)
        elif direction is Direction.EXPENSE:
            _add(row.operation_date, 1, base)

    for rule in recurring_repo.list_rules(conn, active_only=True):
        if _rule_outside_window(rule, event_start, end_date):
            continue
        overrides = recurring_repo.list_overrides(conn, rule.id)
        direction = directions_by_cat[rule.category_id]
        ccy = acct_ccy.get(rule.account_id)
        if ccy is None:
            continue
        for occ in recurring_svc.expand(rule, overrides, event_start, end_date):
            if (rule.id, occ.occurrence_date) in dedup_keys:
                continue
            base = _convert_native_to_base(occ.amount, ccy, base_currency, fx_rates)
            if direction is Direction.INCOME:
                _add(occ.effective_date, 0, base)
            elif direction is Direction.EXPENSE:
                _add(occ.effective_date, 1, base)

    return {month: (bucket[0], bucket[1]) for month, bucket in sums.items()}


def forecast_monthly(
    conn: sqlite3.Connection,
    http: httpx.Client,
    today: dt.date,
    horizon_months: int,
    base_currency: str,
) -> MonthlySeries:
    """Monthly aggregate projection over ``horizon_months`` months (ADR-0043).

    One row per calendar month in ``[today.month, today.month + horizon_months - 1]``:
    ``income_base_minor``, ``expense_base_minor``, ``net`` = income - expense,
    and ``end_balance_base_minor`` = projected total fortune at month-end.

    The daily projection is reused for end-of-month balances; monthly flow
    sums are re-derived from the same event stream to keep per-direction
    totals exact (daily totals aggregate both directions by net). The
    budget overlay (ADR-0042) is excluded here so the table reflects
    explicit planned + recurring + anchor state only — the chart on the
    page continues to render the overlay-adjusted projection separately.
    """
    if horizon_months < 1:
        raise ValueError(f"horizon_months must be >= 1, got {horizon_months}")

    start_month = today.replace(day=1)
    last_month = _month_offset(today, horizon_months - 1)
    end_date = _last_day_of_month(last_month)
    horizon_days = (end_date - today).days
    series = forecast(conn, http, today, horizon_days, base_currency, include_budget_overlay=False)

    active_accounts = tuple(accounts_repo.list_all(conn))
    if not active_accounts:
        months_empty = tuple(
            MonthlyPoint(
                month=_month_offset(today, offset),
                income_base_minor=0,
                expense_base_minor=0,
                net_base_minor=0,
                end_balance_base_minor=0,
            )
            for offset in range(horizon_months)
        )
        return MonthlySeries(
            base_currency=base_currency,
            start_month=start_month,
            end_month=last_month,
            months=months_empty,
        )

    directions_by_cat = {
        c.id: c.direction for c in categories_repo.list_all(conn, include_deleted=True)
    }
    fx_rates = _collect_fx_rates(
        conn, http, today, {a.currency for a in active_accounts}, base_currency
    )
    flows = _month_flow_sums(
        conn,
        today=today,
        end_date=end_date,
        accounts=active_accounts,
        directions_by_cat=directions_by_cat,
        fx_rates=fx_rates,
        base_currency=base_currency,
    )

    eom_by_month: dict[dt.date, int] = {}
    for d in series.days:
        eom_by_month[d.on_date.replace(day=1)] = d.totals_base_minor

    rows: list[MonthlyPoint] = []
    for offset in range(horizon_months):
        month = _month_offset(today, offset)
        income, expense = flows.get(month, (0, 0))
        rows.append(
            MonthlyPoint(
                month=month,
                income_base_minor=income,
                expense_base_minor=expense,
                net_base_minor=income - expense,
                end_balance_base_minor=eom_by_month.get(month, 0),
            )
        )

    return MonthlySeries(
        base_currency=base_currency,
        start_month=start_month,
        end_month=last_month,
        months=tuple(rows),
    )


__all__ = [
    "AccountBalancePoint",
    "DayPoint",
    "ForecastSeries",
    "MonthlyPoint",
    "MonthlySeries",
    "forecast",
    "forecast_monthly",
    "horizon_days_for_months",
]
