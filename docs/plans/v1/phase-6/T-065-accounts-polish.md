# T-065 — Accounts Polish

> Phase 6 — UX redesign. Status: pending.

## Purpose

Promote reconciliation into the primary card body and add a 90-day balance sparkline per card. Reduce vertical noise on the Accounts page by hiding snapshot history behind a `Show snapshots` disclosure. All drawn as pure inline SVG (no Plotly) to keep the card dense and fast.

## Inputs / prerequisites

- Upstream tasks: T-061 (shell).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — Accounts page polish spec.
- Adjacent standards: T-053 tokens, `rules/web/performance.md` (no layout animations; sparkline is static SVG).
- Existing services:
  - `services.balance.derive_balance(account_id, as_of=…)` — gives a single derived balance for a date.
  - If a batched version doesn't exist, add `services.balance.balance_series(account_id, from_date, to_date, step=timedelta(days=1))` — but this is a service-layer change and should ship as a separate task if it doesn't exist yet. For now, assume a daily series exists or add a thin wrapper in `services.balance` only (no new repository changes).

## Deliverables

Updated files:

- `src/budget_planner/web/templates/accounts/_card.html`:
  - Keep the account identity header (name · type badge · currency).
  - Below the headline balance (unchanged): inline SVG sparkline, 100% card-width × 48 px tall, using the last 90 days of derived balances.
  - Replace the current hidden Reconcile CTA with a visible inline button on the card body (uses `.btn-primary` from T-053 components).
  - Move the snapshot history block into a `<details>` disclosure: `<details><summary>Show snapshots</summary>…existing snapshot table…</details>`. Collapsed by default.
- `src/budget_planner/web/routers/accounts.py`:
  - Pass a `balances_90d` list to each card context (one float per day, oldest → newest, in native currency).
  - If `balance_series` is not yet a service helper, inline a 90-step loop in the router — but prefer the service.
- `src/budget_planner/web/static/css/components.css`:
  - `.sparkline` + `.sparkline__line` + `.sparkline__area` using `stroke: var(--color-accent)` + `fill: var(--color-surface-sunken)` (area), 1 px stroke. No animation.

Not deliverables:

- No change to the Reconcile flow itself (modal, workflow, service).
- No change to snapshot ingestion or storage.
- No per-account page detail view (`/accounts/{id}`) in this task.

## Step-by-step

1. **Fetch the 90-day series.** In the router, for each account, call `balance_series(id, today - 90d, today)`. If `balance_series` is missing, write it in `services/balance.py` as:
   ```python
   def balance_series(account_id, from_date, to_date):
       return [derive_balance(account_id, as_of=d) for d in daterange(from_date, to_date)]
   ```
   Mark it as a shim and open a follow-up to make it a single SQL window query. Not a Phase 6 blocker.
2. **Normalise the series for SVG.** Compute `min` and `max`; map each point to `(x, y)` where `x = i * (width / (len-1))` and `y = height - ((value - min) / (max - min)) * height`. Guard the `min == max` branch (flat line centred).
3. **Render the SVG inline in the template.** Use a single `<polyline>` for the line and a `<polygon>` for the subtle filled area under the line. No `<path>` strings assembled in Python — compute `points="x1,y1 x2,y2 …"` and pass as a string.
4. **Empty state.** If `len(series) < 2`, render a thin horizontal rule (`<hr>` with `--color-hairline`) instead of the SVG. Add an aria-label on the SVG wrapper (`aria-label="90-day balance trend"`) or `aria-hidden="true"` on the empty-state fallback.
5. **Inline Reconcile.** Replace the current hidden/footer CTA with a visible button inside the card body:
   ```jinja
   <button type="button" class="btn-primary"
           hx-get="/accounts/{{ account.id }}/reconcile"
           hx-target="#modal-root"
           hx-swap="innerHTML">Reconcile</button>
   ```
   The existing reconcile modal is reused — no new router.
6. **Disclosure.** Wrap the snapshot table in `<details class="snapshots"><summary>Show snapshots</summary>{% include "accounts/_snapshot_table.html" %}</details>`. CSS: style the `summary` with `.eyebrow` + a disclosure caret via `::marker` or a chevron glyph.
7. **Required-qualities audit.** This surface already banked polish in T-053; sparkline adds (10) data-vis integrated. Confirm hover / focus on Reconcile and `summary` are explicit (T-053 compliance).

## Validation / acceptance

- `GET /accounts` renders N cards, each with:
  - A visible Reconcile button inside the card body.
  - A sparkline SVG (when `len(balances_90d) >= 2`) or a horizontal-rule fallback.
  - A collapsed `<details>` disclosure containing the existing snapshot table.
- Integration test `tests/integration/web/test_accounts_card.py`:
  - `test_card_has_inline_reconcile_button`
  - `test_card_renders_sparkline_when_series_has_two_or_more_points`
  - `test_card_renders_empty_state_when_series_too_short`
  - `test_snapshots_hidden_until_details_open` (asserts `<details>` without `open` attr by default)
- Visual (Playwright screenshot test under T-071): three card variants (healthy positive, negative, insufficient data) all render without layout shift.
- No new palette values; `--color-accent`, `--color-surface-sunken`, `--color-hairline` only.

## Risks & gotchas

- **N × 90 `derive_balance` calls** is a hot loop. Mitigate: compute `balance_series` once per request; if slow in dev, cache per-account on `request.state` for the page load; proper SQL fix is a Phase 7 task.
- **Scale distortion** when `min == max`. Flat series must render a centred horizontal line, not NaN coordinates.
- **Non-base currency conversion** on the sparkline. Keep the sparkline in **native** currency to avoid composing FX noise into a visual trend. The headline balance below the hero (Panel A in Overview) handles conversion separately.
- **`<details>` default styling** is browser-ish; override `summary::-webkit-details-marker` and style the caret explicitly for Swiss consistency.
- **Reconcile modal + Settings drawer coexistence.** T-071's topmost-overlay rule governs Esc behaviour. For now, Reconcile mounts into `#modal-root` just like today; the rule applies when drawer is also open.

## Handoff notes

- Hand-off to T-071: this is a new surface for the a11y re-audit — specifically keyboard focus on `<details>` and the inline Reconcile button, plus contrast on the sparkline stroke against the card background.
- If a per-account detail page (`/accounts/{id}`) lands later, the sparkline component should be lifted into `partials/_sparkline.html` and reused — but defer until a second consumer exists.
- Commit shape: `feat(T-065): accounts cards — sparkline + inline reconcile + snapshot disclosure`.
