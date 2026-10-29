# 04 · Plan

Four tabs: Budget · Year · Forecast · Analytics. Shell + tab strip + tab title all match. Content inside each tab still varies vs mock.

## Plan · Budget (mock `desktop-1g-plan-budget.png`)

| # | Element | Status |
|---|---|---|
| 1 | Shell + eyebrow `PLAN` + title `October budget` | ✅ |
| 2 | Tabs `Budget · Year · Forecast · Analytics` + period picker `October 2026` | ✅ |
| 3 | **Period hero** `PERIOD · 15 Oct → 7 Nov · anchor: WYPŁATA · change` | ⚠️ PARTIAL — current shows `month of October 2026` instead of anchor-window dates |
| 4 | **Period hero segmented bar** `spent | committed-hatched | left` | ❌ MISSING — current renders a plain solid bar; `Progress` macro exists in `/dev/components` |
| 5 | Hero right: `257.00 PLN / DAY · 9 DAYS LEFT` | ✅ |
| 6 | **Committed figure** in hero (`402.19 committed · 10 days left`) | ❌ MISSING |
| 7 | Change-anchor link | ✅ |
| 8 | Category table `CATEGORY | PLANNED | ACTUAL | USED | REMAINING | ⋯` | ✅ |
| 9 | Over-budget rows styled red (bar + remaining text) | ✅ |
| 10 | **Overridden amount** rendered bold + accent underline | ❌ MISSING — overrides unreachable anyway (B-01) |
| 11 | **`⋯` row kebab opens popover** `This month only / Every {month} / New default · amount · Save ↩` | 🐛 **B-01** — full-page nav to `/budget/overrides/new?category_id=X` → **404 Not Found** |
| 12 | **"Categories without a budget but with spend this month" footnote** under Total | ❌ MISSING — current merges KOSZTY STAŁE / OPŁATY BANKOWE / PODATKI as 0.00-planned rows in the table body |
| 13 | Total row | ✅ |
| 14 | FAB visible | 🐛 L-05 |

## <a id="plan-year"></a>Plan · Year (mock `desktop-1h-plan-year.png`)

**T-R31 marked ✅** — heatmap now renders. But cells are not clickable (**B-02**) and tier markers are not applied.

| # | Element | Status |
|---|---|---|
| 15 | Shell + eyebrow + title `Budget 2026` + year picker `← 2026 →` | ✅ |
| 16 | Explanatory copy `One off and recurring blocked tiers overlay the default per ADR-0056. Click a cell to edit on the budget tab.` | ⚠️ PARTIAL — current says "Click a cell to edit on the budget tab" but cells aren't clickable (**B-02**) |
| 17 | **Heatmap grid** 12 months × categories with sqrt-scaled intensity (cap 1,600) | ✅ renders values; colour intensity varies per category |
| 18 | **Cell click → popover** (One-off · {month YYYY} / Every year · {month} / Reset to default / Save ↩) | 🐛 **B-02** |
| 19 | **Tier markers**: one-off bold+accent outline · recurring italic+hatch · default plain · dash unset | ❌ MISSING — all cells render as plain text |
| 20 | **Row totals + column totals + grand total in `<tfoot>`** | ⚠️ PARTIAL — row totals ✓, grand total ✓, column totals missing (noted as a `missing-from-plan.md §4.15` **CONFLICT** — mock says drop column totals) |
| 21 | **Unset categories collapsed into "N unset" note** vs individual dash rows | ❌ MISSING |
| 22 | Mobile = per-category horizontal strip cards (T-R54 ✅) | partially verified — at 375 px different layout triggers, see 07-mobile.md |

## Plan · Forecast (mock `desktop-1i-plan-forecast.png`)

| # | Element | Status |
|---|---|---|
| 23 | Shell + eyebrow + title `Projected balance` + tabs + period picker | ✅ |
| 24 | **Horizon segmented** `6 / 12 / 24 / 60 months` | ❌ MISSING — current reads `HORIZON: 12 months` as static text |
| 25 | **Summary strip** `NOW: 49,775.97 · SEP 2027: 104,218.31 · PEAK · AUG 2027: 115,109.45` | ❌ MISSING — current only writes `NOW: Oct 2026 · HORIZON: 12 months · PLN budget overlay on` |
| 26 | **SVG line + area chart** | ✅ (T-R48 shipped) |
| 27 | **Chart annotations on outliers** (`Mar: +43,200 unit8 PROFIT SHARE`, `Sep: 22,195 planned, incl. 16,000 holiday`) | ❌ MISSING |
| 28 | **Monthly table inline below chart** | ❌ MISSING — current wraps it in `<details><summary>▶ Monthly table</summary>` collapsed |
| 29 | **Table columns**: `MONTH | INCOME | EXPENSES | PLANNED BUDGET | NET (inline bar) | END OF MONTH` | ⚠️ PARTIAL — once expanded, columns correct; **inline bar in Net column missing** |
| 30 | **"Oct row comes from Budget summary"** footnote | ❌ MISSING |
| 31 | Current month row sourced from Budget summary (so both pages agree) | not verified — needs manual cross-check |

## Plan · Analytics (mock `desktop-2b-plan-analytics.png`)

| # | Element | Status |
|---|---|---|
| 32 | Shell + eyebrow + title `Where it went` + tabs + period picker | ✅ |
| 33 | **Period segmented** (`Month · 3 months · Year to date · 12 months`) | ❌ MISSING |
| 34 | **← [October 2026] → month nav** | ❌ MISSING |
| 35 | **Bento two-column layout** (Spend-by-category wide left; Income-vs-expense + Largest items stacked right) | ❌ MISSING — current renders three sections stacked vertically |
| 36 | **Spend by category** rows: category pill + horizontal bar + amount + `vs 12-mo avg` signed red/green delta | ⚠️ PARTIAL — only plain blue bars + amounts; **no pill labels (plain uppercase text), no delta column** |
| 37 | `5,595.00 PLN actual` badge right of card title | ❌ MISSING |
| 38 | **Income vs expense** paired bars + legend + `Oct: about +11.2k surplus` copy | ⚠️ PARTIAL — chart renders ("Income vs expense trailing 12m") but axis labels truncated, no copy |
| 39 | **Largest single items** card: `name · date | amount` row shape | ⚠️ PARTIAL — list present but renders as raw text `2026-10-15 PODATKI VAT 5,441.00`, no card chrome, no pill, no padding |
| 40 | **Footer**: `Click a category to open its transactions in Ledger. Red means above the 12-month average.` | ❌ MISSING |
| 41 | Row click → Ledger filtered by that category + period | not probed (depends on 36 being wired) |
