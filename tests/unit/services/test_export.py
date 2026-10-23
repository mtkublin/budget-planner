"""Tests for the generic export service (T-027)."""

from __future__ import annotations

import io
from datetime import date

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from budget_planner.services.export import (
    ExportColumn,
    UnknownColumnError,
    export_csv,
    export_parquet,
)

_COLS = (
    ExportColumn(key="date", header="Date", kind="date"),
    ExportColumn(key="account", header="Account", kind="str"),
    ExportColumn(key="amount", header="Amount", kind="money_minor"),
)


def test_csv_header_and_row() -> None:
    out = export_csv([{"date": date(2026, 1, 15), "account": "Checking", "amount": 12345}], _COLS)
    text = out.decode("utf-8")
    assert text.splitlines()[0] == "Date,Account,Amount"
    assert text.splitlines()[1] == "2026-01-15,Checking,12345"


def test_csv_empty_rows_is_header_only() -> None:
    out = export_csv([], _COLS).decode("utf-8")
    assert out.splitlines() == ["Date,Account,Amount"]


def test_csv_null_str_renders_empty() -> None:
    out = export_csv([{"date": date(2026, 1, 15), "account": None, "amount": 0}], _COLS).decode(
        "utf-8"
    )
    assert out.splitlines()[1] == "2026-01-15,,0"


def test_csv_bool_rendering() -> None:
    cols = (ExportColumn(key="active", header="Active", kind="bool"),)
    out = export_csv([{"active": True}, {"active": False}], cols).decode("utf-8")
    assert out.splitlines() == ["Active", "true", "false"]


def test_csv_date_formatting() -> None:
    cols = (ExportColumn(key="d", header="D", kind="date"),)
    out = export_csv([{"d": date(2026, 1, 15)}], cols).decode("utf-8")
    assert out.splitlines()[1] == "2026-01-15"


def test_csv_money_unscaled_integer() -> None:
    cols = (ExportColumn(key="m", header="M", kind="money_minor"),)
    out = export_csv([{"m": 12345}], cols).decode("utf-8")
    assert out.splitlines()[1] == "12345"


def test_csv_unicode_round_trip() -> None:
    cols = (ExportColumn(key="d", header="D", kind="str"),)
    out = export_csv([{"d": "café — 米"}], cols).decode("utf-8")
    assert out.splitlines()[1] == "café — 米"


def test_csv_deterministic_bytes() -> None:
    rows = [{"date": date(2026, 1, 15), "account": "A", "amount": 1}]
    assert export_csv(rows, _COLS) == export_csv(rows, _COLS)


def test_csv_unknown_column_raises() -> None:
    with pytest.raises(UnknownColumnError):
        export_csv([{"a": 1}], (ExportColumn(key="b", header="B", kind="int"),))


def test_csv_column_order_matters() -> None:
    reversed_cols = tuple(reversed(_COLS))
    out = export_csv(
        [{"date": date(2026, 1, 15), "account": "C", "amount": 1}], reversed_cols
    ).decode("utf-8")
    assert out.splitlines()[0] == "Amount,Account,Date"


def test_csv_int_kind() -> None:
    cols = (ExportColumn(key="n", header="N", kind="int"),)
    out = export_csv([{"n": 42}], cols).decode("utf-8")
    assert out.splitlines()[1] == "42"


def test_parquet_round_trip() -> None:
    rows = [
        {"date": date(2026, 1, 15), "account": "Checking", "amount": 12345},
        {"date": date(2026, 2, 1), "account": "Savings", "amount": -200},
    ]
    out = export_parquet(rows, _COLS)
    table = pq.read_table(io.BytesIO(out))
    df = table.to_pandas()
    assert list(df["Date"]) == [date(2026, 1, 15), date(2026, 2, 1)]
    assert list(df["Account"]) == ["Checking", "Savings"]
    assert list(df["Amount"]) == [12345, -200]


def test_parquet_dtypes() -> None:
    cols = (
        ExportColumn(key="d", header="D", kind="date"),
        ExportColumn(key="s", header="S", kind="str"),
        ExportColumn(key="m", header="M", kind="money_minor"),
        ExportColumn(key="b", header="B", kind="bool"),
        ExportColumn(key="n", header="N", kind="int"),
    )
    rows = [{"d": date(2026, 1, 1), "s": "x", "m": 1, "b": True, "n": 2}]
    table = pq.read_table(io.BytesIO(export_parquet(rows, cols)))
    schema = table.schema
    assert pa.types.is_date32(schema.field("D").type)
    assert pa.types.is_string(schema.field("S").type)
    assert pa.types.is_integer(schema.field("M").type)
    assert pa.types.is_boolean(schema.field("B").type)
    assert pa.types.is_integer(schema.field("N").type)


def test_parquet_nulls_in_strings() -> None:
    cols = (ExportColumn(key="s", header="S", kind="str"),)
    rows: list[dict[str, str | None]] = [{"s": "hello"}, {"s": None}]
    table = pq.read_table(io.BytesIO(export_parquet(rows, cols)))
    values = table.column("S").to_pylist()
    assert values == ["hello", None]


def test_parquet_unknown_column_raises() -> None:
    with pytest.raises(UnknownColumnError):
        export_parquet([{"a": 1}], (ExportColumn(key="b", header="B", kind="int"),))
