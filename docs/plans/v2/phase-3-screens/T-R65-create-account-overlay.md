# T-R65 — Create account overlay reskin

- **Phase**: 3 — Screens
- **Sequential**: after T-R24, T-R34.
- **Depends on**: T-R34 (Accounts page), T-R24 (primitives).
- **References**: handoff screen 2c, ADR-0024, ADR-0030.

## Context

Phase 11 shipped the Create account slide-over (ADR-0030). This task reskins it to the Rising Dough palette + primitive set without changing the server behaviour. Immutable currency, conditional credit-limit, close affordance all stay.

## Deliverables

- `src/budget_planner/web/templates/accounts/_create_form.html` rebuilt against:
  - `_slideover.html` wrapper (close × present).
  - `period_header`-style section title.
  - `combobox` for currency (ISO 4217, existing).
  - Toggle for liability (ADR-0024); credit-limit field hidden + `aria-hidden` + `disabled` when toggle off (ADR-0030 §6).
  - Primary button via `button(variant="primary")`.
- No change to `POST /accounts` route.
- Visual-regression baselines at D/T/M.
- Integration test asserts the credit-limit field is hidden on initial render when the toggle is off (regression guard for the T-123 bug noted in ADR-0030).

## Acceptance criteria

- Overlay opens from Accounts page `+ New account` + from the row ⋯ Edit (T-R67).
- Clear-on-save behaviour (ADR-0030 §5) still fires on 2xx; HTMX dismisses the overlay.
- `frontend-visual-audit` on the Accounts page with the overlay open returns zero findings.
- Visual-regression matches handoff `overlay-2c-create-account.png` within tolerance.

## Validation hook

```sh
pytest tests/integration/web/test_accounts.py::test_create_account_overlay && \
  just test-visual --filter create-account
```

## Risks & gotchas

- Conditional credit-limit must stay in sync at three moments: initial render, toggle change, 422 re-render (ADR-0030 §6). The regression test must cover all three.
- Currency combobox is immutable after creation — the Edit path (T-R67) must pass `readonly` on the field.

## Handoff notes

- T-R67 Accounts ⋯ menu reuses this overlay for Edit; pre-fills values from the existing account row.
