# ADR-0040: Modal Dismissal Fires on Form Submit Only, Not Side-Effect HTMX Requests

- **Status**: Accepted
- **Date**: 2026-10-27
- **Amends**: ADR-0030 §5 (clear-on-save primitive).

## Context

ADR-0030 §5 defines `data-reset-on-submit`: a form attribute that the `base.html` listener uses to reset inputs *and* close the hosting slide-over after any 2xx HTMX response. The listener (`src/budget_planner/web/templates/base.html:70-93`) matches via:

```js
form = evt.target.closest("form[data-reset-on-submit]")
```

The transaction, planned, and recurring create forms also wire **side-effect** HTMX requests to individual inputs — e.g. the amount input in `partials/transactions/_form.html:19-28`:

```
hx-get="/transactions/_limit_preview"
hx-trigger="change delay:200ms, keyup changed delay:400ms"
hx-target="#limit-preview"
```

The `hx-get` fires on keystroke. Its 2xx response is a success event bubbling to `document.body`. The current listener's `closest("form[data-reset-on-submit]")` resolves because the input *is* inside such a form, so the slide-over gets destroyed on the first keystroke in the amount field. User-visible symptom: the New-transaction popover disappears as soon as the user types in `amount`.

The bug surfaced on Overview's `+ Transaction` and Ledger's `+ Transaction`. It would also affect any future side-effect fragment attached inside a reset-on-submit form (combobox hydrators, dependent dropdowns, autosaves).

## Decision

Scope `data-reset-on-submit` to **form submission events only**, not arbitrary descendant HTMX requests.

### Rule

The reset-and-close listener fires when **all three** conditions hold:

1. `detail.xhr.status ∈ [200, 300)`.
2. `evt.target` is itself the `<form[data-reset-on-submit]>` — not a descendant element.
3. The XHR was issued by the form's own HTMX binding (`hx-post` / `hx-put` / `hx-delete`), i.e. `detail.requestConfig.verb` is in `{"post", "put", "delete"}`.

Rephrased for implementation:

```js
document.body.addEventListener("htmx:afterRequest", function (evt) {
  var detail = evt.detail || {};
  if (!detail.successful) return;
  var xhr = detail.xhr;
  if (!xhr || xhr.status < 200 || xhr.status >= 300) return;
  var form = evt.target;
  if (!(form instanceof HTMLFormElement)) return;
  if (!form.hasAttribute("data-reset-on-submit")) return;
  var verb = (detail.requestConfig && detail.requestConfig.verb) || "";
  if (!["post", "put", "delete"].includes(verb.toLowerCase())) return;
  // reset + close slide-over, same body as today.
});
```

- `evt.target` on HTMX form submissions is the form element itself (standard HTMX contract). On input-level side-effect requests it is the input, which fails condition (2) above.
- The verb check (3) is defence in depth: it rules out `hx-get` wired to the form root (rare, but possible for live-search forms).

### Validation requirement

Regression test (`tests/integration/web/test_forms.py`):

- Open `/transactions/new`, assert slide-over markup in `#modal-root`.
- Trigger `GET /transactions/_limit_preview` via a simulated HTMX request against the inputs within the form.
- Assert `#modal-root` still contains the slide-over after the fragment returns 200.
- Then simulate `POST /transactions` with valid payload; assert `#modal-root` is empty and the form was reset.

Same pattern pinned for `/planned/new`, `/recurring/new`.

## Consequences

- Side-effect fragments attached to inputs are safe to add anywhere, without the ambient "close the modal on success" behaviour taking the dialog down.
- The reset-and-close behaviour's trigger surface is now narrow and explicit, matching user mental model: "when I submit a create form successfully, the modal closes".
- HTMX's `requestConfig` is a documented stable field; no reliance on undocumented internals.

## Alternatives Considered

- **Move the side-effect `hx-get` from the input onto a `<span>` wrapper outside the form.** Rejected — the amount input needs to be the hx-target source for `hx-include` to include the right amount value; splitting it fragments the HTMX wiring.
- **Add `data-no-close` to the input.** Rejected — opt-out requires every author of a new side-effect fragment to remember to tag it; opt-in on the form submit path is safer.
- **Give up on auto-close and require explicit `HX-Trigger: close-slide-over` headers from the create endpoints.** Workable but doubles the server-side bookkeeping; the simple event-source check captures the user intent for free.
