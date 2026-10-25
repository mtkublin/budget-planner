# T-085 — Transaction-Form Soft Warning for Liability Accounts

> Phase 7 — Liability Accounts. Status: pending.

## Purpose

Give the user a non-blocking preview on the transaction form: when the chosen account is a credit card, show the projected available credit after the transaction, and a red note when the projected balance would exceed the limit. The service layer is unchanged — this is a UX layer, soft-only.

## Inputs / prerequisites

- Upstream tasks: T-084 (form markup + utilization strip pattern established).
- Binding standards:
  - [`ADR-0024`](../../../adr/0024-liability-accounts-and-credit-limit.md) — soft enforcement; the service never rejects.
  - [`ADR-0008`](../../../adr/0008-transaction-amount-sign-and-direction.md) — signing stays category-driven; the preview respects direction.
  - `web/testing.md` — add deterministic HTMX assertions, no timing-based flake.
- Adjacent precedent: `src/budget_planner/web/templates/partials/transactions/_form.html` + the transactions router (T-031).

## Deliverables

Modified files:

- `src/budget_planner/web/routers/transactions.py` — add one small HTMX fragment endpoint `GET /transactions/_limit_preview?account_id=…&category_id=…&amount=…` that returns the preview partial. No new business logic — the endpoint composes `services.balance.derive_balance` + the category direction + the account's `credit_limit_minor`.
- `src/budget_planner/web/templates/partials/transactions/_form.html` — add a `<div id="limit-preview">` slot and `hx-trigger`/`hx-get` wiring on the account + category + amount inputs.
- `src/budget_planner/web/templates/partials/transactions/_limit_preview.html` — new partial.

### Preview algorithm

```python
def preview(conn, account_id: int, category_id: int, amount_minor: int) -> LimitPreview | None:
    account = accounts_repo.find_by_id(conn, account_id)
    if account is None or not account.is_liability or account.credit_limit_minor is None:
        return None  # no card rendered

    direction = categories_repo.find_by_id(conn, category_id).direction
    current_balance = balance_service.derive_balance(conn, account_id)

    # Project the hypothetical signed delta on THIS account only.
    # Use the same rule as services/balance.signed_legs for the single-leg cases:
    if direction is Direction.INCOME:
        delta = amount_minor
    elif direction is Direction.EXPENSE:
        delta = -amount_minor
    elif direction is Direction.TRANSIT:
        # The form's `account_id` is the SOURCE leg.
        delta = -amount_minor
    else:  # ADJUSTMENT — pre-signed amount
        delta = amount_minor

    projected = current_balance + delta
    limit = account.credit_limit_minor
    used_after = max(-projected, 0)
    available_after = max(limit - used_after, 0)
    over_by = max(used_after - limit, 0)
    return LimitPreview(
        projected_balance=projected,
        available_after=available_after,
        used_after=used_after,
        limit=limit,
        over_by=over_by,
        currency=account.currency,
    )
```

- The preview is **not** a validator — the form continues to submit even when `over_by > 0`.
- The transit case covers only the source leg; the preview is scoped to the single `account_id` on the form. If `account_id` is a liability and the direction is `transit` *into* it (destination), the preview is skipped (destination-leg utilization previews can land in a later task).

### Partial markup (sketch)

```html
<div id="limit-preview">
  {% if preview %}
    <aside class="limit-preview {% if preview.over_by > 0 %}limit-preview--over{% endif %}"
           aria-live="polite">
      {% if preview.over_by > 0 %}
        <strong>Over limit</strong>
        by {{ preview.over_by | money(preview.currency) }}
      {% else %}
        <strong>After this transaction</strong>
        Available {{ preview.available_after | money(preview.currency) }}
        · Limit {{ preview.limit | money(preview.currency) }}
      {% endif %}
    </aside>
  {% endif %}
</div>
```

### Form hooks (sketch)

