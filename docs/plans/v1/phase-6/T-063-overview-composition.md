# T-063 — Overview Composition

> Phase 6 — UX redesign. Status: pending.

## Purpose

Rewrite `/` as the three-panel Overview specified in ADR-0023: Accounts (fortune hero + per-currency row + account list + repeated sum), This month (amount-left headline + spent/of + bar + days-left + pace tag + links to `/forecast` and `/budget`), and Upcoming planned (sorted ascending, overdue rows muted, promoted rows excluded). Panels reuse existing services; a single new fragment route feeds the Upcoming panel.

## Inputs / prerequisites

- Upstream tasks: T-061 (shell), T-062 (nav).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — three-panel Overview spec, overdue highlighting rule.
- Adjacent standards: T-053 tokens, `rules/web/design-quality.md` (≥4 required qualities per surface).
- Existing services (reuse — do not reimplement):
  - `services.balance.derive_balance(account_id, as_of=…)` — per-account derived balance.
  - `services.balance.list_account_balances(as_of=…)` — all accounts with balances (if present; otherwise iterate).
  - `services.budget.month_summary(month=…)` — spent / planned / remaining / pace signal.
  - `services.planned.list_planned(window=…, promoted=False)` — upcoming + overdue, promoted filter.
  - `services.fx.convert(amount, from_currency, to_currency, on_date)` — per ADR-0006, convert non-base balances for display.

## Deliverables

Updated files:

- `src/budget_planner/web/templates/home/index.html` — rewritten as three panels.
- `src/budget_planner/web/routers/home.py`:
  - `GET /` composes the three panels (full-page render) by calling the three services above.
  - `GET /overview/upcoming?window=7|30|all` — HTMX fragment returning `partials/_upcoming_list.html` for the Panel C live-swap.
  - Listens to HTMX trigger events (`txn-created`, `planned-stale`) via `hx-trigger` on the receiving element — no server event system; just re-fetch the fragment on event.

New files:

- `src/budget_planner/web/templates/home/_accounts_panel.html` — Panel A.
- `src/budget_planner/web/templates/home/_month_panel.html` — Panel B.
- `src/budget_planner/web/templates/home/_upcoming_panel.html` — Panel C shell + range selector + list wrapper.
- `src/budget_planner/web/templates/home/_upcoming_list.html` — Panel C list body (fragment target for `/overview/upcoming`).

Not deliverables:

- No new service logic. If a service lacks a needed query, extend it in its own task.
- No forecast chart on this page (lives on `/forecast`, linked out).
- No analytics tiles on this page (lives in Budget breakdown, T-066).

## Step-by-step

1. **Grid.** Panels A + B share row 1 using a 12-col grid: A `col-span-7`, B `col-span-5`. Panel C spans the full 12 cols on row 2. Gap: `var(--space-5)`.
2. **Panel A — Accounts.**
   - Hero: `FORTUNE` eyebrow (`.eyebrow`), display-size tabular-nums base-currency total from the sum of `list_account_balances` converted via `services.fx.convert`.
   - Per-currency row below the hero: iterate currencies present in the account set; format as `EUR 18 420,00 · USD 2 410,55 · CHF 12,00`. Separator = `·` with `--color-text-faint`.
   - Account list: one row per account; hairline bottom separator (`var(--color-hairline)`). Columns: name · type badge · currency · native balance (`.numeric`, right-aligned). For non-base-currency accounts, append converted balance in `--color-text-faint` wrapped in parentheses.
   - Negative balances rendered with `--color-expense` (defined in T-053 tokens; if not present, add in that task before this one lands).
   - Row click target: `href="/accounts#{{ id }}"`.
   - Footer line (closure): hairline + `All accounts · <sum in base>` — same number as the hero.
3. **Panel B — This month.**
   - Headline: amount-left (base currency) from `month_summary.remaining`, display-size tabular-nums.
   - Secondary line: `spent {{summary.spent}} of {{summary.planned}} · {{summary.days_left}} days left`, `.text-sm`, subtle.
   - Bar: accent fill on `--color-surface-sunken` track. Width = `100 * spent / planned` clamped `[0, 100]`.
   - Pace tag: `on track` / `pacing high` / `over budget`. Colour token: `--color-success` / `--color-warning` / `--color-error`.
   - Footer links: `See forecast →` → `/forecast`; `Budget breakdown →` → `/budget`.
