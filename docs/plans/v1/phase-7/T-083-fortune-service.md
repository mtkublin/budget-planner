# T-083 — Fortune Service

> Phase 7 — Liability Accounts. Status: pending.

## Purpose

Extract the fortune aggregation that is currently duplicated across `web/routers/home.py` and `web/routers/accounts.py` into a single pure service, and extend it to compute the Assets / Liabilities / Net worth split. `derive_balance`, `signed_legs`, and ADR-0008 arithmetic are untouched.

## Inputs / prerequisites

- Upstream tasks: T-082 (`Account.is_liability` populated).
- Binding standards:
  - [`ADR-0024`](../../../adr/0024-liability-accounts-and-credit-limit.md) — the aggregation rule.
  - [`ADR-0008`](../../../adr/0008-transaction-amount-sign-and-direction.md) — single arithmetic authority; this service composes `derive_balance` but does not re-implement any signing logic.
  - [`ADR-0021`](../../../adr/0021-functional-style-no-oop.md) — pure functions, frozen DTOs.
  - [`ADR-0006`](../../../adr/0006-multi-currency-model.md) — per-currency buckets; full FX conversion is still T-032 territory, not this task.
- Adjacent precedent: `src/budget_planner/web/routers/home.py:37-44` and `src/budget_planner/web/routers/accounts.py:41-59` carry the current duplicated aggregator.

## Deliverables

New file: `src/budget_planner/services/fortune.py`.

Shape:

```python
from dataclasses import dataclass
import sqlite3

from budget_planner.config import Settings
from budget_planner.repositories import accounts as accounts_repo
from budget_planner.services import balance as balance_service


@dataclass(frozen=True, slots=True)
class FortuneTotals:
    assets_by_ccy: dict[str, int]
    liabilities_by_ccy: dict[str, int]  # positive magnitudes (|balance|) per currency
    net_by_ccy: dict[str, int]
    assets_base: int
    liabilities_base: int
    net_base: int


def compute_fortune(conn: sqlite3.Connection, settings: Settings) -> FortuneTotals: ...
```

Algorithm (one pass over `accounts_repo.list_all(conn)`):

```
assets_by_ccy, liabilities_by_ccy, net_by_ccy = {}, {}, {}
for a in accounts_repo.list_all(conn):
    bal = balance_service.derive_balance(conn, a.id)
    if a.is_liability:
        liabilities_by_ccy[a.currency] = liabilities_by_ccy.get(a.currency, 0) + abs(bal)
    else:
        assets_by_ccy[a.currency] = assets_by_ccy.get(a.currency, 0) + bal
    net_by_ccy[a.currency] = net_by_ccy.get(a.currency, 0) + bal  # negative balance already subtracts
# base-currency selection mirrors the current single-sum behaviour:
assets_base      = assets_by_ccy.get(settings.base_currency, 0)
liabilities_base = liabilities_by_ccy.get(settings.base_currency, 0)
net_base         = net_by_ccy.get(settings.base_currency, 0)
```

Router changes:

- `web/routers/home.py` — replace the inline aggregation with a call into `compute_fortune(conn, settings)`. The existing `fortune_base` field becomes `fortune.net_base`; the template picks up the full `FortuneTotals` under a `fortune` key (T-084 extends the template).
- `web/routers/accounts.py` `_hydrate(...)` — same substitution. The function still returns `cards` + the fortune block; wire the `FortuneTotals` through the template context.

New tests under `tests/unit/services/test_fortune.py`:

- `test_asset_only_no_liabilities` — assets add; liabilities = 0; net = assets.
- `test_liability_only` — one credit card at `-500 PLN`; `assets = 0`, `liabilities_by_ccy[PLN] = 500`, `net = -500`.
- `test_mixed_single_currency` — bank at `+1000`, credit at `-200` → `assets = 1000`, `liabilities = 200`, `net = 800`.
- `test_multi_currency_buckets` — PLN + EUR accounts; buckets stay per-currency; base selection matches `settings.base_currency`.
- `test_soft_deleted_account_excluded` — `accounts_repo.list_all` already excludes soft-deleted rows; add a case that proves the aggregator does not re-include them.
- `test_invariant_net_eq_assets_minus_liabilities` — property style; parametrise 10 cases, assert `net_base == assets_base - liabilities_base`.
- `test_over_limit_balance_included` — a credit-card balance below `-credit_limit_minor` still contributes `|balance|` to liabilities (there is no clamp).
- `test_zero_balance_account_is_included_as_zero` — asset with no transactions, `opening_balance = 0` → contributes 0 to all buckets but is counted.

