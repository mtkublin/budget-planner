# T-025 — Forecast Service

> Phase 2 — Services. Status: pending.

## Purpose

Deterministic forward-looking balance projection. For each day in a user-selected horizon starting at `today + 1`, project the balance for every active account by applying planned transactions (persisted + virtual recurring occurrences) in operation-date order on top of each account's current derived balance. Aggregate into base currency (`config.base_currency`, default `PLN`) per day. Pure (ADR-0015). Reflects user plans only; no trend inference.

## Inputs / prerequisites

- Upstream Phase 1 tasks:
  - [T-013 Repositories](../phase-1/T-013-repository-layer.md) — `repositories/accounts.py`, `repositories/planned.py`, `repositories/recurring.py`.
  - [T-014 Domain types](../phase-1/T-014-domain-types.md) — `Account`, `PlannedTransaction`, `RecurringRule`.
- Upstream Phase 2:
  - [T-020 FX service](T-020-fx-service.md) — `convert(...)` / `get_rate(...)`.
  - [T-021 Balance service](T-021-balance-service.md) — `derive_balance(...)` for "today" anchor.
  - [T-022 Recurring occurrence generator](T-022-recurring-occurrence-generator.md) — `expand(...)`.
- ADRs:
  - [ADR-0015 Forecast deterministic, live via HTMX](../../adr/0015-forecast-deterministic-live-htmx.md). *(tasks.md incorrectly cites ADR-0018 for T-025; the correct ADR is 0015. ADR-0018 is the CI single matrix row.)*
  - [ADR-0006 Multi-currency model](../../adr/0006-multi-currency-model.md) — forecast uses **latest cached FX rate** for forward aggregation (not historical per-day).
  - [ADR-0008 Transaction amount sign & direction](../../adr/0008-transaction-amount-sign-and-direction.md), [ADR-0009 Transit single-row model](../../adr/0009-transit-single-row-model.md), [ADR-0021 Functional style](../../adr/0021-functional-style-no-oop.md).
- Repository functions consumed:
  - `repositories.accounts.list_active(conn) -> list[Account]`
  - `repositories.planned.list_unpromoted_in_range(conn, start, end) -> list[PlannedTransaction]`
  - `repositories.recurring.list_active_rules(conn, in_range=(start, end)) -> list[RecurringRule]`
  - `repositories.recurring.list_overrides_for_rule(conn, rule_id) -> list[RecurringRuleOverride]`

## Deliverables

- Module path: `src/budget_planner/services/forecast.py`
- Test module path: `tests/unit/services/test_forecast.py`
- Public function signatures:

```python
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

import httpx

from budget_planner.domain.money import Currency


@dataclass(frozen=True, slots=True)
class AccountBalancePoint:
    account_id: int
    on_date: dt.date
    native_minor: int        # minor units of the account's own currency
    base_minor: int          # minor units of base_currency, converted at the day's FX rate


@dataclass(frozen=True, slots=True)
class DayPoint:
    on_date: dt.date
    totals_base_minor: int                        # Σ across accounts in base currency
    by_account: tuple[AccountBalancePoint, ...]   # one entry per active account


@dataclass(frozen=True, slots=True)
class ForecastSeries:
    base_currency: Currency
    start_date: dt.date                           # today
    end_date: dt.date                             # today + horizon_days
    days: tuple[DayPoint, ...]                    # length == horizon_days + 1


def forecast(
    conn: sqlite3.Connection,
    http: httpx.Client,
    today: dt.date,
    horizon_days: int,
    base_currency: Currency,
) -> ForecastSeries: ...
```

`today` is injected (not read from `datetime.today()` inside the service) so tests are deterministic and tz-independent.

## Algorithm / step-by-step

