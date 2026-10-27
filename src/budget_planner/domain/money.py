"""Money helpers.

Amounts are stored as signed integer minor units of the account currency
(ADR-0008 / ADR-0006). All conversion between major-unit ``Decimal`` and
integer minor units routes through this module.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

# Minor-unit decimals for currencies we care about in v1. Default is 2.
_CURRENCY_DECIMALS: Final[dict[str, int]] = {
    "JPY": 0,
    "KRW": 0,
    "HUF": 2,
    "PLN": 2,
    "EUR": 2,
    "USD": 2,
    "GBP": 2,
    "CHF": 2,
}

# ISO 4217 active currency codes (ADR-0030). Alphabetical order so the combobox
# surfaces predictable results. Not exhaustive — the subset below covers every
# currency the app is expected to see in v1 while giving the user a familiar
# dropdown. Validation at the service boundary still accepts any three-letter
# ISO code so adding a less-common currency does not require a code change.
ISO_4217_CURRENCIES: Final[tuple[str, ...]] = (
    "AED",
    "AFN",
    "ALL",
    "AMD",
    "ANG",
    "AOA",
    "ARS",
    "AUD",
    "AWG",
    "AZN",
    "BAM",
    "BBD",
    "BDT",
    "BGN",
    "BHD",
    "BIF",
    "BMD",
    "BND",
    "BOB",
    "BRL",
    "BSD",
    "BTN",
    "BWP",
    "BYN",
    "BZD",
    "CAD",
    "CDF",
    "CHF",
    "CLP",
    "CNY",
    "COP",
    "CRC",
    "CUP",
    "CVE",
    "CZK",
    "DJF",
    "DKK",
    "DOP",
    "DZD",
    "EGP",
    "ERN",
    "ETB",
    "EUR",
    "FJD",
    "FKP",
    "GBP",
    "GEL",
    "GHS",
    "GIP",
    "GMD",
    "GNF",
    "GTQ",
    "GYD",
    "HKD",
    "HNL",
    "HTG",
    "HUF",
    "IDR",
    "ILS",
    "INR",
    "IQD",
    "IRR",
    "ISK",
    "JMD",
    "JOD",
    "JPY",
    "KES",
    "KGS",
    "KHR",
    "KMF",
    "KPW",
    "KRW",
    "KWD",
    "KYD",
    "KZT",
    "LAK",
    "LBP",
    "LKR",
    "LRD",
    "LSL",
    "LYD",
    "MAD",
    "MDL",
    "MGA",
    "MKD",
    "MMK",
    "MNT",
    "MOP",
    "MRU",
    "MUR",
    "MVR",
    "MWK",
    "MXN",
    "MYR",
    "MZN",
    "NAD",
    "NGN",
    "NIO",
    "NOK",
    "NPR",
    "NZD",
    "OMR",
    "PAB",
    "PEN",
    "PGK",
    "PHP",
    "PKR",
    "PLN",
    "PYG",
    "QAR",
    "RON",
    "RSD",
    "RUB",
    "RWF",
    "SAR",
    "SBD",
    "SCR",
    "SDG",
    "SEK",
    "SGD",
    "SHP",
    "SLE",
    "SOS",
    "SRD",
    "SSP",
    "STN",
    "SVC",
    "SYP",
    "SZL",
    "THB",
    "TJS",
    "TMT",
    "TND",
    "TOP",
    "TRY",
    "TTD",
    "TWD",
    "TZS",
    "UAH",
    "UGX",
    "USD",
    "UYU",
    "UZS",
    "VES",
    "VND",
    "VUV",
    "WST",
    "XAF",
    "XCD",
    "XDR",
    "XOF",
    "XPF",
    "YER",
    "ZAR",
    "ZMW",
    "ZWL",
)


def currency_decimals(currency: str) -> int:
    """Return the number of minor-unit decimals for ``currency``.

    Defaults to 2 for currencies not listed above.
    """
    return _CURRENCY_DECIMALS.get(currency.upper(), 2)


def to_minor_units(amount: Decimal, currency: str) -> int:
    """Convert a Decimal major-unit amount to signed integer minor units.

    Uses banker's-safe ROUND_HALF_UP (consistent with user expectations in
    finance UIs). Does not clamp the magnitude.
    """
    decimals = currency_decimals(currency)
    quant = Decimal(10) ** -decimals
    quantised = amount.quantize(quant, rounding=ROUND_HALF_UP)
    return int(quantised * (Decimal(10) ** decimals))


def from_minor_units(amount_minor: int, currency: str) -> Decimal:
    """Convert signed minor units back to a ``Decimal`` major-unit amount."""
    decimals = currency_decimals(currency)
    return Decimal(amount_minor) / (Decimal(10) ** decimals)


def format_money(amount_minor: int, currency: str) -> str:
    """Render as e.g. ``'1,234.56 PLN'`` or ``'1,234 JPY'``.

    Preserves sign for negative values. Zero renders without a sign.
    """
    decimals = currency_decimals(currency)
    value = from_minor_units(amount_minor, currency)
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole, _, frac = f"{value:,.{decimals}f}".partition(".")
    return f"{sign}{whole}{('.' + frac) if frac else ''} {currency.upper()}"