Integration-level touch under `tests/integration/web/test_home.py` and `tests/integration/web/test_accounts.py`: the existing `fortune_base` assertions migrate to `fortune.net_base`; one new assertion that the three figures render in the template (string match on the labels is sufficient at this layer — DOM assertions live in T-084).

## Step-by-step

1. **Create the service module.** Keep it tiny — one dataclass, one function. Add module-level `__all__ = ["FortuneTotals", "compute_fortune"]`.
2. **Call site 1: `home.py`.** Replace lines 37-44 with the service call. Pass `fortune=fortune` into the template context (and keep `fortune_base = fortune.net_base` as a compat alias if the template still needs it; T-084 will remove the alias when it switches the DOM to the three-line block).
3. **Call site 2: `accounts.py`.** Replace lines 41-59 with the service call. The `totals_by_ccy` key currently returned becomes `fortune.net_by_ccy`.
4. **No DOM change in this task.** Templates may continue to render a single number via `fortune.net_base` — the three-line split is the T-084 deliverable. The point of T-083 is to land the service + migrate both routers in a tight, test-covered PR before the UI follows.
5. **Tests.** Add the new unit tests. Update any existing router tests that assert the exact template context keys to accept the `fortune` block.

## Validation / acceptance

- `pytest tests/unit/services/test_fortune.py -q` — all new tests pass.
- `pytest tests/integration/web/test_home.py tests/integration/web/test_accounts.py -q` — green with migrated assertions.
- `pytest --cov=src/budget_planner/services/fortune --cov-fail-under=95` — ≥ 95% branch coverage.
- `grep -nE "derive_balance|signed_legs" src/budget_planner/services/fortune.py` — one match (the `derive_balance` call), zero re-implementations of signing.
- `grep -nE "totals_by_ccy" src/budget_planner/web/routers/{home,accounts}.py` — zero matches after the migration.
- `just ci` green.

## Risks & gotchas

- **Base-currency semantics.** Current behaviour selects only accounts whose currency equals `settings.base_currency` for the single-number fortune. The new `*_base` figures preserve that behaviour verbatim. Full cross-currency aggregation stays deferred (T-032 scope).
- **Negative balance on an asset account.** An overdrawn checking account naturally produces a negative asset bucket entry. That is correct — the asset bucket is `Σ balance`, not `Σ max(balance, 0)`. Do not clamp.
- **Over-limit credit cards.** A credit card with `balance = -12_000` and `credit_limit_minor = 10_000` contributes `|balance| = 12_000` to liabilities. The limit is a UX concern (T-084), not an arithmetic one.
- **Pure function discipline.** The service reads `conn` + `settings`; it does not read the clock, filesystem, or env. Keep it that way so T-095-style future metrics compose cleanly.
- **Dict ordering.** `dict` preserves insertion order; aggregation ordering reflects `accounts_repo.list_all` ordering. Templates that iterate for display should sort explicitly (currency code ascending). The service does **not** sort — that is a presentation choice.

## Handoff notes

- Hand-off to T-084: templates read `fortune.assets_base`, `fortune.liabilities_base`, `fortune.net_base` for the headline block and `fortune.{assets,liabilities,net}_by_ccy` for the per-currency breakdown.
- Hand-off to T-085: the service is a convenient single call site for the transaction form preview — the form can call `compute_fortune(conn, settings)` + a hypothetical `derive_balance` delta on the chosen account to show the projected utilization without plumbing new types.
- Commit shape: `feat(T-083): fortune service with assets/liabilities/net split (ADR-0024)`.
