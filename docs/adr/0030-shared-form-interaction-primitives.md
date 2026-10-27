# ADR-0030 — Shared Form Interaction Primitives

**Status**: accepted (2026-10-27)

**Context**

Field use after Phase 7/8/9 surfaces a cluster of inconsistent form behaviours that compound into real friction:

- The transaction form `operation_date` input ships empty — every entry needs a manual date pick even though the overwhelmingly common case is "today".
- The `amount` input is `<input type="text">` with `inputmode="decimal"` only; nothing stops a user from pasting / typing letters, currency symbols, or stray whitespace. Server-side validation catches it but at the cost of a round-trip + inline 422.
- `category_id`, `account_id`, `dest_account_id` on the transaction form, `account_id` + `category_id` on the planned form, and all three on the recurring form, are plain `<select>` dropdowns. With more than ~15 categories or 5+ accounts they are slow to scan; type-to-filter is a browser-native expectation that the current markup does not provide. Same for the account currency field, which is a free-text `<input maxlength="3">` with no completion — the user has to remember exact ISO 4217 codes.
- The Accounts "+ New account" affordance renders the form **inline** on `/accounts` (into `#account-form-slot`) rather than as a slide-over. The Reconcile dialog is a `<div role="dialog">` modal but has **no close button** — the only way out is to submit, press Esc, or click the backdrop. These are inconsistent with the Phase 6 slide-over + Quick-add FAB pattern established by [ADR-0023](0023-ux-redesign-information-architecture.md) + [T-069](../plans/v1/phase-6/T-069-quick-add-fab.md), which gives every slide-over a visible close affordance via `_partials/slide_over_header.html`.
- After submitting the Accounts form the inputs stay filled, which is wrong for a form opened repeatedly to create multiple records.
- The Accounts form shows the "Credit limit" input unconditionally and keeps it visible even when the liability checkbox is unchecked (the inline script hides it, but the markup still ships it and the initial render on a fresh form keeps it visible as a disabled affordance that confuses the eye). The label text "Credit card (liability)" also mis-scopes the feature — the account model and ADR-0024 are about liability accounts generally (credit cards, overdraft lines, buy-now-pay-later, short-term loans), not just credit cards.

Rather than fix each form individually, we extract a small set of **shared interaction primitives** that every create / edit surface in the app composes from. One decision, applied uniformly, replaces N bespoke fixes.

**Decision**

1. **Date inputs default to today in `display_timezone`.** Any `<input type="date">` on a create form (not edit) renders with `value="{{ today|date_fmt }}"`, where `today` is computed in `settings.display_timezone` (ADR-0007) by the router. Edit forms keep the existing stored value. Scope: transaction / planned / recurring / reconcile / budget-rule create forms. Implementation: Jinja global `today_local()` wired at app startup, consumed by every create partial.

2. **Amount inputs restrict to digit + decimal separator only.** `<input type="text" name="amount" inputmode="decimal">` remains the markup (preserves mobile keyboards) and gains:
   - A client-side `beforeinput` listener in a new shared `static/js/numeric-input.js` (~30 lines, vanilla) that cancels the event when the proposed value does not match `^\d*([.,]\d{0,2})?$` (two decimal places maximum, locale-tolerant comma or dot). Paste events are filtered through the same regex.
   - Server-side validation stays exactly as it is — the client script is UX sugar, not a security boundary.
   - Applied to every amount field in the app: transaction, planned, recurring, reconcile actual balance, account opening balance, account credit limit, budget rule amount.
   - The script is loaded once in `base.html`; forms opt in via `data-numeric` on the `<input>` element.

3. **Id-lookup selects become filterable comboboxes.** Any `<select>` whose options are "pick an existing live row" (category, account, dest account, currency ISO code) is replaced by a shared `_partials/combobox.html` macro:
   - Markup: `<label><span>{label}</span><input type="text" role="combobox" aria-expanded="false" aria-controls="{listbox-id}" aria-autocomplete="list" autocomplete="off"><input type="hidden" name="{field}"><ul role="listbox" id="{listbox-id}" hidden>…options…</ul></label>`.
   - Behaviour (new `static/js/combobox.js`, ~80 lines, vanilla): typing in the visible input filters the listbox options by **case-insensitive substring match on the option label**; `↓` / `↑` move highlight; `Enter` / click selects, writing the option id to the hidden input + the label to the visible input + closing the listbox; `Esc` closes without selecting; blur outside closes. ARIA pattern: WAI-ARIA 1.2 combobox (list autocomplete, with manual selection).
   - Options render server-side with `data-value` + visible label. No new endpoint, no XHR per keystroke — the full list is in the DOM.
   - **Currency combobox** sources options from a new `domain.money.ISO_4217_CURRENCIES: tuple[str, ...]` constant (initial scope: the ~180 ISO 4217 "active" codes). Validation at the service boundary unchanged.
   - Scope: transaction form (category, account, dest), planned form (category, account, dest), recurring form (category, account, dest), account form (currency), budget rule modal (category).

