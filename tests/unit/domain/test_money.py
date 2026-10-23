from __future__ import annotations

from decimal import Decimal

import pytest

from budget_planner.domain.money import (
    currency_decimals,
    format_money,
    from_minor_units,
    to_minor_units,
)


def test_currency_decimals_defaults_to_two() -> None:
    assert currency_decimals("PLN") == 2
    assert currency_decimals("eur") == 2
    assert currency_decimals("ABC") == 2  # Unknown falls back to 2.
    assert currency_decimals("JPY") == 0
    assert currency_decimals("KRW") == 0


@pytest.mark.parametrize(
    ("major", "currency", "expected_minor"),
    [
        (Decimal("12.34"), "PLN", 1234),
        (Decimal("0.01"), "EUR", 1),
        (Decimal("-0.01"), "EUR", -1),
        (Decimal("1234"), "JPY", 1234),
        (Decimal("1234.5"), "JPY", 1235),  # rounds half-up
        (Decimal("0"), "USD", 0),
    ],
)
def test_to_minor_units(major: Decimal, currency: str, expected_minor: int) -> None:
    assert to_minor_units(major, currency) == expected_minor


def test_from_minor_units_round_trip() -> None:
    for amount in [-999999, -1, 0, 1, 500, 12345, 999999]:
        for ccy in ("PLN", "EUR", "USD", "JPY"):
            back = from_minor_units(amount, ccy)
            fwd = to_minor_units(back, ccy)
            assert fwd == amount, f"{ccy}:{amount} -> {back} -> {fwd}"


def test_format_money_positive_pln() -> None:
    assert format_money(123456, "PLN") == "1,234.56 PLN"


def test_format_money_negative() -> None:
    assert format_money(-5000, "USD") == "-50.00 USD"


def test_format_money_zero_decimals_currency() -> None:
    assert format_money(1234, "JPY") == "1,234 JPY"


def test_format_money_uppercases_currency() -> None:
    assert format_money(10, "eur") == "0.10 EUR"
