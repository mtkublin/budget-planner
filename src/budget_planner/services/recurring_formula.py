"""Formula-derived recurring amount (ADR-0043).

Pure parsing + validation helpers plus a DB-backed compute function.
Imported indirectly by ``services.recurring`` (which re-exports ``rt_expand``
and ``resolve_rule_amount``). Isolated from the pure cadence generator so
``generate_occurrences`` / ``apply_overrides`` remain DB-free.
"""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from budget_planner.domain.recurring import (
    AmountFormula,
    Occurrence,
    RecurringOverride,
    RecurringRule,
)

logger = logging.getLogger(__name__)

# Basis-point ceiling: 10 000% — formula sanity guard, not a product
# limit. Anything above this is almost certainly a data-entry mistake
# (coefficient_bps=120 ≠ 1200 confusion). Floor is 1 bps (0.01%).
_BPS_MIN = 1
_BPS_MAX = 1_000_000
_PERCENT_TO_BPS = Decimal("100")


class FormulaError(ValueError):
    """Raised when a formula fails validation at the save boundary."""


def parse_percent_to_bps(percent_str: str) -> int:
    """Convert a decimal percent string ("12", "12.5", "0.075") to int bps.

    Rounds half-up to the nearest basis point. Raises :class:`FormulaError`
    on non-decimal input or out-of-range values. Accepts "," as a decimal
    separator (same policy as ``domain.money.parse_amount_str``).
    """
    normalised = (percent_str or "").strip().replace(",", ".")
    if not normalised:
        raise FormulaError("coefficient is required for formula rules")
    try:
        dec = Decimal(normalised)
    except InvalidOperation as exc:
        raise FormulaError("coefficient must be a decimal number") from exc
    bps_dec = (dec * _PERCENT_TO_BPS).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    bps = int(bps_dec)
    if bps < _BPS_MIN or bps > _BPS_MAX:
        raise FormulaError(
            f"coefficient must be between {_BPS_MIN / 100:.2f}% and {_BPS_MAX / 100:.2f}%"
        )
    return bps


def build_formula(
    *,
    coefficient_percent: str,
    source_category_ids: Iterable[int],
) -> AmountFormula:
    """Validate + build an :class:`AmountFormula` from form inputs.

    Deduplicates source_category_ids while preserving the user's order.
    Raises :class:`FormulaError` on invalid input.
    """
    bps = parse_percent_to_bps(coefficient_percent)
    seen: set[int] = set()
    cleaned: list[int] = []
    for raw in source_category_ids:
        cid = int(raw)
        if cid in seen:
            continue
        seen.add(cid)
        cleaned.append(cid)
    if not cleaned:
        raise FormulaError("select at least one source category")
    return AmountFormula(coefficient_bps=bps, source_category_ids=tuple(cleaned))


def _month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
    first = dt.date(year, month, 1)
    if month == 12:  # noqa: PLR2004
        last = dt.date(year, 12, 31)
    else:
        last = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    return first, last


