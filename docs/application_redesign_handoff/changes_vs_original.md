# Rising Dough — changes vs. the original application

Compared against the 39 audit screenshots (desktop 1440, tablet 1024, mobile 375), `README.md` and `visual-audit-findings.md`.
Mockup ids (1a–1t, 2a–2e) refer to `Rising Dough Redesign.dc.html`.

Legend: **Added** = not in the original · **Changed** = exists, treated differently · **Moved/Merged** = same function, new place · **Removed / not carried over** = in the original, absent from the mockups (flagged so nothing is lost silently).

---

## 1. Global

| # | Area | Original | Redesign | Type |
|---|---|---|---|---|
| 1.1 | Product name | "Budget Planner" | **Rising Dough** | Changed |
| 1.2 | Tagline / footer | "LOCAL-FIRST" under the logo; footer "BUDGET PLANNER · local-first" on every page | Removed everywhere. No footer. | Removed |
| 1.3 | Navigation | Overview, Ledger, Accounts, Budget, Forecast (+ Settings at bottom). Transactions and Analytics reachable only by URL. | **Today, Ledger, Plan, Accounts** (+ Settings at bottom) | Merged |
| 1.4 | Nav labels | None | Keyboard hint on each item (`g o`, `g l`, `g p`, `g a`, `g s`) | Added |
| 1.5 | Active nav item | Blue left bar on blue-grey fill | Indigo left bar on neutral sunk fill | Changed |
| 1.6 | Quick add | Floating blue "+" button, bottom right. It overlapped table content (visible on Ledger, Recurring, Overview). | Persistent **+ Add** button with `n` hint in the top bar; on mobile a raised centre tab. FAB removed. | Changed |
| 1.7 | Global search | Search only inside Ledger filters | Search / jump field with ⌘K in the top bar (palette designed, flagged as deferred) | Added |
| 1.8 | Page header | Eyebrow + large serif title + subtitle (date or count) | Same pattern kept; titles rewritten to state purpose ("Today", "Everything that happened", "Standing commitments", "Where it went") | Changed |
| 1.9 | Visual language | Editorial base: warm paper, serif titles, mono amounts, **blue** accent (#0b5fc4-like), blue-grey fills, grey cards with soft shadows | Same base, tightened: warm paper, hairline-first, no card shadows, **indigo** accent, OKLCH tokens, one overlay shadow only | Changed |
| 1.10 | Typography | Serif titles, system sans body, mono amounts (large, heavy in places) | Newsreader (display), Hanken Grotesk (body), IBM Plex Mono (amounts, tabular). Currency code is a muted suffix. | Changed |
| 1.11 | Direction badges | Text-only coloured pills (EXPENSE / INCOME / TRANSIT) | Glyph + label badges (↓ Expense, ↑ Income, ⇄ Transit, ± Adjust) so colour is never the only cue | Changed |
| 1.12 | Category pills | Saturated pills; override colours (magenta, cyan, violet, gold) applied at full strength | Tinted pills derived from one hue (`oklch(.94 .045 H)` + dark text), consistent contrast | Changed |
| 1.13 | Amount format | "356.70 PLN" at body size, currency same weight | Mono tabular, muted currency suffix, sign shown (− / +), ƒ chip for formula-derived amounts | Changed |
| 1.14 | Foreign-currency disclosure | Not visible in screenshots | Pattern specified: "≈ 412.10 PLN · 1 EUR = 4.2936 (28 Oct)" | Added |
| 1.15 | Motion | None specified | 120–180 ms state motion (promote collapse, hero count, overlay rise); off under reduced-motion | Added |
| 1.16 | Keyboard model | `g o/l/a/b/f/s`, `[ ]`, `n`, `/`, ⌘K, `?`, Esc | `g o/l/p/a/s`, `[ ]`, `n`, `/`, ↑↓, ↵, ⇧↵ (promote all due), `?`, Esc; `g b` / `g f` suggested as aliases to Plan | Changed |
| 1.17 | Accessibility | Colour-only cues in places (overdue muted italic, red/green numbers) | Colour + glyph + text on every state; contrast targets documented (body 15:1, muted 5.2:1, pills ≥ 4.8:1) | Changed |
| 1.18 | Tablet layout (1024) | Screenshots exist for all 13 routes | **No tablet mockups.** Breakpoint rules are written in `06-implementation-notes.md` only. | Not carried over |

---

## 2. Overview → Today (1d, mobile 1o)

| # | Original | Redesign | Type |
|---|---|---|---|
| 2.1 | Title "Overview", date subtitle | Title "Today", date as eyebrow | Changed |
| 2.2 | Three separate panels: Fortune (accounts list), This month (budget), Upcoming | Hero + net-worth card on top, Upcoming below; one decision surface | Merged |
| 2.3 | Budget headline led with **1,910.78 PLN** (left in period); 191.08 PLN/day was small secondary text | **191.08 PLN / day** is the 96px hero; 1,910.78 left and "10 days until next income" sit underneath | Changed |
| 2.4 | Pace shown as small "on track" pill, blue progress bar for spent only | Pace tag top-right of hero; **segmented bar**: spent / committed (hatched) / left, with legend and amounts | Changed |
| 2.5 | "402.19 PLN committed (recurring + planned)" and "spent 5,595.00 PLN of 7,907.97 PLN · 10 days left" as text lines | Same numbers in the bar legend; "10 days left" in the hero line | Changed |
| 2.6 | Paycheck window implicit ("10 days left") | Explicit line: "Period 15 Oct → 7 Nov · day 14 of 24" with anchor named | Added |
| 2.7 | Large empty area in the "This month" card (about 400px of whitespace) | Filled by hero + affordability check | Changed |
| 2.8 | — | **"Can I afford it?"** inline calculator: enter an amount, see the new per-day figure and the delta | Added |
| 2.9 | Fortune panel: Assets, Liabilities, Net worth, then all 10 accounts with type tag, currency tag, balance | Net-worth card: net worth, assets, liabilities, and the **six largest** balances; link to "All 10 accounts" | Changed |
| 2.10 | Links "See forecast →", "Budget breakdown →" | "All 10 accounts →", "Forecast →" | Changed |
| 2.11 | Upcoming: flat list, 24 rows in 30-day view, each with Promote / Skip / Override | Grouped by "Next 7 days", "5 – 12 November"; capped at six rows with "Showing 6 of 24 · open in Ledger" | Changed |
| 2.12 | Promote opened a modal | **Inline confirm**: row expands in place (account, date, amount) with Confirm ↵ / Esc | Changed |
| 2.13 | — | **Promote all due** (⇧↵) button | Added |
| 2.14 | Row: date, name, amount, three buttons | Row adds account, category pill, ƒ marker for formulas; buttons are Promote / Skip / Override | Changed |
| 2.15 | Overdue: italic, muted, small "overdue" chip | Solid red "N days late" chip, tinted row, sorted first (shown in Planned 2a) | Changed |
| 2.16 | "+ Planned" and "+ Recurring" buttons | Kept as small buttons in the Upcoming header | Kept |
| 2.17 | `na osobiste` upcoming amount shown as **−2,781.34 PLN**; Recurring tab shows 15,650.66 PLN | Mockups use **15,650.66** (Recurring value). The original screens disagree with each other; needs a data check. | Flag |
| 2.18 | Mobile: not designed | Hero, affordability row, five upcoming rows with "Promote ›", swipe hint, net-worth card, bottom tab bar | Added |

---

## 3. Ledger

### 3.1 Shared (all tabs)
| # | Original | Redesign | Type |
|---|---|---|---|
| 3.1 | Tabs Actual / Planned / Recurring | Same three tabs, now with counts (456 / 0→3 / 27) and `[ ]` hint | Changed |
| 3.2 | Filter row: two native date inputs, category select, account select, search | Chip row: date-range chip, category, account, direction (new), search with `/` hint | Changed |
| 3.3 | Separate **Transactions** page with filters, bulk actions, export (CSV/Parquet) | Folded into Ledger · Actual. Bulk toolbar and export appear on selection (described in docs, **not drawn**) | Merged |
| 3.4 | Add via FAB | Add in top bar | Changed |

### 3.2 Actual (1e, mobile 1p)
| # | Original | Redesign | Type |
|---|---|---|---|
| 3.5 | Flat table: date, direction, amount, category, account, description, Edit/Delete as stacked text | Grouped **by day** with day header and net (transit excluded) | Changed |
| 3.6 | Columns: Date · Direction · Amount · Category · Account · Description · Actions | Description with account beneath · Category pill · Direction badge · Amount · ⋯ | Changed |
| 3.7 | Amount wrapped onto two lines ("175.50 / PLN") | Single-line right-aligned mono amount, signed | Changed |
| 3.8 | Edit / Delete visible as two stacked links | ⋯ menu; "Deleted items are archived and restorable" with a Recently-deleted link | Changed |
| 3.9 | Pagination "Page 1 Next" | "← Newer / Older →" | Changed |
| 3.10 | Mobile: not designed | Two-line cards under day headers, filter chips, tab bar | Added |

### 3.3 Planned (2a) — *new mockup*
| # | Original | Redesign | Type |
|---|---|---|---|
| 3.11 | Empty table "No planned entries." Columns: Date, Direction, Amount, Category, Account, Description, Promoted?, Actions | Populated design: due, description + account, category, amount, status, actions | Changed |
| 3.12 | "Promoted?" column | Status: "in N days", red "N days late", or ✓ Promoted with link to the transaction | Changed |
| 3.13 | — | Pending / promoted sections, empty-state card with "+ Planned entry" | Added |
| 3.14 | — | **All three planned items and the promoted dentist visit are invented** (the real data has none) | Flag |

### 3.4 Recurring (1f)
| # | Original | Redesign | Type |
|---|---|---|---|
| 3.15 | Flat table with Cadence, Next due, Account, Category, Description, Amount, Active, Overrides, Actions | Grouped under **Monthly / Yearly** headings; Cadence and Active columns removed (cadence = group, Active = filter) | Changed |
| 3.16 | Overrides as "▶ 0 overrides" accordion toggle | Count column + chevron; expanded panel lists each override with its own Remove | Changed |
| 3.17 | Actions: single ⋮ kebab, nothing visible | **Edit** and **Skip next** one-click; ⋯ holds Override next…, Duplicate, Deactivate, Archive rule; chevron expands | Changed |
| 3.18 | Formula amounts: small ƒ chip only | Expanded **derivation**: signed terms with values summing to the result ("na osobiste = 20,945.45 − 2,757.34 − 2,513.45 − 24.00 = 15,650.66") | Added |
| 3.19 | — | "Monthly out ≈ 11,886 · Monthly in 27,763 PLN" summary line | Added (**computed by me, verify**) |
| 3.20 | Overrides on unit8 wypłata: "3 overrides" (contents not visible) | Three override rows shown (Dec amount, Jan skipped, Feb moved) | Added (**contents invented**) |
| 3.21 | Account name wrapped over 3 lines | Single line under rule name | Changed |
| 3.22 | Bold next-due date on unit8 wypłata (anchor) | Anchor noted in text ("income anchor"), row highlighted when expanded | Changed |

---

## 4. Budget → Plan

Original `/budget` was one very long page with four stacked sections. It becomes the **Plan** area with tabs **Budget · Year · Forecast · Analytics**.

### 4.1 Budget (1g, mobile 1q)
| # | Original | Redesign | Type |
|---|---|---|---|
| 4.1 | Title "Plan · spend · breakdown" | "October budget" with **← October 2026 →** switch (replaces year field + month select + "Go") | Changed |
| 4.2 | Hero "Left to spend per day 191.08 PLN" | Slim period card: anchor, segmented bar, per-day, committed, days left, "change anchor" link | Changed |
| 4.3 | Section 1 "Monthly summary": Category, Planned, Actual, Avg/mo, YTD avg, Δ prev, bar, Remainder | Category, Planned, Actual, Used bar, Remaining | Changed |
| 4.4 | Avg/mo, YTD avg, Δ prev columns | **Not on Budget.** Average comparison moved to Analytics ("vs 12-mo avg"); YTD avg and Δ prev not carried over. | Removed / partly moved |
| 4.5 | Section 2 "Rules": separate table of inline-editable defaults with Save and Override… buttons | **Merged into the summary**: click Planned to edit the default; ⋯ opens Override | Merged |
| 4.6 | Override… button per category | Override popover: **This month only / Every {month} / New default**, amount, Save ↵ | Changed |
| 4.7 | Over-budget remainders in red, tier bold style only in yearly grid | Over-budget in red with bar turning red; overridden planned amount marked bold + accent underline | Changed |
| 4.8 | Categories with spend but no budget (KOSZTY STAŁE, PODATKI, OPŁATY BANKOWE) at the bottom of the table | Called out below the total as a note | Changed |
| 4.9 | Total row | Kept (7,907.97 / 5,595.00 / 1,910.78) | Kept |
| 4.10 | Mobile: not designed | Category cards with pill, "N left", bar, spent / of planned | Added |

### 4.2 Yearly grid (1h, mobile 1q)
| # | Original | Redesign | Type |
|---|---|---|---|
| 4.11 | 12 plain numeric columns; text inputs with visible labels in each cell ("INNE Jan 2026"); overflowed to 1980–2075px with no scroll wrapper (audit finding) | **Heatmap** fitting 1280px; colour intensity = amount; no overflow | Changed |
| 4.12 | Tier encoded only by bold / italic / plain, explained in a footnote | Legend row above grid, plus **outline = one-off, hatch + italic = every year, plain = default, dash = unset** | Changed |
| 4.13 | Year input + Go button | ← 2026 → switch | Changed |
| 4.14 | Cell editing: always-visible inputs | Click a cell: popover with amount, **One-off / Every year** switch, Save ↵, Reset to default | Changed |
| 4.15 | Row totals (6,000.00 PLN etc.) | Row totals kept; column totals not shown | Changed |
| 4.16 | Unset categories shown as rows of dashes (KOSZTY STAŁE, OPŁATY BANKOWE, PODATKI) | Collapsed into "3 unset" note | Changed |
| 4.17 | Sep WAKACJE I WYJAZDY = 16,000 (real one-off) | Kept | Kept |
| 4.18 | — | SAMOCHÓD March 5,000 shown as recurring-annual example | Added (**invented**) |
| 4.19 | Mobile | Year view becomes 12-month tiles per category (shown for WAKACJE I WYJAZDY only) | Added |

### 4.3 Forecast (1i, mobile 1r)
| # | Original | Redesign | Type |
|---|---|---|---|
| 4.20 | Horizon number input | Segmented 6 / 12 / 24 / 60 | Changed |
| 4.21 | Plotly line chart, default blue, dots, "Start / End" caption | Hand-drawn SVG line + area in accent, summary strip (Now, Sep 2027, Peak Aug 2027) | Changed |
| 4.22 | No explanation of the jumps | Annotations: Mar "+43,200.00 unit8 PROFIT SHARE", Sep "22,195.00 planned, incl. 16,000 holiday" | Added |
| 4.23 | Table: Month, Income, Expenses, Planned budget, Net, Projected EOM | Same columns and **same numbers**; Net gets an inline bar; red/green by sign | Changed |
| 4.24 | "Forecast view" at `/forecast/view` rendered as an unstyled table fragment and overflowed on mobile | Table is part of the page; mobile shows 6 representative months as stacked rows | Changed |
| 4.25 | — | Note that the Oct row reads from the Budget summary (as in the brief) | Added |

### 4.4 Analytics (2b) — *new mockup*
| # | Original | Redesign | Type |
|---|---|---|---|
| 4.26 | `/analytics` is the Budget "Breakdown" section: Plotly bar charts "Spend by category", "Cashflow by account", "Income vs expense (monthly)"; also embeds the overflowing yearly table | Fourth tab in Plan. Period switch (Month / 3 months / YTD / 12 months) | Moved |
| 4.27 | Spend by category: vertical bars with 45° rotated labels, hard to read | Ranked rows with pill, bar, amount, **delta vs 12-month average** (red above) | Changed |
| 4.28 | Income vs expense: blue/orange bars | Green/red grouped bars, Jul–Oct | Changed |
| 4.29 | **Cashflow by account** chart | **Not carried over** | Removed |
| 4.30 | — | "Largest single items" list | Added (**values are real 15 Oct items; ranking mine**) |
| 4.31 | Embedded yearly table | Removed from Analytics (lives only in Plan · Year) | Removed |
| 4.32 | Income vs expense bar heights | Approximated from the existing chart, not exact | Flag |

---

## 5. Accounts (1j, mobile 1s)

| # | Original | Redesign | Type |
|---|---|---|---|
| 5.1 | Card grid, 3 columns, uneven card heights | Single table, one row per account | Changed |
| 5.2 | Header: "Fortune" with Assets, Liabilities, Net worth | Net worth as headline (44px) with Assets and Liabilities beside it | Changed |
| 5.3 | Card: currency tag, balance, "N txns", sparkline, Reconcile button, "Show snapshots (N)", Edit / Snapshot / Delete links | Row: name + type, sparkline, **last-checked tag**, txn count, balance, Reconcile | Changed |
| 5.4 | — | **Last checked** status (✓ date, or amber "14 days ago") | Added (**dates invented**) |
| 5.5 | "Show snapshots" collapsible on every card | Snapshots move into the Reconcile panel ("Previous checks") | Moved |
| 5.6 | Edit / Snapshot / Delete visible | In a ⋯ menu — **menu content described, not drawn** | Changed |
| 5.7 | Credit card: "CREDIT CARD" tag, limit / available / used 19% bar | Same data, shown as an inline bar under the row | Changed |
| 5.8 | Order alphabetical | Order by balance, assets first, liability last | Changed |
| 5.9 | Per-currency fortune totals | Dropped (all accounts are PLN); note says base currency is PLN | Changed |
| 5.10 | Per-account base-currency equivalent | Pattern defined for foreign accounts (1.14), none to show | Kept (pattern) |
| 5.11 | Mobile: not designed | Account list with name, type, check status, balance, sparkline | Added |

### 5.1 Reconcile (1k)
| # | Original | Redesign | Type |
|---|---|---|---|
| 5.12 | Bare modal with signed-amount input | Slide-over with 3-step narrative (open bank → enter balance → review) | Changed |
| 5.13 | Signed adjustment amount typed by the user | User enters **bank balance**; difference computed and explained ("saved as an adjustment, nothing you entered is changed") | Changed |
| 5.14 | Fixed system category | **Record as** selector, default "Reconciliation (system)", any category allowed | Added |
| 5.15 | Snapshot as separate action | Checkbox "Also save a balance snapshot" | Merged |
| 5.16 | — | Previous checks list; button states the effect ("Record −28.90") | Added |
| 5.17 | — | Bank balance 4,702.18 and previous checks are **invented** | Flag |

### 5.2 Create account (2c) — *new mockup*
Original: slide-over form, not in screenshots. Redesign: modal with name, currency (immutable, stated), type, opening balance + as-of date, liability toggle, credit limit shown only while the toggle is on (per ADR-0030). Added.

---

## 6. Add / edit forms

| # | Original | Redesign | Type |
|---|---|---|---|
| 6.1 | Separate forms for transaction, planned, recurring (not in screenshots) | One **New entry** modal: When (Happened / Planned / Repeats) | Merged (1l, 2e) |
| 6.2 | — | **Category first**; direction is derived and displayed as a badge. No Expense/Income/Transit switch. | Changed |
| 6.3 | Transit From/To added to recurring form recently | Choosing the Transit category reveals From and To | Kept |
| 6.4 | Formula amounts editable (ADR-0047) | **Fixed value / Formula ƒ** switch. Fixed = amount input. Formula = term rows (sign · source rule · coefficient % · value), + Add term, live result, cycle/non-positive guard | Changed |
| 6.5 | — | Per-day impact line under the amount ("leaves 187.87 / day") | Added |
| 6.6 | — | ⌘↵ "save and add another" | Added |
| 6.7 | Mobile | Bottom sheet with type segmented control, large amount, category/account/note/repeat rows, custom numeric keypad, full-width Save | Added (1t) |
| 6.8 | Note: mobile sheet still shows an Expense/Income/Transit control | **Inconsistent with 6.2** — mobile sheet 1t was not updated | Flag |

---

## 7. Settings and categories

| # | Original | Redesign | Type |
|---|---|---|---|
| 7.1 | Settings = right drawer with tabs Categories / FX / Preferences (screenshots show it **unstyled**, plain HTML) | **Page** with tabs Categories · Currency & FX · Preferences | Changed |
| 7.2 | Categories: plain table (Name, Direction, Edit, Delete), alphabetical, mixed directions | Grouped **Expense (16) / Income (6) / System**; pill, direction badge, colour source, Edit · Archive | Changed |
| 7.3 | Delete button | **Archive** (restorable), consistent with soft-delete rule | Changed |
| 7.4 | Colour override shown by tinted name only | Swatch + "Override · magenta" text | Changed |
| 7.5 | Income-anchor selector in Preferences | Surfaced at the top of Categories as a card | Moved |
| 7.6 | System rows (Reconciliation, Transit) listed without actions | Same, labelled "locked" | Kept |
| 7.7 | FX tab, Preferences tab (base currency, timezone, refresh timestamp) | **Tab names only. Content not designed.** | Not carried over |
| 7.8 | "+ New category" small button | Primary button + modal (2d): name, direction (Expense/Income, immutable), 10 colour swatches or direction default, live preview | Changed |
| 7.9 | `/categories` route as separate unstyled page | Same page as Settings · Categories | Merged |

---

## 8. Command palette (1m)
Original: ⌘K described in the brief, no screenshot. Redesign: palette with typed query, grouped results (Actions with amounts, Go to, Create) and shortcut hints. **Deferred**, kept as reference.

---

## 9. Mobile and tablet coverage

| Original (375) | Redesign |
|---|---|
| 13 mobile screenshots, wide tables overflowed on Budget, Yearly, Analytics, Forecast view | Designed: Today, Ledger (Actual), Plan Budget (+ year tiles), Forecast, Accounts, Add sheet |
| — | **Not designed on mobile:** Ledger Planned, Ledger Recurring, Plan Analytics, Settings/Categories, create-account and create-category modals, Reconcile |

Tablet (1024): no mockups for any of the 13 routes.

---

## 10. Audit findings addressed

| Finding | Resolution |
|---|---|
| `/budget`, `/budget/yearly`, `/analytics` overflow horizontally (yearly table 1980–2075px) | Heatmap fits 1280; narrow screens use sticky first column or per-category cards; Analytics no longer embeds the table |
| `/forecast/view` overflows on mobile | Stacked-row layout on mobile |
| Brief pain #1 scattered "today" | Today surface (hero, affordability, upcoming, net worth) |
| #2 promote is a multi-click dance | Inline confirm, keyboard-only, batch promote |
| #3 dense yearly grid | Heatmap, legend, popover edit |
| #4 formula derivation invisible | Expandable derivation in Recurring; term editor in the form |
| #5 overdue is muted | Loud red chip and row tint |
| #6 recurring accordion grows | Grouped, inline actions, overrides collapsed behind chevron |
| #7 reconciliation unfamiliar | 3-step narrative slide-over |
| #8 mobile unexplored | Six mobile screens |

---

## 11. Items I introduced that are not in the original data

- Ledger · Planned entries (3 pending + 1 promoted)
- Three unit8 wypłata override contents
- Reconcile bank balance and previous checks
- "Checked N days ago" on accounts; sparkline shapes
- SAMOCHÓD March 5,000 recurring override
- Analytics income/expense bars (approximate) and "vs 12-mo avg" deltas (**real Avg/mo values from the original Budget table**; ranking is mine)
- "Monthly out ≈ 11,886 · in 27,763" summary
- "Largest single items" ordering
- Pace tag "On track" kept from the original although spend is 71% of plan; pace rule should be confirmed

## 12. Known gaps in the mockups

- Mobile add sheet (1t) still shows Expense/Income/Transit (see 6.8)
- Accounts ⋯ menu, bulk-action toolbar, export, Recently-deleted view: described, not drawn
- FX and Preferences settings content: not designed
- Cashflow-by-account chart, YTD avg and Δ prev columns: dropped (4.4, 4.29)
- Tablet: not designed
- Dark mode: out of scope per brief
