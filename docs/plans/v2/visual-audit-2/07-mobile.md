# 07 · Mobile and Tablet

## Overflow signal table (`overflowingElements` from `/tmp/fe-audit/summary.json`)

| Route | desktop (1440) | tablet (1024) | mobile (375) |
|---|:-:|:-:|:-:|
| `/` | 0 | 0 | 0 |
| `/today` | 0 | 0 | **15** |
| `/ledger` | 0 | **15** | **15** |
| `/ledger?view=actual` | 0 | **15** | **15** |
| `/ledger?view=planned` | 0 | **5** | **9** |
| `/ledger?view=recurring` | 0 | **15** | **15** |
| `/ledger/recently-deleted` | 0 | 0 | **15** |
| `/plan?tab=budget` | 0 | 0 | **15** |
| `/plan?tab=year` | 0 | **15** | 0 (per-category cards shipped via T-R54) |
| `/plan?tab=forecast` | 0 | 0 | 0 |
| `/plan?tab=analytics` | 0 | 0 | 0 |
| `/accounts` | 0 | 0 | **15** |
| `/settings` | 0 | 0 | 0 |
| `/dev/components` | 0 | 0 | 0 |

Overlays all clean (0) at every viewport — because B-03 drops the shell, there's nothing wide to overflow.

## Mobile — layout bugs

### <a id="l-01"></a>L-01 · Mobile tab bar not fixed to viewport bottom

**Severity**: 🐛 LAYOUT. Primary mobile chrome element doesn't anchor.

**Evidence**: `/tmp/fe-audit/mobile_probes2.json` → `mobile_tab_bar` → `mobile_tab_bar_present: false, nav_container_position: static, last_nav_box: { x:0, y:770, w:375, h:42 }`. The `<nav>` renders inside the normal document flow at y=770 (just above the 812 viewport base), with `position: static`. Scrolling moves it with content; it overlaps rows (see `/tmp/fe-audit/mobile__accounts.png` where "Today Ledger [+] Plan Accounts" floats mid-page over the "fundusz awaryjny" row, and `mobile__today.png` where it overlaps the "karta kredytowa" row).

**Mock requires**: `Today · Ledger · [+] · Plan · Accounts` fixed to viewport bottom with centre `+ Add` tap target.

**Fix hint**: `src/budget_planner/web/static/rising-dough.css` — add `@media (max-width: 640px) { .rd-rail__footer { position: fixed; left: 0; right: 0; bottom: 0; z-index: 20; } main { padding-bottom: 72px; } }` (approximate — adjust to the actual markup). This is **T-R51** which is still ◻ in `tasks.md`.

### <a id="l-02"></a>L-02 · Tap targets below 44 px on `/accounts`

**Severity**: 🐛 LAYOUT. Mock + handoff require ≥ 44 px.

**Evidence**: `/tmp/fe-audit/mobile_probes2.json` → `mobile_touch_targets` → 11 interactive elements under 32 px. Specific:
- `Reconcile` button: **80 × 31** (height 13 px short)
- `⋮` kebab: **25 × 24** (both dimensions way short — hard to tap accurately)

**Fix hint**: at mobile breakpoints, the row controls should expand (`min-height: 44px; min-width: 44px`). The kebab is particularly bad — 25×24 is almost unselectable with a thumb.

### <a id="l-03"></a>L-03 · Mobile `/accounts` net-worth hero overlaps ASSETS column

**Severity**: 🐛 LAYOUT.

**Evidence**: `/tmp/fe-audit/mobile__accounts.png` — `52,748.21` headline bleeds into the `ASSETS 56,603.21` number sitting in the same flex row with no wrap.

**Fix hint**: `.fortune-split` (or equivalent) needs `flex-direction: column` or `flex-wrap: wrap` at `max-width: 640px`.

### <a id="l-04"></a>L-04 · Mobile `/accounts` credit-card LIABILITY pill wraps to two lines

**Severity**: 🐛 LAYOUT.

**Evidence**: `/tmp/fe-audit/mobile__accounts.png` — on the `karta kredytowa (mBank)` row, the `CREDIT CARD · LIABILITY` pill wraps vertically, breaking the row header into two visual tiers awkwardly.

**Fix hint**: allow pill to wrap under the account name on narrow widths; drop the `· LIABILITY` suffix on mobile (or render as a second-line sub-pill rather than inline).

### <a id="l-05"></a>L-05 · FAB visible on every table page

**Severity**: 🐛 LAYOUT.

**Evidence**: FAB floats bottom-right on `/accounts`, `/ledger?*`, `/plan?*`, `/ledger/recently-deleted`. On mobile `/accounts` it overlaps a row.

**Fix hint**: T-R58 (Phase 7 cleanup) deletes the FAB after v2 ships. Until then, hide it at mobile with `@media (max-width: 640px) { .fab { display: none; } }` so it doesn't compound the tab-bar overlap problem.

## Mobile — missing design elements

| # | Element | Status |
|---|---|---|
| 1 | **Bottom tab bar fixed to viewport** | 🐛 L-01 + ❌ MISSING (T-R51 ◻) |
| 2 | **Centre `+ Add` in the tab bar as a prominent round button** (mock mobile-1o-today) | ❌ MISSING |
| 3 | **Add bottom sheet** (overlay slides from bottom at ≤ 640 px per T-R52 ✅) | ⚠️ PARTIAL — HTMX overlay opens but visually looks like the desktop slide-over at mobile widths; needs reconfirmation that CSS `transform: translateY` is wired |
| 4 | **Mobile /today Upcoming shows amount + Promote → link per row** | ❌ MISSING — rows render without visible amount/action labels (see `/tmp/fe-audit/mobile__today.png`); category pill appears as empty red dot |
| 5 | **Mobile /today swipe hint copy** `"Swipe right to promote, left to skip. Tap a row to override."` | ❌ MISSING |
| 6 | **Mobile Forecast = 6 representative months stacked** | ❌ MISSING — current renders the SVG chart only; no narrow-screen branch |
| 7 | **Mobile Plan Budget tab strip** scrollable; prevents `Forecast → Forecas` truncation | 🐛 LAYOUT — tabs truncate; `missing-from-plan.md` flagged this; `T-R55` scope only covered Settings tab-bar |
| 8 | **Mobile /today, /ledger, /accounts should hide the left rail entirely** | ❌ MISSING — rail renders inline at the top of main at mobile widths |

## Tablet (1024 px)

Handoff produced **no tablet mocks**. Overflow signals (`15` on Ledger · Actual, Recurring, and Plan · Year) indicate the tablet layout is rendering desktop columns in a narrower viewport, forcing elements wider than 1024. **T-R53** (narrow numeric table scroll wrappers) is marked ✅ but doesn't appear to have shipped for `/ledger?view=actual|recurring` based on these counts.

| Route | Issue |
|---|---|
| `/ledger?view=actual` tablet | 15 elements wider than viewport — table columns + action buttons |
| `/ledger?view=recurring` tablet | 15 — same reason |
| `/plan?tab=year` tablet | 15 — heatmap row width exceeds viewport |

**Fix hint**: wrap the three affected tables in `<div class="table-scroll">` with `overflow-x: auto` + sticky-first-column so the content scrolls horizontally within the main column without triggering viewport-level horizontal scroll. Reconfirm T-R53 acceptance by running `frontend-visual-audit` at 1024 and asserting zero overflow.
