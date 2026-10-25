# T-084 — Web Form + Templates for Liability Accounts

> Phase 7 — Liability Accounts. Status: pending.

## Purpose

Surface the two new fields in the account form, show credit-card utilization on the account card, and switch the dashboard + accounts index from a single fortune number to the three-line Assets / Liabilities / Net worth block.

## Inputs / prerequisites

- Upstream tasks: T-082 (domain + repo), T-083 (fortune service).
- Binding standards:
  - [`ADR-0024`](../../../adr/0024-liability-accounts-and-credit-limit.md) — soft enforcement; the UI shows warnings, services never reject.
  - [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — editorial / Swiss direction, tabular numerals, hairline rules, token-driven styling. The new block lives inside the existing Overview bento grid.
  - Global `web/design-quality.md` — do not ship a template-looking panel; the three-line block must have intentional hierarchy and typography pairing.
  - [`ADR-0010`](../../../adr/0010-account-model-free-text-type.md) — the free-text `type` input stays; the new liability checkbox lives next to it, not in place of it.
- Adjacent precedent:
  - `src/budget_planner/web/templates/partials/accounts/_form.html` — current account form (name, type, currency, opening balance).
  - `src/budget_planner/web/templates/partials/accounts/_card.html` — current account card.
  - `src/budget_planner/web/templates/home/index.html` and `web/templates/accounts/index.html` — current fortune display.

## Deliverables

Modified files:

- `src/budget_planner/web/routers/accounts.py` (`create_account`, `update_account`).
- `src/budget_planner/web/templates/partials/accounts/_form.html`.
- `src/budget_planner/web/templates/partials/accounts/_card.html`.
- `src/budget_planner/web/templates/home/index.html`.
- `src/budget_planner/web/templates/accounts/index.html`.
- `src/budget_planner/web/static/app.css` — one new token-driven block + utilization-bar styles.

### Router changes

`create_account` and `update_account` grow two new `Form(...)` parameters:

```python
is_liability: str = Form(""),  # HTML checkbox → "on" or ""
credit_limit: str = Form(""),  # major-unit decimal string, empty when not a liability
```

Validation:

- Trim + lowercase `is_liability`; `is_liability == "on"` or `== "true"` → `True`, else `False`.
- If `is_liability is True`:
  - `credit_limit` must parse to a strictly positive `Decimal`. Convert via `to_minor_units(dec, cur)`; store as `credit_limit_minor`.
  - On parse failure or non-positive value, render the form with 422 and `errors["credit_limit"] = "positive credit limit required"`.
- If `is_liability is False`:
  - Any value in `credit_limit` is ignored. On `update`, pass `PatchAccount(..., is_liability=False, clear_credit_limit=True)` so the stored limit is nulled when the user unchecks the box.

Templates:

- Reuse the existing `_form_errors.html` partial for the error block.
- Pass the full `FortuneTotals` from T-083 into both index templates under `fortune`.

### Form markup (sketch)

```html
<label class="form-field">
  Name<input type="text" name="name" value="{{ account.name if account else '' }}" required>
</label>

<label class="form-field">
  Type<input type="text" name="type" value="{{ account.type if account else '' }}">
</label>

<label class="form-field form-field--inline">
  <input type="checkbox"
         name="is_liability"
         {% if account and account.is_liability %}checked{% endif %}
         hx-trigger="change"
         hx-get="/accounts/_form_toggle"   {# optional server-driven toggle; see Step 2 #}
         hx-target="closest .form-field--limit"
         hx-swap="outerHTML">
  Credit card (liability)
</label>

<label class="form-field form-field--limit"
       {% if not (account and account.is_liability) %}hidden{% endif %}>
  Credit limit
  <input type="text"
         name="credit_limit"
         inputmode="decimal"
         value="{{ format_money_major(account.credit_limit_minor, account.currency) if account and account.credit_limit_minor else '' }}">
</label>

{# existing currency + opening_balance fields unchanged #}
```

Two implementation options for the show/hide of the limit input:

1. **Progressive-enhancement JS** (~10 lines in `static/js/accounts.js`) that toggles the `hidden` attribute on `change`. Zero server round-trip. **Preferred.**
2. **HTMX round-trip** that re-renders the form fragment with the toggled state. More consistent with the HTMX-first style but adds one request per keystroke on the checkbox.

Pick option (1) and keep the JS minimal + idempotent. The form still works without JS because the `hidden` attribute reflects server state on initial render.

### Card markup (sketch)

```html
<article class="account-card" id="account-{{ card.account.id }}">
  <header>
    <h3>{{ card.account.name }}</h3>
    {% if card.account.is_liability %}
      <span class="pill pill--liability">Credit card</span>
    {% endif %}
  </header>

  <div class="account-card__balance" data-balance="{{ card.balance }}">
    {{ card.balance | money(card.account.currency) }}
  </div>

  {% if card.account.is_liability and card.account.credit_limit_minor %}
    {% set used = (0 - card.balance) if card.balance < 0 else 0 %}
    {% set limit = card.account.credit_limit_minor %}
    {% set available = limit - used %}
    {% set pct = (used * 100 / limit) if limit else 0 %}
    <dl class="credit-strip">
      <div><dt>Limit</dt><dd>{{ limit | money(card.account.currency) }}</dd></div>
      <div><dt>Available</dt><dd>{{ (available if available > 0 else 0) | money(card.account.currency) }}</dd></div>
      <div><dt>Used</dt><dd>{{ "%.0f" | format(pct) }}%</dd></div>
    </dl>
    <div class="utilization-bar" role="progressbar"
         aria-valuemin="0" aria-valuemax="100"
         aria-valuenow="{{ (pct if pct <= 100 else 100) | round(0, 'floor') | int }}">
      <span style="width: {{ (pct if pct <= 100 else 100) | round(2) }}%"></span>
    </div>
    {% if card.balance < -limit %}
      <p class="badge badge--warning">
        Over limit by {{ (used - limit) | money(card.account.currency) }}
      </p>
    {% endif %}
  {% endif %}

  {# existing stats + actions unchanged #}
</article>
```

### Dashboard + accounts index block (sketch)

```html
<section class="fortune">
  <h2 class="eyebrow">Fortune</h2>
  <dl class="fortune-split">
    <div>
      <dt>Assets</dt>
      <dd class="num num--mono">{{ fortune.assets_base | money(base_ccy) }}</dd>
    </div>
    <div>
      <dt>Liabilities</dt>
      <dd class="num num--mono">{{ fortune.liabilities_base | money(base_ccy) }}</dd>
    </div>
    <div class="fortune-split__net">
      <dt>Net worth</dt>
      <dd class="num num--mono">{{ fortune.net_base | money(base_ccy) }}</dd>
    </div>
  </dl>
  {% if fortune.net_by_ccy|length > 1 %}
    <details class="per-ccy">
      <summary>Per currency</summary>
      <ul>
        {% for ccy, v in fortune.net_by_ccy|dictsort %}
          <li>{{ ccy }} <span class="num num--mono">{{ v | money(ccy) }}</span></li>
        {% endfor %}
      </ul>
    </details>
  {% endif %}
</section>
```

### CSS additions

Add tokens + rules in `static/app.css` under the existing token layer:

- `.pill--liability` — accent-wash background, 1px hairline border, 12px uppercase tracking.
- `.credit-strip` — three-column `<dl>` with hairline separators and tabular-nums.
- `.utilization-bar` — 6px rail using `--rule-strong` for the track and `--accent` for the fill; add `.utilization-bar[aria-valuenow="100"]` to tint red when at or above the limit.
- `.badge--warning` — reuse the existing warning flash tokens; do not invent a new palette.
- `.fortune-split` — three-column grid at ≥480px; stacked below; `.fortune-split__net dd` is `--text-hero` sized for scale contrast.

Honour `@media (prefers-reduced-motion: reduce)` on the utilization bar transition — the T-052 global rule already does this.

### Test matrix

Integration (`tests/integration/web/test_accounts.py`):

- `test_create_credit_card_account_round_trips_limit`.
- `test_create_liability_without_limit_returns_422`.
- `test_update_asset_to_credit_card_sets_limit`.
- `test_update_credit_card_to_asset_clears_limit_via_patch_sentinel`.
- `test_card_shows_utilization_strip_only_for_liability`.
- `test_card_shows_over_limit_badge_when_balance_below_negative_limit`.
- `test_card_hides_badge_when_within_limit`.
- `test_accounts_index_renders_assets_liabilities_net`.

Integration (`tests/integration/web/test_home.py`):

- `test_home_renders_assets_liabilities_net` — assert three labels, three figures, and that the per-currency `<details>` appears only when `len(net_by_ccy) > 1`.

Unit (`tests/unit/web/test_form_toggle.py` — optional, if the JS toggle is non-trivial): omit — ten lines of DOM toggling is better covered by the integration DOM assertions above.

## Step-by-step

1. **Router first.** Add the two `Form(...)` params, the validation branch, and the `PatchAccount` wiring. Keep `_hydrate(...)` + `index` unchanged except for the fortune context key, which T-083 already produced.
2. **Form template.** Add the checkbox + conditional field in that order. Reflect server state via the `hidden` attribute so no-JS users still see a coherent form.
3. **Static JS toggle.** Add `static/js/accounts.js` with one event listener; include it from `base.html` only on `/accounts*` pages (or inline on the form template). Keep ≤ 15 lines.
4. **Card template.** Insert the pill + credit strip + utilization bar + over-limit badge. Keep the existing stats block below.
5. **Dashboard templates.** Switch both index templates from the single-figure fortune to the three-line block with the per-currency disclosure.
6. **CSS.** Add tokens + rules; reuse existing palette variables.
7. **Tests.** Add integration coverage per the matrix above. Use BeautifulSoup for DOM assertions (precedent set by T-031 tests).
8. **Accessibility re-sweep.** The utilization bar carries `role="progressbar"` + `aria-valuemin/max/now`. Add one test to `tests/integration/web/test_accessibility.py` asserting these attributes.

## Validation / acceptance

- `pytest tests/integration/web/test_accounts.py tests/integration/web/test_home.py -q` — all new cases green.
- `pytest tests/integration/web/test_accessibility.py -q` — progressbar coverage added.
- `just lint` + `just typecheck` + `just ci` all green.
- Manual: `just dev` → create "Visa (PLN)" with limit `10,000.00` → card shows `Limit 10,000.00 · Available 10,000.00 · 0% used`.
- Manual: add `expense 500.00` on Visa → card shows `Available 9,500.00 · 5% used`; dashboard shows `Liabilities 500.00`, `Net worth = Assets − 500.00`.
- Manual: add `expense 11,000.00` on Visa (overshoot) → over-limit badge shows `Over limit by 1,500.00`; dashboard figures update; the transaction is NOT rejected.

## Risks & gotchas

- **Checkbox booleanness.** `Form("")` returns `""` when the box is unchecked and `"on"` when checked. Guard with an explicit comparison; do not rely on truthiness of the raw string.
- **Clearing the limit.** When the user unchecks "credit card" on an existing liability, the router must pass `PatchAccount(is_liability=False, clear_credit_limit=True)` — `None` on the patch field means "no change" everywhere else in the codebase.
- **Over-limit vs available.** `available = max(limit - used, 0)` so the strip never shows a negative "available". The over-limit badge carries the signed delta separately. Keep the two displays consistent.
- **Dashboard scope.** The three-line block replaces the single number on `home/index.html` and `accounts/index.html` only. `/forecast`, `/budget`, and `/analytics` are untouched in this phase (their fortune references, if any, continue to use `fortune.net_base`).
- **Decimal parsing.** `credit_limit` uses the same `Decimal` pipeline as `opening_balance`; reuse `to_minor_units(dec, cur)` instead of hand-rolling conversion.
- **Design discipline.** Do not add a dedicated "liability" palette hue. Reuse `--accent-wash` + the existing warning tokens. The point is quiet, intentional hierarchy — not a loud new theme.

## Handoff notes

- Hand-off to T-085: the transaction form can import `services.balance.derive_balance` + the chosen account's `credit_limit_minor` directly to project post-transaction utilization. No new types needed.
- Hand-off to T-086: the seed should land a liability account that exercises both the "within limit" and "over limit" code paths across the e2e journey.
- Commit shape: `feat(T-084): credit-card form + card utilization + net-worth split (ADR-0024)`.
