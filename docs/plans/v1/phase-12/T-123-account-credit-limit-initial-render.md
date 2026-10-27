# T-123 [P] Account form: credit-limit initial-render visibility bug

> Depends on: T-116. Parallel-safe with T-121, T-122, T-124.

## Scope

One-file surgical fix. No service / schema change.

### Bug

`partials/accounts/_form.html` renders the credit-limit field with `hidden aria-hidden="true"` + `disabled` when `account is None or account.is_liability is False`. The inline `<script>` at the bottom re-synchronises on `change` and on initial load via `sync()`. In practice the field is visible on first open of the New-account slide-over.

Root cause hypothesis (confirm via inspector in impl):

1. **HTMX swap stripping the `<script>`** — HTMX executes inline scripts in swapped content, but when the form fragment is nested inside the shared `partials/_slideover.html` (which wraps the include in `<div class="slide-over__body">`), `document.currentScript.previousElementSibling` resolves to the slide-over body element, not the `<form>`. `querySelector` from the wrong root returns `null`, early-return skips the sync.
2. **CSS override** — a theme rule may override `[hidden]` display behaviour on `.account-form__limit`. Low-likelihood but inspector-confirmable.

### Fix

- Rewrite the sync script to find the form via `data-account-form` attribute on the form root instead of `previousElementSibling` (DOM-position-independent). Make the script idempotent — safe to execute multiple times after HTMX swaps or `htmx:afterSwap`.
- Call `sync()` on `DOMContentLoaded` **and** on `htmx:afterSwap` scoped to the form element — belt + suspenders.
- As a complementary guard, in `_form.html` include the following at the top of the script:
  ```js
  var form = document.querySelector("[data-account-form]");
  if (!form) return;
  ```
- Add `data-account-form` to the `<form>` tag.
- Confirm the initial-render markup contract: `hidden aria-hidden="true"` + `disabled` when either `account is None` *or* `account.is_liability` is falsy; same Jinja condition drives all three attributes.

### Tests

- `tests/integration/web/test_accounts.py`:
  - `GET /accounts/new` — assert the credit-limit `<label>` carries `hidden` + `aria-hidden="true"` and its input carries `disabled`.
  - `GET /accounts/{id}/edit` on a liability account — all three attributes absent.
  - `GET /accounts/{id}/edit` on a non-liability account — all three attributes present.
- Playwright journey test extension (`tests/e2e/test_credit_card_journey.py` or a new focused test): opens the New-account slide-over, confirms the credit-limit field is not visible, toggles liability on, confirms it becomes visible, toggles off, confirms it hides again.

### `frontend-visual-audit`

- `/accounts` at 1440 / 1024 / 375 — open the New-account slide-over, screenshot both toggle states.

## Acceptance

- Credit-limit field never visible on the New-account slide-over when "Credit (liability)" is off.
- Toggling the liability checkbox flips the field visibility + disabled state in lockstep (ADR-0030 §6 contract).
- `just ci` + visual sweep green.

## Non-goals

- Any ADR-0024 scope change — label text is already "Credit (liability)" (set in T-111).
- Changes to the credit-limit server-side validation.