4. **Every modal / slide-over has a visible close control.** The `_partials/slide_over_header.html` macro already renders a `.slide-over__close` button; it becomes mandatory on every slide-over wrapper. The Reconcile dialog (`partials/accounts/_reconcile_modal.html`) migrates from its bespoke modal shell to the shared `partials/_slideover.html` wrapper so it inherits the close button, Esc handling, backdrop click dismissal, and overlay-stack cooperation (ADR-0023 §overlay stack). No new modal pattern — the slide-over is already the standard; this ADR removes the exception.

5. **Submit clears create forms; edit forms stay bound.** Create forms (no `txn`/`account`/`rule` entity bound in the Jinja context) listen for `htmx:afterRequest` and, on a successful 2xx response, reset their inputs to the initial state and move focus back to the first field. The reset also re-fires the "default date = today" assignment. Implementation: `data-reset-on-submit` attribute on the `<form>` + a 5-line listener in `base.html`'s existing scripts section. Edit forms do not carry the attribute. This mirrors the slide-over lifecycle: creating many planned payments or many accounts in sequence should not require manually clearing each field.

6. **Conditional fields are hidden at both the markup and the a11y layer.** Fields that depend on a sibling checkbox (today only: Account's "Credit limit") render with `hidden` + `aria-hidden="true"` + the input `disabled` when the trigger is off; the inline toggle script flips all three attributes in lockstep. Hidden-but-enabled inputs leak into form submission on some browsers (Firefox) — `disabled` is the belt to the `hidden` suspenders. The checkbox label becomes `"Credit (liability)"`, dropping the "card" scope mistake.

**Consequences**

Pros:

- One place to fix each primitive. Future forms get type-to-filter selects, digit-only amounts, close affordance, and clear-on-save by composing the shared partial — no per-form JS, no per-form Jinja.
- Server-side contracts stay identical. The combobox hidden input emits the same `category_id=…` as the current `<select>`; the digit-only script does not change what the server sees; the `"Credit (liability)"` relabel does not touch the `is_liability` payload.
- Removes one real UX cliff (missing close button on Reconcile) and one scope mislabel (liability ≠ credit card) called out by ADR-0024.
- The combobox pattern unblocks future scale: once the user has 50+ categories or 10+ accounts, plain selects become unusable; this ADR future-proofs that.

Cons / costs:

- Two new static JS files (`numeric-input.js` ~30 lines + `combobox.js` ~80 lines) and one new Jinja macro (`combobox.html`). Added to `base.html`'s existing script block. Within the "no framework" budget set by ADR-0023.
- Visual-regression baselines regenerate for every page carrying a replaced select or modal. Expected churn: transaction / planned / recurring / account forms + reconcile modal. Baselines refreshed in the T-110 landing commit.
- Keyboard semantics shift (combobox vs. select) — covered by WAI-ARIA 1.2 pattern + accessibility re-audit on affected routes.
- The ISO 4217 currency list adds a static constant (~180 entries) to `domain.money`. Trivial cost; no runtime fetch.

Explicit non-goals:

- **No autocompletion from the server.** Options render inline; no new HTTP endpoint per combobox. Keeps the "no XHR per keystroke" posture and sidesteps the whole async-combobox a11y footgun class.
- **No multi-select combobox.** Current forms are single-value; multi-select is deferred until a surface actually needs it.
- **No form-library adoption.** React Hook Form, Alpine.js, HTMX extensions — all considered and rejected. Vanilla JS fits the ADR-0002 / ADR-0023 budget.
- **No currency metadata beyond the ISO code.** The combobox does not render country names or symbols; the label is the ISO 4217 code. Can grow later without an ADR because it is purely cosmetic.

**Alternatives considered**

- *Per-form fixes.* Rejected — N × bespoke scripts drift and never share a11y audits.
- *Alpine.js / Petite-Vue for combobox state.* Rejected — adds a runtime for a 2-primitive surface. Vanilla is cheaper.
- *HTMX `hx-trigger="keyup changed delay:150ms"` + server-rendered option list.* Rejected — XHR per keystroke, needs a new endpoint per combobox, and the full list already fits in the DOM for every v1 surface (categories ≤ 50, accounts ≤ 10, currencies ≤ 180).
- *Replace `<select>` with native `<datalist>`.* Rejected — Safari and iOS WebKit treat `<datalist>` as a non-filtering autocomplete; the UX is inconsistent per browser.

**References**

- Supersedes nothing. Amends: [ADR-0023](0023-ux-redesign-information-architecture.md) (overlay stack now includes Reconcile; close affordance is universal), [ADR-0024](0024-liability-accounts-and-credit-limit.md) (label is "Credit (liability)" — behavioural scope unchanged).
- Related: [ADR-0026](0026-fab-visibility-scope.md) (slide-over lifecycle), [ADR-0027](0027-frontend-toolchain-hardening.md) (new JS files flow through the stylelint / visual-regression surface — `scripts/` are not CSS so stylelint is not involved; visual regression refreshes baselines on affected routes).
- Requirements: [§2.1](../requirements.md#21-transaction-log-persistent), [§2.2](../requirements.md#22-account-management), [§3.9](../requirements.md#39-ui--interaction-model).
- Task breakdown: [Phase 11 — Shared Form Primitives + Overview Enhancements + Budget Page v2](../plans/v1/phase-11/README.md).
