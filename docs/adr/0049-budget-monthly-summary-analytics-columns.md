# ADR-0049: Budget Monthly Summary — Surface Analytics Columns (Avg/mo, YTD avg, Δ prev)

- **Status**: Accepted
- **Date**: 2026-10-28
- **Amends**: [ADR-0031](0031-budget-page-composition-v2.md) §Monthly summary (extends the Section 1 table surface); surfaces values already computed per F4.5 in [requirements.md](../requirements.md).

## Context

`services.budget.month_summary` already computes three per-category analytical values on every `CategoryBudgetLine` DTO (`services/budget.py:293–364`):

- `avg_monthly_overall_minor` — lifetime mean spend per category, derived as `total_spend / distinct_active_months`.
- `avg_this_year_minor` — YTD mean, derived as `year_sum / elapsed_months`.
- `delta_vs_prev_month_minor` — signed change vs the previous calendar month (`spent_this − spent_prev`).

Requirement F4.5 already lists these as part of the Current-month view. ADR-0031 did not extend the Monthly Summary table to render them; the values sit on the DTO unused. `/budget` Section 1 (`templates/budget/index.html:77–139`) renders only Category · Planned · Actual · Remainder-bar · Remainder.

Users asked "what do I usually spend on category X?" — the answer is already computed, just not visible.

## Decision

Add three columns to the Section 1 Monthly summary table, in this order after "Actual" and before the Remainder bar:

1. **Avg/mo** — `line.avg_monthly_overall_minor|money(base_ccy)`. Lifetime mean.
2. **YTD avg** — `line.avg_this_year_minor|money(base_ccy)`. Current calendar-year mean.
3. **Δ prev** — `line.delta_vs_prev_month_minor|money(base_ccy)`, prefixed with explicit `+` / `−` sign and classed `.delta--up` (expense increased, red tint) or `.delta--down` (expense decreased, green tint) via a signed CSS modifier.

Rendering rules:

- All three columns use `tabular-nums` + `text-right`.
- Zero-value cells render as `0.00` (same `money` filter), not em-dash — these are computed values, not "unset".
- `delta_vs_prev_month_minor == 0` renders as `0.00` with neither sign modifier class.
- `tfoot` totals row leaves these three cells empty (`<td></td>`). Summing per-category averages would be misleading because each category's `_active_month_counts` divisor differs; a weighted-sum here would overstate on recently-created categories.

Responsive behaviour:

- At viewport `< 640px` the **YTD avg** and **Δ prev** columns are hidden via a `.col-hide-sm` utility (`display: none` under the breakpoint; `table-cell` above). **Avg/mo** stays visible — it is the single most-asked-for value.
- Column `<th>` carries the same `.col-hide-sm` class so the header hides in lockstep.
- The 7-column desktop width stays inside the existing `.ledger-scroll` wrapper so overflow is already handled.

No service, repository, or DTO change. Pure template + CSS surfacing.

## Consequences

Pros:

- Zero new computation. The three values are already present on `CategoryBudgetLine`; the surface change is template-only.
- Answers the "what do I usually spend?" question in the primary budget surface, where the user already sees the current-month "spent" alongside.
- Δ prev gives a trend signal that YTD avg alone cannot — users spot an off-trend month immediately.
- Keeps the Monthly summary and the (unchanged) Rules + Yearly sections tier-independent — the analytics are observational, not an input to F4.2 budget resolution.

Cons / costs:

- The desktop table grows from 5 to 7 columns. At 1024/1440 widths this fits inside existing `.ledger-scroll`; audited at those viewports.
- Visual-regression baselines refresh on `/budget` for desktop + tablet + mobile.
- A new signed-delta CSS modifier (`.delta--up` / `.delta--down`) joins the existing color token set. Red/green are driven by the existing `--expense` / `--income` CSS custom properties so no new palette.
- One more thing for new users to parse. The three new columns are opt-out-by-design on mobile (YTD + Δ hidden), opt-in-by-reading on desktop.

Explicit non-goals:

- **No sparklines / in-row charts.** Keep the surface a plain table; charts live in Section 4 Breakdown.
- **No "last 3 months" or custom windows.** The three windows (overall / YTD / vs prev) match F4.5 exactly; expanding the window set is a future ADR.
- **No sortable columns.** The row order stays "budgeted first, then alphabetical" (`services/budget.py:367`).
- **No income-direction categories in Section 1.** Monthly summary already filters to `Direction.EXPENSE` (`services/budget.py:306`); the new columns inherit that scope.
- **No totals-row aggregation of averages.** Weighted means across categories with different active-month counts is misleading; left blank.

## Alternatives considered

- *Add a dedicated `/budget/analytics` subpage.* Rejected — adds a route for data that is already on the Monthly summary row context. Fragments the surface.
- *Expose the values via a per-row "Analytics" slide-over.* Rejected — the values are small, three of them, and they live on every row. A slide-over per row is heavier than three columns.
- *Toggleable column visibility (user-controlled checkboxes).* Rejected for v1 — three columns is below the threshold where a toggle UX pays for itself. Revisit if the column count grows.
- *Render the delta as a percentage (`+12.5%`) instead of absolute minor units.* Rejected — percentages blow up for categories with near-zero prev-month spend. Absolute minor units match the other columns' units and are legible.

## References

- Amends: [ADR-0031](0031-budget-page-composition-v2.md) §Monthly summary (table surface extended; Rules + Yearly unchanged).
- Related: [ADR-0023](0023-ux-redesign-information-architecture.md) (budget-as-hub IA scope), [ADR-0014](0014-budget-flat-no-rollover-three-tier.md) (three-tier resolution — unchanged), [ADR-0041](0041-budget-period-anchor-window.md) (per-category `spent_minor` is paycheck-window; the three new analytics windows stay calendar-month per F4.6).
- Requirements: [§2.4 F4.5](../requirements.md#24-monthly-budget) (analytical values list — this ADR is the surface for the already-documented values).
- Task breakdown: T-133 in Phase 12.
