# T-R40 — `GET /today/afford?amount=`

- **Phase**: 4 — Backend
- **Parallel-safe**: yes.
- **Depends on**: T-R10.
- **References**: ADR-0056 §3, ADR-0041, ADR-0039.

## Context

Today's "can I afford it?" live preview. Takes an amount in minor units, returns the recomputed per-day figure given the current anchor window, plus the signed delta vs the current left-per-day baseline and the recomputed pace tag. The endpoint is a pure read; no DB write.

## Deliverables

- `src/budget_planner/services/today.py`:

  ```python
  @dataclass(frozen=True)
  class AffordResult:
      per_day_minor: int
      delta_minor: int
      pace_tag: Literal["on_track", "tight", "overdue"]
      days_left: int

  def afford(conn: Connection, today: date, amount_minor: int) -> AffordResult: ...
  ```

  Reuses `services.budget.month_summary(conn, today)` for the baseline (`left_daily_spend_minor`, `days_until_next_income`). The afford math: `(remaining_minor - amount_minor) / max(days_left, 1)`.
- `src/budget_planner/web/routers/today.py` gains:
  - `GET /today/afford?amount=<int>` returns a Jinja fragment with the recomputed per-day line + delta chip.
  - Validation: `amount` is a non-negative integer (minor units); otherwise 422.
- `templates/today/_afford_result.html` fragment:
  ```html
  <span class="afford__per-day">{{ amount(result.per_day_minor, settings.base_currency, size="hero") }}</span>
  <span class="afford__delta amt--{{ 'expense' if result.delta_minor < 0 else 'income' }}">
    {{ amount(result.delta_minor, settings.base_currency, direction=…) }}
  </span>
  {{ pace_tag(result.pace_tag) }}
  ```
- Unit tests under `tests/unit/services/test_today_afford.py`: positive amount, zero amount, amount > remaining, zero days left, anchor fallback (no income anchor configured).
- Integration test under `tests/integration/web/test_today.py::test_afford_endpoint` covers 200 OK + fragment shape + 422 on invalid input.

## Acceptance criteria

- `AffordResult.per_day_minor >= 0`; the result never goes negative — it clamps at zero with pace tag `overdue`.
- Coverage ≥ 90 % on the new module.
- `GET /today/afford?amount=10000` from a seeded dev DB returns a fragment containing an `.afford__per-day` span with the expected value.
- `GET /today/afford?amount=-1` returns 422.
- No DB write (verified by audit-log count before/after).

## Validation hook

```sh
pytest tests/unit/services/test_today_afford.py tests/integration/web/test_today.py::test_afford_endpoint && \
  curl -sS "http://localhost:8000/today/afford?amount=10000" | grep "afford__per-day"
```

## Risks & gotchas

- Anchor fallback: when the income anchor is unset or stale, `month_summary` falls back to end-of-month (ADR-0041). Reuse the fallback as-is; do not reinvent inside `afford`.
- Multi-currency: the endpoint accepts amounts in the **base currency** (minor units). The input UI on Today constrains to base currency; this is documented in the task PR body.
- Debounce + preview: the HTMX trigger `keyup changed delay:200ms` throttles input; the endpoint must stay idempotent and side-effect-free.

## Handoff notes

- T-R25 (Today screen) consumes this endpoint via HTMX. Do not import service functions in the template — go through the router.
- `services.today.afford` is pure — reuse in any future "simulate a transaction" surface.
