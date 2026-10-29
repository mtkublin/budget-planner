# 07 · Mobile & Tablet

Everything in this file is already Phase 6 scope (`T-R51..T-R56`) **unless flagged 🐛**. The 🐛 rows are regressions on the current build — not "mobile is pending" — and should be filed independently.

## Signal table

Re-stated from the audit summary for convenience:

| Route | tablet overflow | mobile overflow |
|---|:-:|:-:|
| `/today` | 0 | **20** |
| `/ledger?view=actual` | **20** | **20** |
| `/ledger?view=planned` | **5** | **9** |
| `/ledger?view=recurring` | **20** | **20** |
| `/plan?tab=budget` | 0 | **20** |
| `/plan?tab=year` | **7** | **20** |
| `/plan?tab=forecast` | 0 | **7** |
| `/plan?tab=analytics` | 0 | **5** |
| `/accounts` | 0 | **20** |
| `/settings` | 0 | 0 |

All overlay routes (`/accounts/new`, `/categories/new`, `/transactions/new`, `/recurring/new`, `/accounts/1/reconcile`) are clean because the bare-partial bug drops the shell — see [bug B-01](08-bugs.md#b-01).

## Shell-level observations

| # | Observation | Status |
|---|---|---|
| 1 | **Left rail stays in document flow at 375 px.** Causes most of the Today / Plan / Accounts overflow signals. Mock has no rail on mobile — tab bar at bottom instead. | ✅ `T-R51` |
| 2 | **Bottom tab bar not fixed to viewport.** `Today · Ledger · [+] · Plan · Accounts` labels appear mid-page over the current scroll offset. Floats on top of other content. | 🐛 **B-03** |
| 3 | **FAB stays visible on all table routes** on both desktop and mobile. On mobile it overlaps row content. | 🐛 **B-02** (position) + ✅ `T-R58` (removal) |
| 4 | **Table overflow at tablet (1024 px)**: `/ledger?view=actual|recurring` already exceed the viewport width before responsive wrappers land. | ✅ `T-R53` (narrow numeric table scroll wrappers) |

## Per-screen mobile deltas (brief)

See the per-screen files for the full delta list. Only mobile-specific additions below.

### `/today` mobile — mock `mobile-1o-today.png`

- Hero card with large serif number, segmented bar, Can-I-afford input, net-worth bottom card, bottom tab bar. ✅ `T-R51` + `T-R25`.
- Swipe hint copy: *"Swipe right to promote, left to skip. Tap a row to override."* ❓ **UNCOVERED** — add to `T-R51`.

### `/ledger` mobile — mock `mobile-1p-ledger.png`

- Mocks for actual only. Planned + recurring mobile missing per `missing-from-plan.md §9`.
- Each row = description + account + category pill + amount, no action buttons visible (actions behind long-press or ⋯?). Needs an explicit spec. ✅ host `T-R51`/`T-R26`, 📎 planned/recurring mobile branches.

### `/plan?tab=budget` mobile — mock `mobile-1q-plan-budget.png`

- Tab chips at the top wrap or scroll horizontally; mock cuts off `Forecas…` cleanly with a fade. Current truncates mid-word with no fade. 🐛 **B-06**.
- Period hero stacks (anchor info → day left → bar). ✅ `T-R51` + `T-R30`.

### `/plan?tab=year` mobile — mock `mobile-1q-plan-budget.png` lower half

- Heatmap replaced by **per-category horizontal strip cards**. ✅ `T-R54`.

### `/plan?tab=forecast` mobile — mock `mobile-1r-plan-forecast.png`

- 6 representative months stacked, not 12. 📎 `missing-from-plan.md §4.24` — needs mobile forecast task.

### `/accounts` mobile — mock `mobile-1s-accounts.png`

- Overlap bugs on hero / pill / FAB called out individually in [08-bugs.md](08-bugs.md).
- Rows show account + sparkline + checked chip. txn count dropped. ✅ `T-R51` + `T-R34`.

### Create overlays mobile

- Overlays sheet from the bottom instead of sliding from the right at ≤640 px. ✅ `T-R52`.
- Direction segmented control deleted (direction derived from category). ⚠️ **conflict**: mock `mobile-1t-add-sheet.png` still shows Expense/Income/Transit segmented control. 📎 `missing-from-plan.md §6.8`.

## Tablet (1024 px)

Handoff produced **no tablet mockups**. Current app renders desktop-with-narrower-columns at 1024, which triggers the overflow signals on `/ledger?view=actual|recurring` and `/plan?tab=year`.

📎 `missing-from-plan.md §9` already flags this: decide between (a) document "tablet = desktop with narrower columns" in an ADR amendment, or (b) commission tablet mocks before Phase 3 lands.
