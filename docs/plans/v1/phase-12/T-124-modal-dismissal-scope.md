# T-124 [P] Modal dismissal scope + amount `,`/`.` regression test

> Depends on: T-116, [ADR-0040](../../../adr/0040-modal-dismissal-scope.md). Parallel-safe with T-121, T-122, T-123.

## Scope

Two surgical web-layer changes bundled because the bug they both unblock is "amount input kills the modal".

### Fix 1 — Modal dismissal scope (ADR-0040)

- `templates/base.html` script block: rewrite the `htmx:afterRequest` handler so the reset-and-close path fires only when **all three** conditions hold:
  1. `detail.xhr.status ∈ [200, 300)`.
  2. `evt.target` is itself a `<form[data-reset-on-submit]>` (not a descendant).
  3. `detail.requestConfig.verb` is `"post"`, `"put"`, or `"delete"` (case-insensitive).
- The 422-shouldSwap branch above it stays unchanged.

### Fix 2 — Amount decimal separator regression pin

Existing `numeric-input.js` regex already allows both `,` and `.` (one occurrence, up to two fractional digits). This task pins the behaviour against future regression by adding tests, not code.

- `tests/integration/web/test_forms.py` (or `tests/unit/web/test_numeric_input.py` if a JS test harness exists; otherwise a server-side integration test is sufficient):
  - `POST /transactions` with `amount=12,34` — server accepts and persists `1234` minor units (per `domain.money.to_minor_units` handling both separators).
  - `POST /transactions` with `amount=12.34` — same result.
  - `POST /transactions` with `amount=12.345` — server rejects with 422 (two fractional digits max).

### Tests

- `tests/integration/web/test_forms.py`:
  - `test_amount_sidebar_request_does_not_dismiss_slide_over`:
    - Open `/transactions/new`, extract CSRF-free form fragment (project has no CSRF layer today).
    - Simulate `GET /transactions/_limit_preview?...` with the same form field set — assert the response is 200 (fragment with `#limit-preview` body), *and* assert that `#modal-root` is unaffected (test harness renders the slide-over markup directly then asserts the handler scope by invoking the JS via Playwright, or by unit-testing the handler via a tiny JSDOM harness — pick whichever already exists in the suite).
  - `test_form_submit_still_dismisses_slide_over`:
    - `POST /transactions` with a valid payload; assert the response does **not** carry the slide-over markup and does carry a `data-reset-on-submit` form marker in the response fragments.
  - `test_amount_accepts_comma_or_dot` (per Fix 2 above).
- `tests/visual/` — no new baselines; the dismissal behaviour is JS-driven and unobservable in a static screenshot. Playwright journey test may serve as the strongest signal.

### `frontend-visual-audit`

- Not applicable to this task (no static markup changes beyond script contents inside `base.html`).

## Acceptance

- Typing in the New-transaction amount field no longer dismisses the slide-over.
- Submitting the New-transaction form still dismisses the slide-over.
- `12,34` and `12.34` both land `1234` minor units; `12.345` is rejected.
- `just ci` green.

## Non-goals

- Converting the side-effect `/transactions/_limit_preview` request away from the input (would complicate `hx-include`).
- Any change to other inputs' HTMX wiring.
