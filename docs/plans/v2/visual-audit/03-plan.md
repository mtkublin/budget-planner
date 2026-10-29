# 03 · Plan

Four tabs under `/plan?tab=`: **Budget · Year · Forecast · Analytics**. Current shell + tab strip + title look match. Everything below the tab strip is still v1 or placeholder.

## `/plan?tab=budget` (mock `desktop-1g-plan-budget.png`)

| # | Delta | Status |
|---|---|---|
| 1 | **Segmented period bar** (spent | committed with diagonal hatch | left) in the period hero. Current renders a plain solid bar. | ❓ **UNCOVERED** → <a id="u-06"></a>**U-06** (also 📎 `T-R20` which ships the primitive) |
| 2 | **Period dates "15 Oct → 7 Nov"** (actual anchor window). Current renders "month of October 2026". ADR-0041 already defines the window. | ❓ **UNCOVERED** → <a id="u-07"></a>**U-07** (also 📎 `T-R22` host) |
| 3 | **Committed figure** displayed in the hero (`402.19 committed · 10 days left`). Current shows only `9 DAYS LEFT`. | ✅ `T-R25` + `T-R22` (period header macro) |
| 4 | **"Change anchor" link** inline in the period card. Current renders `change` link ✓. | 📎 `T-R30` (weak — `missing-from-plan.md §4.2`) |
| 5 | **Override popover** on ⋯: `This month only / Every {month} / New default`, amount input, Save ↩. Current ⋯ cell navigates away to `/budget/overrides/new?category_id=`. | ✅ `T-R30` |
| 6 | **Over-budget rows** show amount in red + bar in red ✓ (matches mock). | ✅ shipped |
| 7 | **Overridden amount styling**: bold + accent underline. Current treats overrides the same as defaults. | 📎 `T-R30` (weak — `missing-from-plan.md §4.7`) |
| 8 | **"Categories without a budget but with spend this month" footnote** under Total. Current merges them into the main table body as 0.00-planned rows. | ❓ **UNCOVERED** → <a id="u-08"></a>**U-08** |
| 9 | **Total remaining definition**: mock shows `1,910.78` (planned − committed). Current shows `2,312.97` (planned − actual). Pick one and document — not a bug yet but worth settling before `T-R30` ships. | ❓ **UNCOVERED** — add decision bullet to `T-R30` |

## `/plan?tab=year` (mock `desktop-1h-plan-year.png`)

Current renders a bare placeholder: *"Heatmap renders once the Year endpoint lands (ADR-0056 §2 / T-R31). Phase 1 placeholder."* No cells, no data.

| # | Delta | Status |
|---|---|---|
| 10 | Entire heatmap grid (12 months × categories, colour intensity by amount, tier markers for one-off / recurring / default / unset). | ✅ `T-R31` + `T-R19` (heatmap cell macro) |
| 11 | Cell edit popover (One-off · {month YYYY} / Every year · {month} / Save ↩ / Reset to default). | ✅ `T-R31` |
| 12 | Row totals + column totals + grand total in `<tfoot>` — conflict open: mock says column totals **not shown**; task plan includes them. | 📎 **CONFLICT** `missing-from-plan.md §4.15` + `T-R31` |
| 13 | Unset categories collapsed into "3 unset" note vs individual dash rows. | 📎 `T-R31` (weak — `missing-from-plan.md §4.16`) |
| 14 | Mobile card layout at ≤640px. | ✅ `T-R54` |

## `/plan?tab=forecast` (mock `desktop-1i-plan-forecast.png`)

| # | Delta | Status |
|---|---|---|
| 15 | **Horizon segmented 6 / 12 / 24 / 60 months** control. Current shows static text `HORIZON: 12 months`. | ✅ `T-R32` + `T-R16` |
| 16 | **Summary strip** above chart: `NOW · 49,775.97 · SEP 2027 · 104,218.31 · PEAK · AUG 2027 · 115,109.45`. Current absent. | 📎 `T-R32`/`T-R48` (weak — `missing-from-plan.md §4.21`) |
| 17 | **Chart annotations** on outliers (`Mar: +43,200 unit8 PROFIT SHARE`, `Sep: 22,195 planned, incl. 16,000 holiday`). Current absent. | ✅ `T-R48` (deliverable; add annotations to acceptance) |
| 18 | **Monthly table inline, not collapsed.** Current wraps it in `<details><summary>▶ Monthly table</summary>`. | ❓ **UNCOVERED** → <a id="u-09"></a>**U-09** (default-open state) |
| 19 | **Inline bar in the Net column** (red/green by sign). Current renders plain numbers. | 📎 `T-R32` (weak — `missing-from-plan.md §4.23`) |
| 20 | **Mobile = 6 representative months** stacked, not full 12. | 📎 `missing-from-plan.md §4.24` — needs new mobile task or `T-R32` mobile branch |
| 21 | **"Oct row comes from Budget summary"** footnote. Current absent. | 📎 `T-R32` (weak — `missing-from-plan.md §4.25`) |

## `/plan?tab=analytics` (mock `desktop-2b-plan-analytics.png`)

| # | Delta | Status |
|---|---|---|
| 22 | **Period control**: ← `[October 2026]` → + segmented `Month · 3 months · YTD · 12 months`. Current absent. | ✅ `T-R33` + `T-R22` |
| 23 | **Bento two-column layout** (Spend-by-category wide left; Income-vs-expense + Largest-items stacked right). Current renders three sections stacked vertically. | ❓ **UNCOVERED** → <a id="u-10"></a>**U-10** |
| 24 | **Spend by category: "vs 12-mo avg" column** with signed red/green delta. Current absent (bar + amount only). | ✅ `T-R33` + `T-R43` (analytics bundle service) |
| 25 | **Category pill labels** on rows. Current renders plain uppercase text. | ✅ `T-R12` + `T-R33` |
| 26 | **Income vs expense chart**: paired bars per month, with legend + "Oct: about +11.2k surplus" copy. Current renders a trailing-12m chart with raw axis labels, no copy. | ✅ `T-R33` + `T-R49` |
| 27 | **Largest single items card**: `name · date | amount` row shape. Current renders raw text list `2026-10-15 PODATKI VAT 5,441.00` with no card chrome. | ✅ `T-R33` + `T-R49` |
| 28 | **Footer copy**: *"Click a category to open its transactions in Ledger. Red means above the 12-month average."* Current absent. | ✅ `T-R33` |
| 29 | **"PLN actual" badge** right of Spend-by-category title. Current absent. | ✅ `T-R33` |
