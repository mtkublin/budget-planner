# 02 · Ledger

Three tabs: **Actual · Planned · Recurring**. Current app serves the Rising Dough shell + title + tab chips, but every table underneath still runs the v1 layout.

## `/ledger?view=actual` (mock `desktop-1e-ledger-actual.png`)

| # | Delta | Status |
|---|---|---|
| 1 | **Tab counts** on each chip: `Actual 456 · Planned 0 · Recurring 27`. Current chips have no numbers. | 📎 `T-R26`/`T-R27`/`T-R28` (weak — `missing-from-plan.md §3.1`) |
| 2 | **Day grouping** with `Tue 27 Oct` header + net sum for the day (transit excluded). Current renders a flat row list sorted by date. | 📎 `T-R26` (weak — `missing-from-plan.md §3.5`) |
| 3 | **Column shape**: mock = `DESCRIPTION + ACCOUNT (stacked) · CATEGORY · DIRECTION · AMOUNT · ⋯`. Current = `DATE · DIRECTION · AMOUNT · CATEGORY · ACCOUNT · DESCRIPTION · ACTIONS`. Column count + order wrong. | ✅ `T-R26` (deliverable) |
| 4 | **Actions collapse into ⋯ menu.** Current renders inline `Edit · Delete` buttons on every row. | ✅ `T-R26` + `T-R18` |
| 5 | **Pagination labels** `← Newer / Older →`. Current shows `Page 1 Next`. | 📎 `T-R26` (weak — `missing-from-plan.md §3.9`) |
| 6 | **FAB removed** from the bottom-right of the table. Current still renders it. | ✅ `T-R58` (Phase 7 cleanup) |
| 7 | **Transit row example**: mock renders `spłata karty · osobiste → karta kredytowa` with the `TRANSIT` pill and `↹ TRANSIT` badge. Current has transit rows (direction=`transit`) but renders them with the generic direction badge. | ✅ `T-R13` + `T-R26` |
| 8 | **Footer** reads `Deleted items are archived and can be restored from ⋯ or Recently deleted.` Current renders no equivalent footer. | ✅ `T-R70` (Recently deleted surface) |
| 9 | Filter row chips present ✓ but segmented chip style not applied; current uses native `<select>` controls. | ✅ `T-R17` |

## `/ledger?view=planned` (mock `desktop-2a-ledger-planned.png`)

| # | Delta | Status |
|---|---|---|
| 10 | **Header summary** right-aligned: `3 items · 3,150.00 PLN over the next 60 days`. Current absent. | ❓ **UNCOVERED** — add bullet to `T-R27` |
| 11 | **Filter chip "Pending ▾"** (status segmented). Current serves generic date-range + category + account + direction filters, no status filter. | ✅ `T-R27` + `T-R16` |
| 12 | **Column shape**: mock = `DUE · DESCRIPTION + ACCOUNT · CATEGORY · AMOUNT · STATUS · (actions)`. Current = `DATE · DIRECTION · AMOUNT · CATEGORY · ACCOUNT · DESCRIPTION · PROMOTED? · ACTIONS` — too many columns, `PROMOTED?` as its own column instead of merging into `STATUS`. | ✅ `T-R27` |
| 13 | **STATUS chip shows `in N days`, red `N days late`, or green `✓ Promoted`.** Current only has a boolean `PROMOTED?` cell. | ✅ `T-R27` |
| 14 | **Overdue row** (e.g. `serwis auto 13 days late`): expense-soft background + red chip + sorted first. Current absent. | ❓ **UNCOVERED** → **U-03** (shared with Today) |
| 15 | **"Already promoted" section** below pending, with `View transaction →` deep link. Current absent. | ❓ **UNCOVERED** → <a id="u-04"></a>**U-04** |
| 16 | **Empty-state card** with headline + description + inline `+ Planned entry` button. Current renders a bare `No planned entries.` line. | ❓ **UNCOVERED** → <a id="u-05"></a>**U-05** |
| 17 | **`+ Add` button in top bar** (chrome-level). Current has a surface-specific `+ Planned entry` button in the title row instead. | ✅ `T-R21` + `T-R27` |
| 18 | **Per-row actions**: mock = `Promote ↩ · Edit · ⋯`. Current = `Edit · Delete`. | ✅ `T-R27` |
| 19 | FAB still present. | ✅ `T-R58` |

## `/ledger?view=recurring` (mock `desktop-1f-ledger-recurring.png`)

| # | Delta | Status |
|---|---|---|
| 20 | **Monthly out / Monthly in summary strip** above table (`Monthly out ≈ 11,886 · Monthly in 27,763 PLN`). Current absent. | 📎 `T-R28` (weak — `missing-from-plan.md §3.19`) |
| 21 | **Grouped `Monthly` / `Yearly` sections** with group headers. Current renders flat, mixed. | ✅ `T-R28` |
| 22 | **Column shape**: mock = `NEXT DUE · DESCRIPTION + ACCOUNT · CATEGORY · AMOUNT · OVERRIDES · (actions)`. Current = `CADENCE · NEXT DUE · ACCOUNT · CATEGORY · DESCRIPTION · AMOUNT · ACTIVE · OVERRIDES · ACTIONS`. | ✅ `T-R28` |
| 23 | **Chevron expand** per row → shows overrides list (date, type Amount/Skipped/Moved, value, Remove). Current absent. | ✅ `T-R28` |
| 24 | **For formula rules, chevron expands into derivation** (signed terms + values + sources linking to their rules). Current absent. | ✅ `T-R28` |
| 25 | **Per-row inline actions**: `Edit · Skip next · ⋯ · chevron`. ⋯ opens: Override next…, Duplicate, Deactivate, Archive rule. Current only renders `Actions` cell with the usual Edit/Delete pair. | ✅ `T-R28` |
| 26 | **"Few actions"** mobile-first collapse (shown in handoff §Ledger · Recurring). Current no mobile branch. | 📎 `T-R28` (weak — `missing-from-plan.md §9`) |
| 27 | FAB still present. | ✅ `T-R58` |

<a id="u-03b"></a>**U-03 note**: overdue styling (background + chip + sort) must be applied consistently on `/today` Upcoming and `/ledger?view=planned`. Add the same acceptance to both `T-R25` and `T-R27`.
