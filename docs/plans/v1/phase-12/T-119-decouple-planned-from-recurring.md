# T-119 [S] Decouple planned log from recurring + introduce upcoming / income-anchor services

> Depends on: T-117. Blocks: T-120, T-121.

## Scope

Service refactors + light router update. No new DB schema.

### `services/planned.py`

- Drop the virtual-recurring branch from `list_planned`. The function now returns only persisted `planned_transactions` rows, filtered + sorted as before.
- `PlannedKind` literal collapses to the single value `"persisted"`. Keep the field so templates do not need to re-key, but drop the virtual-row construction code.
- `_virtual_to_view` + `recurring_svc` import removed.
- `next_planned_for_category` is removed. Callers migrate to `services.income.next_anchor_date` (see below).

### `services/income.py` (new)

```python
def next_anchor_date(
    conn: sqlite3.Connection,
    category_id: int,
    after: dt.date,
    *,
    horizon_days: int = 400,
) -> dt.date | None:
    """Earliest effective date strictly after `after` within the horizon
    for a planned one-off *or* an active recurring rule whose
    `next_due` matches the anchor category. Override on `next_due`
    applied via `recurring_repo.list_overrides` lookup. Returns `None`
    when nothing matches.
    """
```

- Composes `planned_repo.list_filtered(..., promoted=False, category_ids=(category_id,))` + `recurring_repo.list_rules(active_only=True)` filtered client-side on `category_id`.
- Pure (DB only); no `today` dependency — caller injects `after` per ADR-0007.

### `services/upcoming.py` (new)

```python
@dataclass(frozen=True, slots=True)
class UpcomingItem:
    kind: Literal["planned", "recurring"]
    effective_date: dt.date
    account_id: int
    dest_account_id: int | None
    category_id: int
    amount_minor: int
    description: str
    is_overdue: bool
    # planned-only fields:
    planned_id: int | None
    # recurring-only fields:
    rule_id: int | None
    override_present: bool


def list_upcoming(
    conn: sqlite3.Connection,
    *,
    today: dt.date,
    window_days: int | None,
) -> tuple[UpcomingItem, ...]:
    """Union of persisted planned (not promoted, within window) and
    active recurring rules whose `next_due` falls within window.
    `window_days=None` ⇒ unbounded tail (used by the "All" range).
    Sorted by effective_date, ties broken by kind='planned' first.
    """
```

- `is_overdue = (kind == 'planned' and effective_date < today)`.
- Recurring overrides on `next_due`: looked up via `recurring_repo.list_overrides(rule.id)` — if an override with `state=overridden` targets `rule.next_due`, its `amount_override` / `description_override` / `date_override` are applied; `state=skipped` → the row is excluded. If `date_override` moves the effective date outside the window, the row is excluded.

### Router changes

- `web/routers/home.py` — the Upcoming fragment switches from `services.planned.list_planned` to `services.upcoming.list_upcoming`. Template hydration shifts into a small helper (see T-121) that renders different action buttons per `kind`.
- `web/routers/ledger.py`:
  - `_planned_rows` continues to call `services.planned.list_planned` (which is now persisted-only). No behavioural change inside the Planned tab beyond "virtual rows disappear".
  - `_hydrate_recurring_rows` now reads `rule.next_due` directly rather than aliasing `start_date` to `next_due` (`web/routers/ledger.py:144` fix).
- `services/budget.py` imports `services.income` instead of `services.planned.next_planned_for_category` (`month_summary` reference stays shape-equivalent).

### Tests

- `tests/unit/services/test_planned.py` — update: assert no virtual rows ever appear in `list_planned`. Delete the dedup + override tests that targeted the virtualisation path (migrated to T-121 upcoming tests).
- `tests/unit/services/test_upcoming.py` (new) — planned-only; recurring-only; mixed; override merge; override moves date outside window → excluded; skipped override excluded; `window_days=None` returns everything into the future.
- `tests/unit/services/test_income.py` (new) — planned-only hit; recurring-only hit; both candidates, recurring earlier; both candidates, planned earlier; no match returns `None`; override that moves recurring date is honoured.
- `tests/unit/services/test_budget.py` — `month_summary` continues to find the anchor date (test re-pointed from `services.planned.next_planned_for_category` to `services.income.next_anchor_date`). Values unchanged.
- `tests/integration/web/test_home.py` — Upcoming fragment contains both planned and recurring rows for an in-window case; recurring rows carry `data-kind="recurring"`.
- `tests/integration/web/test_ledger.py` — Planned tab excludes virtual rows for a seeded active rule (regression pin).

## Acceptance

- Full suite green including the budget / forecast suites (forecast is unaffected — it continues to use `services.recurring.expand`).
- No regression on `MonthSummary.left_daily_spend_minor` values on existing budget fixtures (confirmed by `test_budget.py` fixtures staying green).
- Coverage ≥ 90%.

## Non-goals

- Committed-in-window math (T-120).
- Overview template changes (T-121).
- Recurring row action buttons (T-122).