4. **Panel C — Upcoming planned.**
   - Header row: `UPCOMING` eyebrow + range selector (`7 days · 30 days · all`) as segmented buttons wired via `hx-get="/overview/upcoming?window=7|30|all"` targeting the list wrapper + `hx-swap="innerHTML"` + `hx-push-url="false"`.
   - List: sorted by `planned_date` ascending. Default window: last 7 days through next 30 days.
   - Row columns: date · direction pill · amount · category · account · description · promote-button.
   - **Highlight rule.** For each row:
     - `planned_date >= today` → class `upcoming-row` (full emphasis; `--color-text`, hairline bottom, accent-tinted date column).
     - `planned_date < today` → class `upcoming-row upcoming-row--overdue` (`--color-text-subtle`, italic date, small `overdue` chip at row start).
     - `promoted = True` rows are filtered out at the service call (`promoted=False` filter).
   - Empty state: `No planned payments in this window.` inside the list wrapper.
   - Live-update: the list wrapper has `hx-get="/overview/upcoming?window={{ window }}" hx-trigger="txn-created from:body, planned-stale from:body"`. Events are emitted by T-064 and T-069 after mutations.
5. **Accessibility.**
   - The list wrapper is `aria-live="polite" aria-busy` toggles during swap.
   - Range selector buttons use `aria-pressed="true|false"` to communicate the active window.
   - Panel A account list is a semantic `<ul>` of rows, not a `<table>`, because columns are presentational — see `rules/web/coding-style.md`.
6. **Required-qualities audit.** (1) hierarchy ✓ (2) rhythm ✓ (3) depth via hairlines ✓ (5) semantic colour ✓ (10) data-vis integrated (bar uses tokens) ✓ — five of ten.

## Validation / acceptance

- `GET /` returns 200, DOM contains three sections: `[data-panel="accounts"]`, `[data-panel="month"]`, `[data-panel="upcoming"]`.
- `GET /overview/upcoming?window=7` returns the fragment HTML (no `<html>` wrapper).
- Integration test `tests/integration/web/test_overview.py`:
  - `test_overdue_row_has_overdue_class`: seeds a planned txn with `planned_date = today - 1`, asserts the rendered row has `upcoming-row--overdue`.
  - `test_future_row_has_full_emphasis_class`: seeds `planned_date = today + 5`, asserts `upcoming-row` without the overdue modifier.
  - `test_promoted_rows_excluded`: a `promoted=True` planned row does not appear in `GET /overview/upcoming`.
  - `test_window_param_filters`: `?window=7` and `?window=30` return different row counts for a seeded dataset.
  - `test_live_update_after_txn_created`: posts a transaction, asserts an HTMX event is included in the response headers (`HX-Trigger: txn-created`); the panel's `hx-trigger` picks it up (verified via the `hx-trigger` attribute presence in the rendered page, not JS execution).
- Visual: Panel A fortune number matches `sum(convert(balance, native, base) for each account)`.
- No new tokens introduced; everything references `--color-*` / `--space-*` / `--text-*` from T-053.

## Risks & gotchas

- **FX conversion cost.** Fetching per-account converted balances inline can be O(N) FX lookups. Prefer batching: pre-fetch latest rate map for the base currency once, then convert in-memory.
- **"Today" boundary.** Use `datetime.utcnow().date()` as per ADR-0007 (dates are naive DATE); the overdue cutoff is `planned_date < today`.
- **Pace tag thresholds.** The service owns the signal (`on track` / `pacing high` / `over budget`). Do not re-derive in the template.
- **Live-update loops.** `txn-created` fires after any transaction mutation. If the Panel C fragment also emits that event (it shouldn't; it's read-only), you'd loop. Panels only *listen*, never emit.
- **Empty state copy.** `No planned payments in this window.` — not `No results`. Copy matters.
- **Range selector state.** The selector is a form group with `aria-pressed`; the active state is driven by the current query param rendered by the server, not JS state.

## Handoff notes

- Hand-off to T-068 (palette): the "Reconcile account…" and "Filter by category…" palette JUMP items can read account names from the Accounts panel if the palette fetches `/overview/upcoming` or a dedicated `/palette/jump` endpoint. T-068 decides; T-063 is agnostic.
- Hand-off to T-069 (FAB): `[+ Planned]` button in Panel C header opens the Quick-add slide-over with the planned form preselected. The button uses the same `data-add-kind="planned"` contract T-069 defines.
- Commit shape: `feat(T-063): overview — three-panel composition + /overview/upcoming fragment`.
