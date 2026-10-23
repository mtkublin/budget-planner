# T-027 — Export Service

> Phase 2 — Services. Status: pending.

## Purpose

Serialise an in-memory list of rows into CSV or Parquet bytes. Reused across the transaction log, planned log, and analytics views (ADR-0020). The service is intentionally dumb about domain shape — callers hand it a column order plus a list of mappings. Keeping it generic avoids three near-identical exporters and matches DRY-by-composition from the implementation plan.

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `Transaction`, `PlannedTransaction`, `Money` helpers; the service does not import them directly but shares their minor-unit conventions.
- Upstream Phase 2:
  - None mandatory, but callers (T-031 Transactions router, T-034 Planned router, T-038 Analytics router) will supply already-shaped record lists.
- ADRs:
  - [ADR-0020 Import deferred, export v1](../../adr/0020-import-deferred-export-v1.md).
  - [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
- Third-party:
  - CSV via stdlib `csv` module.
  - Parquet via `pyarrow` + `pandas` (both already listed as deps in T-001).

## Deliverables

- Module path: `src/budget_planner/services/export.py`
- Test module path: `tests/unit/services/test_export.py`
- Public function signatures:

```python
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExportColumn:
    key: str                 # key into the row mapping
    header: str              # label written to the file
    kind: str                # "int" | "money_minor" | "date" | "str" | "bool"
    currency_key: str | None = None   # for kind="money_minor" rows that carry a per-row currency column


def export_csv(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[ExportColumn],
) -> bytes: ...


def export_parquet(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[ExportColumn],
) -> bytes: ...
```

## Algorithm / step-by-step

### Row shape

- `rows`: list of plain `dict`-like mappings (the caller builds these from domain dataclasses — a tiny `asdict`-plus-join helper per router).
- `columns`: ordered sequence that drives header order and type conversion. Unknown keys raise `UnknownColumnError`.
- Minor-unit money columns are **not** auto-converted to major units. The exported file contains the raw integer plus (optional) a separate currency column. Downstream tooling (pandas, duckdb, Excel) can scale by currency. Rationale: lossless export, no float introduction. Document in the docstring and in `docs/CHANGELOG.md` on landing.

### `export_csv`

```python
import csv, io
def export_csv(rows, columns):
    buf = io.StringIO()
    writer = csv.writer(buf, dialect="excel", lineterminator="\n")
    writer.writerow(col.header for col in columns)
    for row in rows:
        writer.writerow(_format_cell(row[col.key], col) for col in columns)
    return buf.getvalue().encode("utf-8")
```

`_format_cell` is pure:

| `kind` | Formatting |
|--------|-----------|
| `"int"` | `str(value)` |
| `"money_minor"` | `str(value)` (integer; no scaling) |
| `"date"` | `value.isoformat()` (`YYYY-MM-DD`) |
| `"str"` | `value` as-is, `""` for `None` |
| `"bool"` | `"true"` / `"false"` |

Nulls export as empty string.

### `export_parquet`

```python
import io
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def export_parquet(rows, columns):
    df = pd.DataFrame({col.key: [_coerce_cell(r.get(col.key), col) for r in rows] for col in columns})
    df.columns = [col.header for col in columns]
    table = pa.Table.from_pandas(df, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    return buf.getvalue()
```

`_coerce_cell` maps `kind` → pyarrow-friendly type:

| `kind` | Pandas dtype hint |
|--------|-------------------|
| `"int"` | `pd.Int64Dtype()` (nullable) |
| `"money_minor"` | `pd.Int64Dtype()` |
| `"date"` | `date` object → stored as `date32` after `pa.Table.from_pandas` |
| `"str"` | `pd.StringDtype()` |
| `"bool"` | `pd.BooleanDtype()` |

Explicit dtypes avoid pandas inferring `object`.

Compression: `zstd` default (small, fast). Document that the parquet file can be opened by pandas, DuckDB, or anything with Apache Arrow.

### Streaming consideration

v1 operates on bounded result sets (filtered transaction/planned logs for a single user). Both exporters materialise fully in memory. If the "export entire history" button is added later, revisit via a stream API; out of scope now.

## Interfaces / contracts

```python
def export_csv(rows, columns) -> bytes:
    """
    UTF-8 CSV with LF line endings, Excel dialect, header row from
    `columns`. Minor-unit money columns are exported as raw integers;
    callers who want a human-readable scaled value must build an extra
    column (e.g. `amount_major = amount_minor / 10^decimals`) and pass it
    as kind='str'.
    """


def export_parquet(rows, columns) -> bytes:
    """
    Apache Parquet, zstd compression, no index column. Column dtypes are
    chosen from ExportColumn.kind to prevent pandas type inference drift.
    """
```

```python
class UnknownColumnError(KeyError): ...
```

## Test strategy

Fixtures: in-memory. No DB required.

Cases:

1. **CSV header**: given columns `[Date, Account, Amount]`, assert the first line of the output is `Date,Account,Amount`.
2. **CSV rows**: feed `[{date: 2026-01-15, account: "Checking", amount: 12345}]` with the matching column kinds; assert exactly one data line `2026-01-15,Checking,12345`.
3. **CSV empty rows**: `rows=[]` returns just the header row + newline.
4. **CSV null handling**: a `None` for an `"str"` column exports as empty string.
5. **CSV bool rendering**: `True` → `"true"`, `False` → `"false"`.
6. **CSV date formatting**: `date(2026, 1, 15)` → `2026-01-15`.
7. **CSV money is unscaled**: `12345` minor units for a 2-decimal currency exports as `12345`, not `123.45`.
8. **Parquet round-trip**: write with `export_parquet(...)`, read back via `pq.read_table(io.BytesIO(bytes))`, assert the column names, dtypes, and values match.
9. **Parquet dtypes**: a column of `"money_minor"` has Arrow type `int64`; `"date"` has `date32`; `"bool"` has `bool`; `"str"` has `string`.
10. **Parquet nulls**: a mix of `None` and real values in an `"str"` column survives the round-trip.
11. **Unknown column key**: `rows=[{"a": 1}]` with `columns=[ExportColumn("b", ...)]` → `UnknownColumnError`.
12. **Deterministic bytes for CSV**: calling `export_csv` twice with the same inputs yields identical bytes (useful for tests + diffing). Parquet is not byte-stable (zstd framing), so test for round-trip equality instead.
13. **Column ordering**: changing the `columns` order changes the output column order.
14. **Unicode**: a row with description `"café — 米"` round-trips through both exporters.

Mocking boundaries: none. The service has no network / no DB.

## Risks & gotchas

- **Minor-unit vs major-unit money**: the choice to export raw integers is deliberate (lossless, no float). Users who open the CSV in Excel will see `12345` for `123.45 PLN`. Document loudly in the UI tooltip for the export button. Alternative — adding a scaled column — is a router concern, not this service's.
- **CSV line endings**: Excel is happy with `\n` but some tools expect `\r\n`. The plan uses `\n` for byte-stable output and documents it.
- **Floating-point via pandas**: pandas eagerly promotes columns to `float64` when any `None` is present and the dtype isn't explicit. The nullable `pd.Int64Dtype` is critical — do not skip the explicit dtype step.
- **Parquet non-determinism**: zstd framing can vary across versions. Tests must compare via Arrow round-trip, not by byte equality.
- **Large exports**: materialising a 5-year unfiltered log in memory before writing is fine for v1 (bounded user data). Flag for revisit if we ever land scheduled exports.
- **Timezones in Parquet**: `date` columns are `date32`, not `timestamp`. If `datetime` sneaks in from the caller, pyarrow may upgrade to `timestamp[ns]`. Guard in `_coerce_cell` by type-checking `date` vs `datetime`.
- **Currency column coupling**: `ExportColumn.currency_key` is defined but unused in v1 (reserved for a multi-currency export annotation column). Keep the field; do not inflate the implementation.

## Handoff notes

Phase 3 consumers:

- **Transactions router (T-031)**: `GET /transactions/export?format=csv|parquet` → fetches filtered rows via `repositories.transactions.list_filtered`, builds `rows: list[dict]`, defines a canonical `columns` list (date, account, category, direction, amount_minor, description), calls the exporter, returns a FastAPI `Response(bytes, media_type=...)`.
- **Planned router (T-034)**: analogous, operates on `services.planned.list_planned` output.
- **Analytics router (T-038)**: exports whatever aggregated view is currently rendered.

Router-side helpers that convert domain dataclasses into export mappings should live close to each router (`web/routers/_export_shapes.py` or similar), not in this service — the service stays shape-agnostic.