```html
<fieldset>
  <select name="account_id"
          hx-get="/transactions/_limit_preview"
          hx-include="[name='account_id'],[name='category_id'],[name='amount']"
          hx-target="#limit-preview"
          hx-swap="outerHTML"
          hx-trigger="change">...</select>
  <select name="category_id"
          hx-get="/transactions/_limit_preview"
          hx-include="[name='account_id'],[name='category_id'],[name='amount']"
          hx-target="#limit-preview"
          hx-swap="outerHTML"
          hx-trigger="change">...</select>
  <input name="amount"
         hx-get="/transactions/_limit_preview"
         hx-include="[name='account_id'],[name='category_id'],[name='amount']"
         hx-target="#limit-preview"
         hx-swap="outerHTML"
         hx-trigger="change delay:200ms, keyup changed delay:400ms">
</fieldset>

<div id="limit-preview"></div>
```

### Tests

Integration (`tests/integration/web/test_transactions.py`):

- `test_preview_hidden_for_asset_account`.
- `test_preview_shows_available_for_within_limit_expense`.
- `test_preview_shows_over_limit_for_overshoot_expense`.
- `test_preview_handles_transit_source_leg`.
- `test_preview_handles_adjustment_signed_amount`.
- `test_preview_updates_on_amount_change` — simulate three fragment requests with different `amount` values, assert the response text changes accordingly.
- `test_form_submits_even_when_over_limit` — a POST with an over-limit amount still returns 200 and inserts the transaction (soft only).

Unit (`tests/unit/services/test_transactions_preview.py`): optional — the preview arithmetic is small and the integration tests cover each branch deterministically. Only add a unit test if the router accrues more than ~20 lines of logic.

## Step-by-step

1. **Add the endpoint.** `GET /transactions/_limit_preview` with query parameters `account_id`, `category_id`, `amount` (as a decimal string). Parse amount via `to_minor_units(Decimal(...), account.currency)`; return a 200 with an empty `#limit-preview` fragment on any parse failure (preview is lossy by design).
2. **Add the partial.** Keep it accessible (`aria-live="polite"`) and reuse the existing warning tokens for the over-limit variant.
3. **Wire the form.** Attach `hx-get` / `hx-target` / `hx-trigger` on the three relevant inputs. Debounce the amount input (`delay:200ms` on change, `delay:400ms` on keyup) to avoid chatty fragment requests.
4. **Tests.** Follow the matrix above; use BeautifulSoup to assert the preview text and class on each case.

## Validation / acceptance

- `pytest tests/integration/web/test_transactions.py -q` — all new cases green.
- `pytest -k "preview" -q` — the preview tests specifically pass.
- `just lint` + `just typecheck` + `just ci` all green.
- Manual: `just dev` → `/transactions/new`, pick the Visa account + an expense category + `500.00` → preview strip shows `Available 9,500.00 · Limit 10,000.00`.
- Manual: change amount to `11,000.00` → strip flips to `Over limit by 1,500.00` with the warning tint; submit succeeds; the account card now shows the over-limit badge from T-084.

## Risks & gotchas

- **HTMX chattiness.** Debounce the amount input to keep fragment requests under one per 400ms of continuous typing. Do not debounce the select changes — those are discrete events.
- **Partial on failure.** If any input is unparseable, return the empty `#limit-preview` fragment (not 422) so the form stays usable. Validation errors still land through the main `POST /transactions` path.
- **Direction coverage.** Keep the preview switch tightly aligned with `services.balance.signed_legs`. Any future direction (none planned in v1) must be added in both places together.
- **Destination-leg previews.** Deliberately out of scope. If a user picks a liability as the TRANSIT destination, the preview is suppressed. A later task can extend the endpoint to accept `dest_account_id` and render two cards.
- **Accessibility.** `aria-live="polite"` is correct — the preview is advisory, not a status alert. Do not escalate to `role="alert"`.

## Handoff notes

- Hand-off to T-086: the e2e journey adds a `transit` payment from a bank account to the Visa; verify the preview is suppressed on that submission (destination-leg out of scope) and the card utilization still updates post-submit via `balance-stale`.
- Commit shape: `feat(T-085): credit-card soft-limit preview on transaction form (ADR-0024)`.
