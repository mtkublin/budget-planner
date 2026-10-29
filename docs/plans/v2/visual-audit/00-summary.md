# 00 · Summary

## Headline

- **Desktop shell + nav** reskinned to Rising Dough (wordmark, hairline rail, keyboard shortcut chips). ✓
- **Accounts (`T-R34`, `T-R67`)**: closest-to-mock screen; sparklines + ⋯ menu + liability pill present. Still missing: credit-card utilisation bar, relative "checked X days ago" chips, sort-by-balance order.
- **Reconcile (`T-R39` ✅)**, **Create account (`T-R65` ✅)**, **Create category (`T-R66` ✅)** render the Rising Dough chrome **only inside the HTMX overlay**. Direct URL navigation returns a bare partial with zero shell CSS — see [bug B-01](08-bugs.md#b-01).
- **Everything else** (Today hero, Ledger row shape + grouping, Plan Budget period card, Plan Year, Plan Forecast chart, Plan Analytics bento, Settings grouping) still runs the v1 shape underneath the new chrome.
- **Mobile** has no mock-matching layout anywhere. Desktop rail stays in flow, FAB overlaps content, nav labels float mid-page. All of this is covered by Phase 6 (`T-R51..T-R56`) but see bugs below for the ones that are regressions rather than "not built yet".
- **FAB** still present on `/ledger*`, `/plan*`, `/accounts` — scheduled for removal at `T-R58` (Phase 7). Not a new bug, but worth noting it is still on screen at 2026-10-29.

## Totals

| Category | Count |
|---|---|
| Deltas vs mocks | 72 |
| ✅ Covered by a task | 46 |
| 📎 Covered weak (missing-from-plan.md flagged) | 11 |
| ❓ **UNCOVERED** — needs plan edit | 10 |
| 🐛 **BUG** — regression / defect | 7 |

## ❓ UNCOVERED items (need a plan edit before Phase 3 lands)

Each of these has no row in `tasks.md`, no bullet in `missing-from-plan.md`, and no ADR hit. All are design elements visible in the mocks that no current task promises.

1. **U-01 — `/today` row-expand-in-place Promote UX.** Mock 1d: tapping a row expands it inline into editable `account | date | amount | Confirm ↩ | Esc`. `T-R25` says "Promote / Skip / Override" are per-row actions but does not call out the expand-in-place pattern. See [01-today-and-home.md](01-today-and-home.md#u-01).
2. **U-02 — `/today` Upcoming "Showing N of M · open in Ledger" footer cap.** Mock shows a 6-row cap with footer link. `T-R25` deliverables and `missing-from-plan.md §2.11` both describe grouping but not the cap+link. See [01](01-today-and-home.md#u-02).
3. **U-03 — Overdue row visual treatment** (`expense-soft` background + "N days late" red chip + sorted first). Needed on `/today` Upcoming **and** `/ledger?view=planned`. `T-R14` ships the `overdue_chip` macro; nothing wires the row background or ordering. See [01](01-today-and-home.md#u-03) + [02](02-ledger.md#u-03b).
4. **U-04 — `/ledger?view=planned` "Already promoted" section** + "View transaction →" deep link. Mock 2a shows a divider with promoted items below pending ones. `T-R27` does not include it. See [02](02-ledger.md#u-04).
5. **U-05 — `/ledger?view=planned` empty-state card** with description + inline `+ Planned entry` button. `T-R27` shows an empty state but copy + card chrome unspecified. See [02](02-ledger.md#u-05).
6. **U-06 — `/plan?tab=budget` segmented spent | committed | left period bar.** Mock 1g shows a 3-segment stacked bar (committed uses diagonal hatch). `T-R20` ships `progress_bar` with hatch; `T-R30` uses it for category rows but not for the period hero. See [03](03-plan.md#u-06).
7. **U-07 — `/plan?tab=budget` period dates header "15 Oct → 7 Nov" (actual anchor window)** rather than "month of October 2026". The anchor window is already in ADR-0041; the display string needs to flow through `period_header` (`T-R22`). See [03](03-plan.md#u-07).
8. **U-08 — `/plan?tab=budget` "Categories without a budget but with spend" footnote.** Mock 1g pulls KOSZTY STAŁE / PODATKI / OPŁATY BANKOWE **out** of the main table into a note under the Total row. Current renders them as 0.00-planned rows in the body. `T-R30` doesn't call this out. See [03](03-plan.md#u-08).
9. **U-09 — `/plan?tab=forecast` monthly table rendered inline** (not inside a `<details>` disclosure). Mock 1i has it visible; current collapses it. `T-R32`/`T-R48` describe the SVG + fallback but not the default-open state. See [03](03-plan.md#u-09).
10. **U-10 — `/plan?tab=analytics` bento two-column layout** (Spend-by-category wide left, Income-vs-expense + Largest-items stacked right). `T-R33` lists the three charts but no layout spec; current renders them stacked vertically. See [03](03-plan.md#u-10).

## 🐛 BUGS (regressions / defects to file independently of the redesign)

Each is a concrete fix the designer did not change — these are current-code issues worth logging in `docs/CHANGELOG.md` or a bugs tracker.

1. **B-01 — Direct URL navigation to overlay routes renders bare partial.** `GET /accounts/new`, `GET /categories/new`, `GET /accounts/{id}/reconcile`, `GET /transactions/new`, `GET /recurring/new` all return the slide-over/form fragment with no `<html><head>` and therefore no CSS. Expected: either render into the shell on first load or server-side redirect to the host route with the overlay auto-opened. See [08-bugs.md#b-01](08-bugs.md#b-01).
2. **B-02 — Mobile FAB overlays table rows on `/accounts`.** The FAB sits mid-viewport and covers the "fundusz konserwatyny (mBank)" row. Position should be `position: fixed; bottom: ...` with sufficient clearance; today it is anchored at the end of a non-scrolling container.
3. **B-03 — Mobile nav labels float mid-content on `/accounts` and `/plan?tab=budget`.** Rising Dough bottom tab bar appears in flow at mid-page instead of fixed to viewport bottom. Suggests `.rd-rail` responsive breakpoint not wired. (Related to Phase 6 but this specific "nav text sitting in content" is a layout bug, not just "mobile not built".)
4. **B-04 — Mobile `/accounts` net worth hero overlaps ASSETS column.** `52,748.21` headline bleeds into `56,603.21` to its right at 375 px because the two live in the same flex row without wrap.
5. **B-05 — Mobile `/accounts` credit-card `LIABILITY` pill clips off right edge.** Pill is horizontally positioned past viewport width.
6. **B-06 — `/plan?tab=budget` mobile tab-strip truncates "Forecast" to "Forecas".** Tabs row has no horizontal scroll wrapper; the fourth tab bleeds past viewport. (`T-R55` covers Settings tab-bar scroll but not Plan tabs.)
7. **B-07 — `/` (home) still renders legacy "Overview" dashboard** (title: `Overview · Budget Planner`). `T-R06` promises `/today` as the canonical landing route with `/` as a 302 redirect; `/` currently serves a full dashboard template that neither matches v1 Overview nor the Today mock. Also means `grep "Budget Planner" src/budget_planner/web/templates` is not empty (`T-R05` acceptance would currently fail).

## Shortlist for the next planning pass

If you want the smallest batch of plan edits before Phase 3 implementation starts:

- Resolve the three Phase-0 decisions (`T-R71..T-R73`) — they already gate everything downstream.
- Add bullets to `T-R25` for U-01 / U-02 / U-03.
- Add bullets to `T-R27` for U-04 / U-05, and to `T-R26`/`T-R27`/`T-R28` for overdue styling (U-03).
- Add bullets to `T-R30` for U-06 / U-07 / U-08, and to `T-R32` for U-09, and to `T-R33` for U-10.
- File B-01 as its own ticket — it is a correctness regression, not a redesign item, and it affects three already-shipped overlays (`T-R39`, `T-R65`, `T-R66`).
- File B-02 / B-04 / B-05 / B-06 under their respective Phase-6 tasks as explicit acceptance checks (they would otherwise be considered "part of mobile not built" and ignored).
- File B-07 against `T-R05` + `T-R06` so the rename + redirect ship as a single bundle.
