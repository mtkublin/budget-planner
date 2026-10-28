# T-R68 — `sparkline()` helper + Accounts trend column

- **Phase**: 5 — Charts
- **Sequential**: after T-R47, T-R34.
- **Depends on**: T-R47 (`charts.py`), T-R34 (Accounts page).
- **References**: ADR-0054 §Follow-ups, handoff §Accounts (sparkline shown on screen 1j).

## Context

Each Accounts table row shows a 30-day balance trend as an inline sparkline. The handoff mock renders a thin stroke with no axes, filling about 80 × 20 px. Server computes points; `charts.py` returns geometry; the template emits inline SVG.

## Deliverables

- `src/budget_planner/web/charts.py` gains:
  ```python
  @dataclass(frozen=True)
  class Sparkline:
      path_d: str
      viewbox: str

  def sparkline(points: Sequence[float], width: int = 80, height: int = 20) -> Sparkline: ...
  ```
  Normalises points to the given box; no axes; monotonic rising/falling colour determined by first vs last.
- `services.accounts.trend(conn, account_id, days=30) -> tuple[float, ...]` returns daily end-of-day derived balances in the account's own currency (fast via `derive_balance` cached per date).
- `templates/accounts/_row.html` renders:
  ```html
  <svg class="sparkline sparkline--{{ 'up' if trend.rising else 'down' }}" viewBox="{{ spark.viewbox }}" width="80" height="20">
    <path d="{{ spark.path_d }}" fill="none" stroke="currentColor" stroke-width="1.5"/>
  </svg>
  ```
  Colour: `--income` if rising, `--expense` if falling, `--mute` if flat.
- Unit tests for `sparkline()`: single point, two points, flat line, mixed up/down.
- Integration test: Accounts row carries a non-empty `<svg class="sparkline">`.

## Acceptance criteria

- Every live Accounts row renders a sparkline; empty balance history renders an em-dash via `data-empty`.
- Sparkline colour matches the trend direction; `prefers-reduced-motion` is irrelevant (no animation).
- `/accounts` renders in under 300 ms for 20 accounts (sparkline compute amortised; cache the per-account daily series per request).
- Visual-regression baseline at D/T/M matches handoff `desktop-1j-accounts.png` within tolerance.

## Validation hook

```sh
pytest tests/unit/web/test_sparkline.py tests/integration/web/test_accounts.py::test_sparkline_renders && \
  just test-visual --filter accounts-sparkline
```

## Risks & gotchas

- Daily balance derivation runs over the full transaction history by default. Cache per request or compute incrementally from the latest snapshot.
- Multi-currency: sparkline is in the account's own currency; do not convert to base currency on the row (base conversion is the net-worth hero's job).
- SVG stroke `currentColor` lets the trend-direction class style it; do not inline `stroke="…"`.

## Handoff notes

- T-R34 Accounts page is the primary consumer. The `_row.html` fragment lands in that task; this task extends it with the sparkline cell.
