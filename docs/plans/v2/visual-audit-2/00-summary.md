# 00 · Summary

## Headline

The chrome, token system, macro primitives, navigation shortcuts, and most route-level screens are in place and render the Rising Dough visual language. Everything inside the screens still has significant gaps versus the mocks — day grouping, column shapes, inline interactions, popovers, period hero segmented bar, charts, mobile responsive. **One feature is hard-broken (every Plan · Budget override link 404s)**. Several keyboard + overlay interactions misbehave.

## Totals

| Category | Count |
|---|---|
| 🐛 BLOCKING bugs (dead endpoint, non-functional feature) | **3** |
| 🐛 FUNCTIONAL bugs (interaction wrong outcome) | **5** |
| 🐛 LAYOUT bugs (overlap, clip, responsive) | **5** |
| ❌ MISSING design elements (per-mock delta) | **61** |
| ⚠️ PARTIAL (present but wrong shape) | **14** |

## 🐛 BLOCKING — fix immediately

1. **B-01 · `/budget/overrides/new?category_id=*` returns 404 for every category.** Every row ⋯ on Plan · Budget links to the dead URL. Scanned 16 category hrefs → 16 404s. The entire "Override budget" feature is unreachable. See [`01-bugs-blocking.md#b-01`](01-bugs-blocking.md#b-01).
2. **B-02 · Plan · Year heatmap cells are not clickable.** 246 `<td>` cells rendered, 0 contain a button/link/role=button. Mock requires click → cell-edit popover (One-off · {month YYYY} / Every year · {month} / Reset / Save ↩). Cell edit UX never shipped despite T-R31 marked ✅. See [`04-plan.md#year`](04-plan.md#plan-year).
3. **B-03 · Direct URL navigation to overlay routes still returns bare partials.** `GET /transactions/new`, `GET /accounts/new`, `GET /categories/new`, `GET /recurring/new`, `GET /accounts/{id}/reconcile` all return the raw `_slideover.html` fragment with no `<html><head>`, no CSS. Overlay chrome only renders when triggered via HTMX from the host page. Share links / refresh / open-in-new-tab break. See [`01-bugs-blocking.md#b-03`](01-bugs-blocking.md#b-03).

## 🐛 FUNCTIONAL — wrong outcome

4. **F-01 · Keyboard `g a` does not navigate to /accounts.** `g l`, `g o`, `g p`, `g s`, `[`, `]`, `?` all work. `g a` silently fails. See [`01-bugs-blocking.md#f-01`](01-bugs-blocking.md#f-01).
5. **F-02 · Today "Promote" row action does full-page navigation to `/recurring/{id}/promote?date=…`.** Mock requires inline row-expand with `account | date | amount | Confirm ↩ | Esc`. Current always navigates away.
6. **F-03 · Reconcile slide-over missing "Record as" category selector and "Also save a snapshot" checkbox.** Steps, side-by-side columns, difference callout, previous checks all present ✓. Two controls still absent.
7. **F-04 · Add entry overlay missing Direction segmented (Happened / Planned / Repeats), Fixed/Formula toggle, large amount display, per-day preview, "save and add another".** `/transactions/new` only serves the plain tx form, not the unified add entry per handoff. `/recurring/new` is a separate overlay with its own fields; no shared add surface.
8. **F-05 · Cheatsheet modal renders duplicated "Keyboard shortcuts" section** on first `?` press — second table shows only `Esc Close`. Visual duplicate.

## 🐛 LAYOUT — overlap / clipping / responsive

9. **L-01 · Mobile tab bar NOT fixed to viewport bottom.** `position: static`, `y=770` in document flow at bottom of `<main>`. Scrolls with content; overlaps rows when scrolled. T-R51 still pending.
10. **L-02 · Mobile tap targets below 44 px on /accounts.** `Reconcile` button 80×31, `⋮` kebab 25×24. 11 interactive elements under 32 px.
11. **L-03 · Mobile `/accounts` net worth hero (52,748.21) overlaps the ASSETS column number (56,603.21)** at 375 px. Flex row with no wrap.
12. **L-04 · Mobile `/accounts` credit-card LIABILITY pill wraps to its own line (two lines).** Mock has pill inline with the account name on narrow widths.
13. **L-05 · FAB still present on all table pages** (`/accounts`, `/ledger?*`, `/plan?*`, `/ledger/recently-deleted`). T-R58 (Phase 7 cleanup) pending — but it currently overlaps row content on mobile.

## ❌ MISSING design elements — top of the list

Full list in the per-screen files. Highest-signal:

- **Period hero segmented bar** (spent | committed-hatched | left) on `/today` AND `/plan?tab=budget` — primitive exists in `/dev/components`, screens don't consume it.
- **Date-range grouping in Upcoming** on `/today` ("NEXT 7 DAYS", "5–12 November").
- **Day grouping with net sum** on `/ledger?view=actual`.
- **Monthly / Yearly grouping** on `/ledger?view=recurring` + Monthly in/out summary strip.
- **Tab counts** on every Ledger tab (`Actual 456 · Planned 0 · Recurring 27`) — primitive exists in `/dev/components`.
- **Chevron row-expand → overrides + formula derivation** on `/ledger?view=recurring`.
- **Already-promoted section + overdue row styling** on `/ledger?view=planned` and `/today`.
- **Horizon segmented 6/12/24/60 + Now/End/Peak summary + chart annotations** on `/plan?tab=forecast`.
- **Period segmented (Month / 3mo / YTD / 12mo) + bento two-column layout + "vs 12-mo avg" delta** on `/plan?tab=analytics`.
- **Relative "today / 14 Oct / 14 days ago" chips with colour** on `/accounts` CHECKED column.
- **Credit-card limit / available / used% bar** on `/accounts` liability row.
- **Income-anchor selector + Expense/Income/System grouping + colour source indicator + Archive action** on `/settings` Categories.
- **Mobile tab bar fixed to viewport bottom with centre `+ Add`**.

## Shortlist of claims to verify

The user's upstream claim is "all tasks done". Against `docs/plans/v2/tasks.md`:

- Marked ✅ in `tasks.md` as of this audit: `T-R31, T-R38, T-R39, T-R52, T-R53, T-R54, T-R55, T-R56, T-R65, T-R66, T-R67, T-R69, T-R70` (13 tasks).
- All other `T-R##` tasks still ◻ in `tasks.md`.
- Features that show up on screen but whose task line is still ◻: Rising Dough shell, nav, keyboard shortcuts, every macro primitive, Today reskin, Ledger · Actual columns, Plan · Budget period hero, Plan · Forecast SVG chart, Plan · Analytics bundle, Accounts sparklines + ⋮ menu, Settings tabs, Recently-deleted link, bulk toolbar. **The code shipped faster than the task-tracker was ticked.** This audit treats every delta as a finding regardless of ◻/✅ state.

## Next-step priority

1. Fix **B-01** (override 404). Blocks every budget override action.
2. Wire **B-02** (year cell click → popover). Keystone of Plan · Year.
3. Resolve **B-03** (overlay direct-URL fallback). Breaks sharing/refresh.
4. Patch **F-01** (`g a` shortcut) + **F-04** (overlay unification Happened/Planned/Repeats + Fixed/Formula).
5. Land **T-R51** (mobile tab bar fixed) — blocks half the mobile-layout bugs.
