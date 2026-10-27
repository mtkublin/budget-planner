"""Budget service (T-024).

Resolve monthly budgets via the three-tier null-coalesce (one-off →
recurring → default) and build a month summary with per-category
budgeted / spent / remaining plus analytics (avg monthly overall,
avg this year, delta vs previous month). Flat categories, no rollover
(ADR-0014).

The service does its own aggregation over ``transactions.list_filtered``
rather than extending the repository with aggregate SQL — keeps the repo
a thin SQL wrapper (ADR-0022) and bounded loops are fine for v1 volumes.
"""

from __future__ import annotations

import calendar
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

from budget_planner.domain.enums import Direction
from budget_planner.domain.transactions import Transaction, TransactionFilter
from budget_planner.repositories import (
    budgets as budgets_repo,
    categories as categories_repo,
    transactions as transactions_repo,
)
from budget_planner.services import planned as planned_svc, preferences as preferences_svc


@dataclass(frozen=True, slots=True)
class CategoryBudgetLine:
    category_id: int
    category_name: str
    budgeted_minor: int | None
    spent_minor: int
    remaining_minor: int | None
    avg_monthly_overall_minor: int
    avg_this_year_minor: int
    delta_vs_prev_month_minor: int


@dataclass(frozen=True, slots=True)
class MonthTotals:
    budgeted_minor: int
    spent_minor: int
    remaining_minor: int


@dataclass(frozen=True, slots=True)
class MonthSummary:
    year: int
    month: int
    lines: tuple[CategoryBudgetLine, ...]
    totals: MonthTotals
    left_daily_spend_minor: int | None
    next_income_date: date
    days_until_next_income: int
    anchor_category_name: str | None


# ADR-0031 §3 — Yearly budget grid origin tag for cell typography.
# Literal "default" | "recurring" | "one_off" | "unset" is projected into the
# template to encode tier dominance via CSS classes.
@dataclass(frozen=True, slots=True)
class YearlyCell:
    amount_minor: int | None
    origin: str  # "default" | "recurring" | "one_off" | "unset"


@dataclass(frozen=True, slots=True)
class YearlyRow:
    category_id: int
    category_name: str
    cells: tuple[YearlyCell, ...]  # exactly 12 entries, Jan..Dec
    total_minor: int