```
Inputs: conn, http, today, horizon_days, base_currency
Window: [today, today + horizon_days]  (inclusive both sides, horizon_days + 1 points)

1. Load the universe:
     accounts = repositories.accounts.list_active(conn)
     planned  = repositories.planned.list_unpromoted_in_range(conn,
                    today + 1 day, today + horizon_days)
     rules    = repositories.recurring.list_active_rules(conn,
                    in_range=(today + 1 day, today + horizon_days))
     occurrences = []
     for r in rules:
         ovr = repositories.recurring.list_overrides_for_rule(conn, r.id)
         occurrences.extend(services.recurring.expand(r, ovr, today + 1 day, today + horizon_days))

2. De-dup: drop any occurrence whose (recurring_rule_id, occurrence_date)
   already appears in `planned` as a materialised row. Same rule as T-023's
   list_planned, but applied here to avoid double-counting. Prefer the
   persisted planned row.

3. Bucket "cash events" by operation_date:
     events_by_date: dict[date, list[CashEvent]]
     - For each planned row:   emit CashEvent(operation_date, signed_leg(s))
     - For each virtual occ:   emit CashEvent(occurrence_date, signed_leg(s))
   Use services.balance.signed_legs(...) adapted to accept Occurrence-like
   DTOs (category direction known via planned.category_id lookup / rule's
   category_id). To avoid N+1 lookups, pre-fetch the direction map:
     cat_dir = repositories.categories.directions_by_id(conn)

4. Anchor each account at today:
     anchor_native[a.id] = services.balance.derive_balance(conn, a.id,
                                                           as_of_date=today)

5. Precompute today's FX rate per currency to base_currency (ONE call per
   distinct account currency):
     fx[a.currency] = services.fx.get_rate(conn, http, today,
                                           a.currency, base_currency)
   (identity for a.currency == base_currency)
   NB: FX for forecast uses the latest known rate (ADR-0006/ADR-0015). The
   simplest realisation is "today's rate", held constant across the horizon.
   This is correct for the deterministic contract — the forecast is not a
   currency forecast.

6. Walk the horizon:
     running_native = dict(anchor_native)
     days: list[DayPoint] = []
     for d in daterange(today, today + horizon_days):
         if d != today:
             for ev in events_by_date.get(d, []):
                 running_native[ev.account_id] += ev.signed_amount_minor
         # today's point is the anchor itself (no events applied).
         by_account = tuple(
             AccountBalancePoint(
                 account_id=a.id, on_date=d,
                 native_minor=running_native[a.id],
                 base_minor=_convert_native_to_base(running_native[a.id], a.currency, fx),
             )
             for a in accounts
         )
         total = sum(p.base_minor for p in by_account)
         days.append(DayPoint(d, total, by_account))

7. Return ForecastSeries(base_currency, today, today + horizon_days, tuple(days)).
```

`_convert_native_to_base(amount_native, ccy, fx)` multiplies by the pre-fetched Decimal rate and quantises to base-currency minor units (`ROUND_HALF_EVEN`). The service never calls `services.fx.convert` per day — that would make `horizon_days * n_accounts` identical calls.

### Signed events for transit occurrences

A transit occurrence (planned or virtual) produces **two** `CashEvent`s on the same date — `-amount` on `account_id`, `+amount` on `dest_account_id` — identical to `services.balance.signed_legs` for actual transactions.

### Adjustment / reconciliation handling

Planned adjustments are not supported (T-023 blocks promotion for adjustments). Any surviving row is ignored by the forecast with a `DEBUG` log line.

## Interfaces / contracts

```python
def forecast(conn, http, today, horizon_days, base_currency) -> ForecastSeries:
    """
    Deterministic forward projection.

    - Day 0 of the series == `today` and equals the derived balance per
      account anchored by services.balance.derive_balance.
    - Each subsequent day applies the cash events scheduled on that day in
      operation_date order (within-day ordering is sort-stable by
      (account_id, planned.id or (rule_id, occurrence_date))).
    - Aggregation to base_currency uses TODAY's FX rate, held constant across
      the horizon (ADR-0006/0015).
    - Pure. Same inputs + same DB snapshot + same FX cache state → identical
      output.
    """
```

Invariants:

- `len(days) == horizon_days + 1`.
- `days[0].on_date == today` and `days[0].totals_base_minor` equals the sum of each account's `derive_balance(today)` converted at today's rate.
- Removing (soft-deleting) a planned row before calling `forecast` reduces the projected balance on all days after that row's `operation_date` by exactly the signed-leg magnitude.

## Test strategy

Use a seeded fixture small enough to compute expected numbers by hand. Example:

```
today = 2026-10-23
base_currency = PLN

accounts:
   A1 Checking  PLN  opening_balance = 100_000     # derived balance today assumed 150_000
   A2 Savings   PLN  opening_balance =       0
   A3 EUR Cash  EUR  opening_balance =  50_000     # today derived = 50_000; rate EUR→PLN = 4.30

planned_transactions (unpromoted):
   P1 2026-10-25 expense  cat=Groceries   amount=10_000  account=A1
   P2 2026-11-05 transit                 amount=20_000  from=A1 to=A2
   P3 2026-11-15 income   cat=Salary     amount=800_000 account=A1

recurring_rules (active):
   R1 monthly start=2026-10-01 expense Rent amount=300_000 account=A1
      -> virtual occurrences at 2026-11-01 (inside horizon), 2026-12-01

fx cache:
   (today, EUR, PLN) = 4.30
```

Horizon: 60 days.

Cases:

1. **Deterministic output for seeded DB**: call `forecast(...)` twice; assert equal.
2. **Anchor correct**: `days[0].by_account[A1].native_minor == derive_balance(A1, today)`.
3. **Expense moves native balance**: on `2026-10-25` A1 drops by 10_000 vs the previous day.
4. **Transit affects both legs**: on `2026-11-05` A1 drops by 20_000 and A2 rises by 20_000.
5. **Income increases balance**: on `2026-11-15` A1 rises by 800_000.
6. **Virtual recurring applied**: on `2026-11-01` A1 drops by 300_000 (Rent occurrence from R1).
7. **Dedup**: materialise the 2026-11-01 occurrence as a persisted planned row with `occurrence_date=2026-11-01, rule_id=R1`. Assert the forecast still drops by exactly 300_000, not 600_000.
8. **FX aggregation**: `days[0].totals_base_minor == A1_native + A2_native + round(A3_native * 4.30)`. Base-currency total uses today's rate.
9. **Latest FX cached as fallback**: delete today's FX row, insert yesterday's; `forecast` picks up yesterday's via `services.fx.get_rate`'s cache-miss path (mock `httpx` to raise so fallback kicks in). Series matches with yesterday's rate applied.
10. **Horizon length**: `len(days) == 61`.
11. **Deactivated rule**: flip `R1.active=False`; the Nov 01 drop disappears.
12. **Soft-deleted planned excluded**: delete P1; the Oct 25 drop disappears.
13. **End of horizon**: `days[-1].on_date == today + 60d`.
14. **Horizon=0 edge**: returns a 1-day series equal to the anchor. (Hard-code: should still succeed.)
15. **Property**: for any two days `d1 < d2`, `days[d2].by_account[a].native_minor - days[d1].by_account[a].native_minor` equals the signed sum of events for `a` in `(d1, d2]`.
16. **No events, no change**: an account with no planned/recurring touching it has a flat line equal to its anchor every day.

Fixtures:

- `forecast_conn`: full schema with accounts, categories (including Rent, Groceries, Salary, Transit), planned, recurring, overrides, fx_rates.
- `freeze_today(today=dt.date(2026, 10, 23))` fixture.
- `fake_http`: `httpx.Client` mock (used only when FX cache misses).

Mocking boundaries: only `httpx.Client` for FX fallbacks. Live DB, live repositories, live T-021/T-022.

## Risks & gotchas

- **FX call explosion**: naive implementation calls `convert` on every (day, account) pair. Horizon=1825 (5 years) × 10 accounts = 18 250 calls. Pre-fetch the per-currency rate once, apply pure arithmetic in the inner loop.
- **FX for forward dates**: `services.fx.get_rate(conn, http, today, ...)` is correct. Calling with `d` for d in future would try to fetch a non-existent remote rate, trigger the fallback every day, and spam the log. Explicitly use `today`.
- **Historical vs latest FX**: ADR-0006 says historical rates for historical conversion. The forecast is forward-looking → latest rate. Do not conflate.
- **De-dup discipline (same as T-023)**: key is `(recurring_rule_id, occurrence_date)`. Dedup must happen before event bucketing or Rent is paid twice in the forecast.
- **Direction lookup**: pre-fetch the `cat_id → direction` map once; do not query inside the loop.
- **Rounding drift**: aggregating `base_minor` by summing `AccountBalancePoint.base_minor` is correct only if each per-account conversion is rounded independently; summing in `Decimal` then rounding once would give slightly different totals. Pick one and document — the plan chooses per-account rounding then integer sum, which is cheaper and matches how a user reads the per-account column.
- **Snapshot staleness**: the forecast is pure w.r.t. the DB snapshot. Routers must call `forecast(...)` on every page load (and HTMX swap on `forecast-stale` trigger per ADR-0015).
- **Timezone**: `today` is a `date`. Router responsibility to compute `today` in display timezone (`Europe/Warsaw`, ADR-0007) and pass it in.
- **Transit source=dest**: pathological. Should be rejected at validation; defensively check `source != dest` and raise.

## Handoff notes

Phase 3 consumers:

- **Forecast router (T-037)**:
  - `GET /forecast?horizon_days=N` → `forecast(conn, http, today, horizon_days, config.base_currency)`.
  - Response renders a Plotly chart (per-account line + totals line) plus a table of `days[::7]` (weekly ticks). HTMX re-triggers via `HX-Trigger: forecast-stale` from any mutating router (T-031..T-036) that touches planned, recurring, or account state.
- **Home dashboard (T-039)**: `forecast(..., horizon_days=90)` for a mini-chart tile.
- **Analytics router (T-038)** does **not** call the forecast; it reads actuals only.
