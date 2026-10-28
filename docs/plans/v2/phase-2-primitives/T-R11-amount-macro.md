# T-R11 — `amount` macro

- **Phase**: 2 — Primitives
- **Parallel-safe**: yes (one macro per task).
- **Depends on**: T-R10.
- **References**: ADR-0053 §1 (Amount row), ADR-0048, handoff `docs/application_redesign_handoff/docs/04-components.md`.

## Context

Every money value in the app renders through this macro: Plex Mono tabular numerals, sign based on direction, currency as a muted 0.72em suffix, ƒ chip for formula-derived amounts, FX hint tooltip for cross-currency values. This is the single highest-leverage primitive — screens become shallow if this is right.

## Deliverables

- `src/budget_planner/web/templates/_partials/components/_amount.html` with:

  ```jinja
  {% macro amount(minor, currency, direction=None, formula=False, fx_hint=None, size="base") %}
    <span class="amt amt--{{ size }}{% if direction %} amt--{{ direction }}{% endif %}"
          {% if fx_hint %}data-fx-hint="{{ fx_hint.base_minor }} {{ fx_hint.base_currency }} · 1 {{ currency }} = {{ fx_hint.rate }} ({{ fx_hint.as_of }})"{% endif %}>
      <span class="amt__sign">{{ _amount_sign(direction) }}</span>
      <span class="amt__value">{{ _format_minor(minor, currency) }}</span>
      <span class="amt__currency">{{ currency }}</span>
      {% if formula %}<span class="amt__formula" aria-label="formula-derived">ƒ</span>{% endif %}
    </span>
  {% endmacro %}
  ```

- Helper functions in `src/budget_planner/web/jinja_filters.py`:
  - `_amount_sign(direction)` returns `−`, `+`, or empty.
  - `_format_minor(minor, currency)` formats to the currency's minor-unit convention (e.g. PLN two decimals, JPY zero).
- `static/css/components/amount.css` with Plex Mono + tabular + colour variants.
- Unit tests under `tests/unit/web/test_amount_macro.py` covering: expense sign, income sign, transit no sign, formula chip, FX hint data attribute, JPY zero-decimal.
- Representative inputs rendered on `/dev/components#amount`.

## Acceptance criteria

- `pytest tests/unit/web/test_amount_macro.py` green.
- `/dev/components#amount` renders ten variants (expense, income, transit, adjust, with ƒ, with FX hint, JPY, large value, zero, over-budget negative).
- Visual-regression baseline captured at D/T/M; delta zero after T-R24.
- `grep "<span.*amount\|__amount" src/budget_planner/web/templates/**/*.html | grep -v _amount.html` returns zero (confirms the macro is the only producer).

## Validation hook

```sh
pytest tests/unit/web/test_amount_macro.py && \
  curl -sS http://localhost:8000/dev/components | grep -c "amt__value" | awk '{ exit $1 < 10 }'
```

## Risks & gotchas

- Browsers render Plex Mono tabular only when `font-variant-numeric: tabular-nums` is on the containing element; set it on `.amt__value`, not the parent `.amt`.
- The currency suffix at 0.72em must not break tabular alignment — align with `baseline` not `middle`.
- FX hint data attribute is read by the tooltip CSS; avoid pre-formatting the string (keep the structured data in `data-*`).

## Handoff notes

- Every screen task (T-R25..T-R39) imports and uses this macro. Any screen test that asserts the amount shape must look for `.amt__value` + `.amt__currency` instead of raw text content.