def _apply_coefficient(sum_minor: int, coefficient_bps: int) -> int:
    """Return ``round_half_up(sum_minor * coefficient_bps / 10 000)`` as int."""
    dec = Decimal(sum_minor) * Decimal(coefficient_bps) / Decimal(10_000)
    return int(dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_formula_amount(
    conn: sqlite3.Connection,
    formula: AmountFormula,
    year: int,
    month: int,
    *,
    exclude_rule_id: int | None = None,
) -> int:
    """Return the computed amount (minor units) for ``formula`` in ``(year, month)``.

    Enumerates every active, non-deleted recurring rule whose ``category_id``
    is in ``formula.source_category_ids`` AND whose ``amount_formula IS NULL``
    (cycle prevention — only fixed rules feed the sum). For each such rule,
    expands its canonical schedule within the calendar month (overrides
    applied) and sums the occurrence amounts. Returns 0 when no sources
    produce an occurrence.
    """
    from budget_planner.repositories import recurring as recurring_repo  # noqa: PLC0415
    from budget_planner.services.recurring import (  # noqa: PLC0415
        expand,
    )

    start, end = _month_bounds(year, month)
    source_ids = set(formula.source_category_ids)
    total_minor = 0
    for rule in recurring_repo.list_rules(conn, active_only=True):
        if rule.id == exclude_rule_id:
            continue
        if rule.category_id not in source_ids:
            continue
        if rule.amount_formula is not None:
            # Cycle guard: a formula referencing another formula is rejected
            # at save time; a stale cross-reference caught here is silently
            # dropped so the UI stays stable while the user cleans up.
            logger.warning(
                "formula source rule %s has its own formula; skipping",
                rule.id,
            )
            continue
        overrides = recurring_repo.list_overrides(conn, rule.id)
        for occ in expand(rule, overrides, start, end):
            total_minor += occ.amount
    return _apply_coefficient(total_minor, formula.coefficient_bps)


def resolve_rule_amount(
    conn: sqlite3.Connection,
    rule: RecurringRule,
    occurrence_date: dt.date,
) -> int:
    """Return the amount to use for an occurrence of ``rule``.

    Fixed rules → ``rule.default_amount``. Formula rules → recomputed from
    the formula using the occurrence's calendar month.
    """
    if rule.amount_formula is None:
        return rule.default_amount
    return compute_formula_amount(
        conn,
        rule.amount_formula,
        occurrence_date.year,
        occurrence_date.month,
        exclude_rule_id=rule.id,
    )


def rt_expand(
    conn: sqlite3.Connection,
    rule: RecurringRule,
    overrides: Iterable[RecurringOverride],
    range_start: dt.date,
    range_end: dt.date,
) -> tuple[Occurrence, ...]:
    """Expand ``rule`` across ``[range_start, range_end]`` with runtime amounts.

    Thin wrapper over :func:`services.recurring.expand` that substitutes
    computed amounts for formula rules before overrides apply. For fixed
    rules this is equivalent to calling ``expand`` directly.

    Overrides still win: an explicit ``amount_override`` beats the computed
    amount, consistent with the planned-override precedence everywhere else.
    """
    from budget_planner.services.recurring import (  # noqa: PLC0415
        apply_overrides,
        generate_occurrences,
    )

    occs = generate_occurrences(rule, range_start, range_end)
    if rule.amount_formula is not None:
        occs = tuple(_with_formula_amount(conn, rule, occs))
    return apply_overrides(occs, overrides)


def _with_formula_amount(
    conn: sqlite3.Connection,
    rule: RecurringRule,
    occurrences: Sequence[Occurrence],
) -> Iterable[Occurrence]:
    """Yield occurrences with ``amount`` replaced by the per-month formula result."""
    assert rule.amount_formula is not None
    cache: dict[tuple[int, int], int] = {}
    for occ in occurrences:
        key = (occ.occurrence_date.year, occ.occurrence_date.month)
        if key not in cache:
            cache[key] = compute_formula_amount(
                conn,
                rule.amount_formula,
                key[0],
                key[1],
                exclude_rule_id=rule.id,
            )
        yield Occurrence(
            rule_id=occ.rule_id,
            occurrence_date=occ.occurrence_date,
            effective_date=occ.effective_date,
            category_id=occ.category_id,
            account_id=occ.account_id,
            dest_account_id=occ.dest_account_id,
            amount=cache[key],
            description=occ.description,
            is_overridden=occ.is_overridden,
            is_skipped=occ.is_skipped,
        )


def validate_formula_sources(
    conn: sqlite3.Connection,
    formula: AmountFormula,
    *,
    exclude_rule_id: int | None = None,
) -> None:
    """Raise :class:`FormulaError` if any source category contains a formula rule.

    Enforces the ADR-0043 structural cycle guard at the save boundary: the
    dependency graph must be a 2-level tree (formula → fixed only). Compute
    time silently skips formula sources with a WARNING log; this call makes
    the rejection visible to the user before they save.
    """
    from budget_planner.repositories import recurring as recurring_repo  # noqa: PLC0415

    source_ids = set(formula.source_category_ids)
    for rule in recurring_repo.list_rules(conn, active_only=True):
        if rule.id == exclude_rule_id:
            continue
        if rule.amount_formula is None:
            continue
        if rule.category_id in source_ids:
            raise FormulaError(
                "a source category contains a formula rule — "
                "pick categories whose rules are fixed amounts only"
            )


__all__ = [
    "FormulaError",
    "build_formula",
    "compute_formula_amount",
    "parse_percent_to_bps",
    "resolve_rule_amount",
    "rt_expand",
    "validate_formula_sources",
]
