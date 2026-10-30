# 03 · Ledger

## `/ledger?view=actual` (mock `desktop-1e-ledger-actual.png`)

| # | Element | Status |
|---|---|---|
| 1 | Shell + eyebrow `LEDGER` + title `Everything that happened` + tabs + search | ✅ |
| 2 | **Tab counts** (`Actual 456 · Planned 0 · Recurring 27`) | ❌ MISSING — primitive exists in `/dev/components`, not consumed. Tabs render as `Actual · Planned · Recurring · Next` with no number badges. |
| 3 | Filter chips row (date range, categories, accounts, direction, search) | ✅ |
| 4 | Search input filters rows live (61 → 11 for "takeaway") | ✅ (verified via probe) |
| 5 | **Day grouping with net sum** (`Tue 27 Oct` header + `net -801.9`, transit excluded) | ❌ MISSING |
| 6 | **Row shape**: mock = `DESCRIPTION + account (stacked)` single column + category pill + direction badge + amount + `⋯` | ⚠️ PARTIAL — current column order is `DATE | DIRECTION | AMOUNT | CATEGORY | ACCOUNT | DESCRIPTION | ACTIONS`; description+account not merged |
| 7 | **Actions collapse into `⋯` menu** | ❌ MISSING — current renders inline `Edit · Delete` on every row |
| 8 | **Transit row example** (`spłata karty · osobiste → karta kredytowa · TRANSIT pill · ↹ TRANSIT badge`) | ✅ data present; styling partially matches |
| 9 | **Footer**: `Deleted items are archived and can be restored from ⋯ or Recently deleted.` | ✅ (link to `/ledger/recently-deleted` ✓) |
| 10 | **Pagination labels** `← Newer · Older →` | ⚠️ PARTIAL — current reads `Page 1 Next` |
| 11 | Bulk-select toolbar on row checkbox (`0 selected · Clear · Export CSV · Export Parquet · Delete selected`) | ✅ renders when any row checked |
| 12 | FAB in bottom-right (should be removed per T-R58 Phase 7) | 🐛 LAYOUT **L-05** |

## `/ledger?view=planned` (mock `desktop-2a-ledger-planned.png`)

| # | Element | Status |
|---|---|---|
| 13 | Shell + eyebrow + title `Planned one-offs` + tab chips | ✅ |
| 14 | **Header summary** right-aligned (`3 items · 3,150.00 PLN over the next 60 days`) | ❌ MISSING |
| 15 | **`Pending ▾` status segmented filter** | ❌ MISSING |
| 16 | **Column shape**: mock = `DUE | DESCRIPTION + account | CATEGORY | AMOUNT | STATUS | (actions)` | ⚠️ PARTIAL — current has `DATE | DIRECTION | AMOUNT | CATEGORY | ACCOUNT | DESCRIPTION | PROMOTED? | ACTIONS` (8 cols vs 6) |
| 17 | **STATUS chip** (`in N days` neutral · `N days late` red · `✓ Promoted` green) | ❌ MISSING — current has boolean `PROMOTED?` cell |
| 18 | **Overdue row visual** (expense-soft bg + `N days late` red chip + sorted first) | ❌ MISSING |
| 19 | **"ALREADY PROMOTED" section** with `View transaction →` deep link | ❌ MISSING |
| 20 | **Empty-state card** (headline + description + inline `+ Planned entry`) | ❌ MISSING — current shows bare `No planned entries.` |
| 21 | Per-row actions `Promote ↩ · Edit · ⋯` | ❌ MISSING — current renders `Edit · Delete` |
| 22 | FAB visible | 🐛 L-05 |

## `/ledger?view=recurring` (mock `desktop-1f-ledger-recurring.png`)

| # | Element | Status |
|---|---|---|
| 23 | Shell + eyebrow + title `Standing commitments` + tabs | ✅ |
| 24 | `+ Recurring rule` button + `[ ] switch tab` hint | ✅ |
| 25 | **Monthly out / Monthly in summary strip** (`Monthly out ≈ 11,886 · Monthly in 27,763 PLN`) | ❌ MISSING |
| 26 | **Grouped `Monthly` / `Yearly` sections** with group headers | ❌ MISSING |
| 27 | **Column shape**: mock = `NEXT DUE | DESCRIPTION + account | CATEGORY | AMOUNT | OVERRIDES | (actions)` | ⚠️ PARTIAL — current `CADENCE | NEXT DUE | ACCOUNT | CATEGORY | DESCRIPTION | AMOUNT | ACTIVE | OVERRIDES | ACTIONS` (9 cols vs 6, ACTIONS cell empty) |
| 28 | **Chevron expand** per row → overrides list + formula derivation | ❌ MISSING |
| 29 | **For formula rules**: expansion shows signed terms + values + sources linking to their rules | ❌ MISSING |
| 30 | **Per-row inline actions**: `Edit · Skip next · ⋯ · chevron`; ⋯ opens Override next…, Duplicate, Deactivate, Archive rule | ❌ MISSING — Actions cell appears empty in current render |
| 31 | Footer: `Deleted = archived; restorable from Recently deleted →` | ✅ |
| 32 | FAB visible | 🐛 L-05 |

## `/ledger/recently-deleted` (new route, T-R70 ✅)

Mock reference: handoff spec `03-screen-specs.md` + handoff diff `missing-from-plan.md`. No standalone mock PNG.

| # | Element | Status |
|---|---|---|
| 33 | Shell + eyebrow `LEDGER` + title `Recently deleted` + `← Ledger` back link | ✅ |
| 34 | Explanatory copy: `Soft-deleted items from the last 90 days...` | ✅ |
| 35 | Three sections `Transactions · 0 / Planned · 0 / Categories · 2` | ✅ |
| 36 | Categories table: `DELETED | NAME | DIRECTION | Restore` with timestamps + Restore button | ✅ |
| 37 | FAB visible on this page too | 🐛 L-05 |

## Bulk toolbar (T-R69 ✅)

Verified: on `/ledger?view=actual`, checking any row checkbox renders a header toolbar `0 selected · Clear · Export CSV · Export Parquet · Delete selected`. ✓

**But the ↑ label `0 selected` is odd** when 1 row is checked — needs to update the counter dynamically after each check/uncheck. Not probed deeply, but visible in the screenshot after one check: label says `0 selected`.

| Element | Status |
|---|---|
| Toolbar appears on any row-level checkbox check | ✅ |
| Counter updates to reflect number of selected rows | ❌ MISSING (shows `0` even after a check — needs verification; could be a label bug) |
| Export CSV action link | ✅ `/transactions/export?format=csv` → 200 |
| Export Parquet action link | ✅ `/transactions/export?format=parquet` → 200 |
| Delete selected (bulk soft-delete) | not probed — would mutate DB |