def prev_year_month(year: int, month: int) -> tuple[int, int]:
    """Return the previous ``(year, month)`` tuple handling January rollover."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def resolve_budget(
    conn: sqlite3.Connection,
    category_id: int,
    year: int,
    month: int,
) -> int | None:
    """Null-coalesce: one-off → recurring → default. Zero is a valid value."""
    one_off = budgets_repo.get_one_off(conn, category_id, year, month)
    if one_off is not None:
        return one_off.amount
    recurring = budgets_repo.get_recurring(conn, category_id, month)
    if recurring is not None:
        return recurring.amount
    default = budgets_repo.get_default(conn, category_id)
    if default is not None:
        return default.amount
    return None


def _month_range(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _expense_txns_in_range(conn: sqlite3.Connection, start: date, end: date) -> list[Transaction]:
    return transactions_repo.list_filtered(
        conn,
        TransactionFilter(
            date_from=start,
            date_to=end,
            directions=(Direction.EXPENSE,),
        ),
    )


def _sum_by_category(txns: list[Transaction]) -> dict[int, int]:
    out: dict[int, int] = defaultdict(int)
    for t in txns:
        out[t.category_id] += t.amount
    return dict(out)


def _active_month_counts(txns: list[Transaction]) -> dict[int, int]:
    """Count distinct ``YYYY-MM`` buckets per category (expense direction only)."""
    seen: dict[int, set[str]] = defaultdict(set)
    for t in txns:
        key = f"{t.operation_date.year:04d}-{t.operation_date.month:02d}"
        seen[t.category_id].add(key)
    return {cat_id: len(months) for cat_id, months in seen.items()}


def _mean_minor(total: int, count: int) -> int:
    if count <= 0:
        return 0
    quantised = (Decimal(total) / Decimal(count)).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    return int(quantised)


def _all_expense_txns(conn: sqlite3.Connection) -> list[Transaction]:
    return transactions_repo.list_filtered(conn, TransactionFilter(directions=(Direction.EXPENSE,)))


def month_summary(
    conn: sqlite3.Connection,
    year: int,
    month: int,
    *,
    today: date,
) -> MonthSummary:
    """Build the per-category spent / budgeted / remaining view + analytics.

    Lines include every live expense-direction category. Totals exclude
    unbudgeted lines (``remaining_minor is None``). ``today`` is injected
    (ADR-0007) so left-daily-spend math stays deterministic in tests.
    """
    cats = [c for c in categories_repo.list_all(conn) if c.direction is Direction.EXPENSE]

    this_start, this_end = _month_range(year, month)
    prev_y, prev_m = prev_year_month(year, month)
    prev_start, prev_end = _month_range(prev_y, prev_m)
    year_start = date(year, 1, 1)
    year_end = _month_range(year, 12)[1]

    this_txns = _expense_txns_in_range(conn, this_start, this_end)
    prev_txns = _expense_txns_in_range(conn, prev_start, prev_end)
    year_txns = _expense_txns_in_range(conn, year_start, year_end)
    all_txns = _all_expense_txns(conn)

    spent_this = _sum_by_category(this_txns)
    spent_prev = _sum_by_category(prev_txns)
    year_sums = _sum_by_category(year_txns)
    overall_sum = _sum_by_category(all_txns)
    overall_mo = _active_month_counts(all_txns)

    elapsed_in_year = month if year_txns else max(month, 1)

    lines: list[CategoryBudgetLine] = []
    for cat in cats:
        budgeted = resolve_budget(conn, cat.id, year, month)
        spent = spent_this.get(cat.id, 0)
        remaining = (budgeted - spent) if budgeted is not None else None
        avg_overall = _mean_minor(overall_sum.get(cat.id, 0), overall_mo.get(cat.id, 0))
        avg_year = _mean_minor(year_sums.get(cat.id, 0), elapsed_in_year)
        delta_prev = spent - spent_prev.get(cat.id, 0)
        lines.append(
            CategoryBudgetLine(
                category_id=cat.id,
                category_name=cat.name,
                budgeted_minor=budgeted,
                spent_minor=spent,
                remaining_minor=remaining,
                avg_monthly_overall_minor=avg_overall,
                avg_this_year_minor=avg_year,
                delta_vs_prev_month_minor=delta_prev,
            )
        )

    # Budgeted first (False sorts before True), then alphabetical.
    lines.sort(key=lambda line: (line.budgeted_minor is None, line.category_name))

    totals = MonthTotals(
        budgeted_minor=sum(line.budgeted_minor or 0 for line in lines),
        spent_minor=sum(line.spent_minor for line in lines if line.budgeted_minor is not None),
        remaining_minor=sum(line.remaining_minor or 0 for line in lines),
    )

    end_of_month = _month_range(year, month)[1]
    if totals.budgeted_minor == 0:
        anchor_category_name: str | None = None
        next_income_date = end_of_month
        left_daily_spend_minor: int | None = None
    else:
        anchor = preferences_svc.resolve_income_anchor_category(conn)
        if anchor is None:
            anchor_category_name = None
            next_income_date = end_of_month
        else:
            hit = planned_svc.next_planned_for_category(conn, anchor.id, after=today)
            if hit is None:
                anchor_category_name = None
                next_income_date = end_of_month
            else:
                anchor_category_name = anchor.name
                next_income_date = hit.operation_date
    days_until_next_income = max((next_income_date - today).days, 1)
    if totals.budgeted_minor != 0:
        left_daily_spend_minor = int(
            (Decimal(totals.remaining_minor) / Decimal(days_until_next_income)).quantize(
                Decimal("1"), rounding=ROUND_HALF_EVEN
            )
        )

    return MonthSummary(
        year=year,
        month=month,
        lines=tuple(lines),
        totals=totals,
        left_daily_spend_minor=left_daily_spend_minor,
        next_income_date=next_income_date,
        days_until_next_income=days_until_next_income,
        anchor_category_name=anchor_category_name,
    )


def yearly_grid(conn: sqlite3.Connection, year: int) -> tuple[YearlyRow, ...]:
    """Return per-category (rows) by Jan..Dec (12 cells) resolved budgets.

    Projection over the three persistence tables; no new storage per
    ADR-0031 §3. Each cell carries both the resolved amount (or ``None``
    when no tier is set) and the origin tag so the UI can encode tier
    dominance via typography (bold = one-off, italic = recurring, plain =
    default, em-dash = unset).
    """
    cats = [c for c in categories_repo.list_all(conn) if c.direction is Direction.EXPENSE]
    defaults_by_cat = {d.category_id: d.amount for d in budgets_repo.list_defaults(conn)}
    recurring_by_key: dict[tuple[int, int], int] = {
        (r.category_id, r.month): r.amount for r in budgets_repo.list_recurring(conn)
    }
    one_off_by_key: dict[tuple[int, int], int] = {
        (o.category_id, o.month): o.amount for o in budgets_repo.list_one_off(conn, year=year)
    }

    rows: list[YearlyRow] = []
    for cat in cats:
        cells: list[YearlyCell] = []
        total = 0
        for month in range(1, 13):
            one_off = one_off_by_key.get((cat.id, month))
            if one_off is not None:
                cells.append(YearlyCell(amount_minor=one_off, origin="one_off"))
                total += one_off
                continue
            recurring = recurring_by_key.get((cat.id, month))
            if recurring is not None:
                cells.append(YearlyCell(amount_minor=recurring, origin="recurring"))
                total += recurring
                continue
            default = defaults_by_cat.get(cat.id)
            if default is not None:
                cells.append(YearlyCell(amount_minor=default, origin="default"))
                total += default
                continue
            cells.append(YearlyCell(amount_minor=None, origin="unset"))
        rows.append(
            YearlyRow(
                category_id=cat.id,
                category_name=cat.name,
                cells=tuple(cells),
                total_minor=total,
            )
        )
    rows.sort(key=lambda r: r.category_name.casefold())
    return tuple(rows)


__all__ = [
    "CategoryBudgetLine",
    "MonthSummary",
    "MonthTotals",
    "YearlyCell",
    "YearlyRow",
    "month_summary",
    "prev_year_month",
    "resolve_budget",
    "yearly_grid",
]
