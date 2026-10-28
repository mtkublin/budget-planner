# 03 · Screen specs

Ids refer to the canvas and screenshots. Data shown in mockups is the real data from the audit screenshots unless noted in 07.

## Today (1d, mobile 1o)
- **Hero:** left per day (e.g. 191.08 PLN/day), pace tag (On track / Tight / N overdue), segmented bar spent | committed | left, period line.
- **Can I afford it?** amount input → recomputed per-day figure = (left − input) / days left, plus the delta. Server computes; debounced.
- **Net worth card:** total, assets, liabilities, the six largest balances, links to Accounts and Forecast.
- **Upcoming:** segmented 7 days / 30 days / All. Grouped by "Next 7 days", then date ranges. Row: date, name + account (+ ƒ if formula), category pill, signed amount, **Promote / Skip / Override**.
- **Promote** expands the row in place into editable account, date, amount and **Confirm ↵ / Esc**. No modal.
- **Overdue** rows: expense-soft background, "N days late" chip, sorted first. Never muted.
- Top bar: search/jump (⌘K, deferred) and + Add.

## Ledger · Actual (1e, mobile 1p)
Tabs with counts; `[` and `]` switch. Filters as chips: date range, category, account, direction, search (`/`). Rows grouped by day with day header and net (transit excluded). Columns: description + account, category pill, direction badge, signed amount, ⋯. Deleted = archived; restorable from ⋯ or "Recently deleted".

## Ledger · Planned (2a)
Columns: due, description + account, category, amount, status, actions. Status: "in N days", red "N days late" chip, or ✓ Promoted with a link to the transaction. Actions: Promote ↵, Edit, ⋯. Empty state with "+ Planned entry".

## Ledger · Recurring (1f)
Grouped Monthly / Yearly. Row: next due, rule + account, category, amount (ƒ marks formula), override count, **Edit · Skip next · ⋯ · chevron**. ⋯ = Override next…, Duplicate, Deactivate, Archive rule. Chevron expands:
- overrides list (date, type Amount/Skipped/Moved, value, Remove);
- for formula rules, the **derivation** (signed terms and values summing to the amount; sources link to their rules).

## Plan · Budget (1g, mobile 1q)
Header: period card (anchor, bar, per-day). Month switch ← Month YYYY →. Table: category, **Planned (click to edit default)**, actual, used bar, remaining (red if over), ⋯. ⋯ opens **Override**: This month only / Every {month} / New default, amount, Save. Categories with spend but no budget listed below the total.

## Plan · Year (1h, mobile 1q lower)
Year switch ← 2026 →. Rows = budgeted categories, columns = Jan–Dec + total. Cell colour intensity scales with amount (sqrt, capped at 1,600). Tier markers: **bold + accent outline = one-off**, **italic + diagonal hatch = recurring every year**, plain = default, dash = unset. Click a cell: popover with amount, **One-off · {month YYYY} / Every year · {month}** switch, Save ↵, Reset to default. Narrow screens: sticky category column + horizontal scroll, or cards.

## Plan · Forecast (1i, mobile 1r)
Horizon 6 / 12 / 24 / 60 months. Summary: now, end, peak. SVG line + area with annotations on outliers (e.g. profit share in March; planned holiday in September). Table: month, income, expenses, planned budget, net (with inline bar), end-of-month balance. Current month row comes from Budget summary.

## Plan · Analytics (2b)
Month / 3 months / YTD / 12 months. Spend by category with bar, amount, and delta vs 12-month average (red above). Income vs expense by month. Largest single items. Each category row links to Ledger filtered by that category and period.

## Accounts (1j, mobile 1s)
Net worth headline, assets, liabilities. Table: name + type, trend sparkline, **last checked** status (warning tag if stale), transaction count, balance, Reconcile. Liability rows show limit / available / used bar. Edit, Snapshot, Delete move into a ⋯ menu (not shown).

## Reconcile slide-over (1k)
Three steps in plain language: open your bank → enter its balance → review. Shows app vs bank balance, the difference, and a **Record as** category selector (default "Reconciliation (system)", any category allowed). Option to also save a snapshot. History of previous checks. Primary button states the amount: "Record −28.90".

## Add entry (1l formula, 2e fixed, mobile 1t)
1. When: Happened / Planned / Repeats.
2. **Category** (pill + derived direction badge). Direction is not chosen separately. Choosing the Transit system category reveals From/To accounts (same currency only).
3. **Amount: Fixed value / Formula ƒ.** Fixed = one amount input with per-day impact. Formula = list of terms (sign, source rule, coefficient %, resulting value), + Add term, live result. Cycles and non-positive results blocked on save.
4. Account, date, note; for Repeats: next due and cadence.

## Create account (2c)
Name, currency (immutable, stated), free-text type, opening balance + as-of date, liability toggle. Credit limit field is rendered only while the toggle is on (hidden, `aria-hidden` and disabled otherwise, per ADR-0030).

## Create category (2d)
Name, direction (Expense / Income only; immutable), colour (direction default or one of 10 swatches), live preview of the pill + badge.

## Settings · Categories (1n)
Income-anchor selector, then Expense / Income / System groups. Row: pill, direction badge, colour source, Edit · Archive (archived categories restorable). System rows are locked.

## Command palette (1m) — deferred
Groups: Actions (promote items with amount and date), Go to, Create. Kept as a design reference only.
