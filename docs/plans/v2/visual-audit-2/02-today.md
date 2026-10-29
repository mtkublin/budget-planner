# 02 · Today, Home, /dev/components

## `/today` — desktop (mock `desktop-1d-today.png`)

| # | Element | Status |
|---|---|---|
| 1 | Rising Dough wordmark + nav + keyboard shortcut chips | ✅ |
| 2 | Eyebrow `THURSDAY · 29 OCTOBER 2026` + title `Today` + `ON TRACK` pace tag | ✅ |
| 3 | Top-bar `Search · all accounts` + `+ Add n` button | ✅ |
| 4 | Hero number `257.00 PLN / DAY` with "LEFT TO SPEND PER DAY" eyebrow | ✅ |
| 5 | Breakdown line (`2,572.07 PLN left · 9 days left · 6,059.00 PLN spent`) | ⚠️ **PARTIAL** — missing committed figure (mock also shows `402.19 committed`) |
| 6 | **Segmented progress bar** `spent | committed-hatched | left` | ❌ **MISSING** — only a solid line divider renders. Primitive exists in `/dev/components` under `Progress`. |
| 7 | `Can I afford · 250.00 · PLN · Would leave 257.00 PLN / day` | ✅ (debounced preview works, `/today/afford` fires) |
| 8 | Net worth card right side (hero number, Assets/Liabilities, six largest balances) | ✅ |
| 9 | "View all accounts →" link | ✅ |
| 10 | Link to Forecast from net-worth card | ❌ MISSING |
| 11 | Upcoming segmented `7 days · 30 days · all` | ✅ |
| 12 | **"Promote in: Today · Planned · Recurring"** header text (current) vs mock **"+ Planned" + "+ Recurring" buttons + "Promote all due" button bound to ⇧↵** | ❌ **MISSING** — the Promote-all-due button and the two + buttons |
| 13 | **Date-range grouping** (`NEXT 7 DAYS`, `5 – 12 November`) | ❌ **MISSING** — current is flat chronological list |
| 14 | **6-row cap + "Showing 6 of 24 · open in Ledger" footer** | ❌ **MISSING** — all upcoming rows render inline |
| 15 | Per-row shape `date | description | account | category | amount | Promote` | ⚠️ PARTIAL — missing `Skip` and `Override` and `⋯` buttons (mock shows all four) |
| 16 | **Row expand-in-place** on Promote → inline `account | date | amount | Confirm ↩ | Esc` | ❌ **MISSING** — see F-02 |
| 17 | **Overdue row visual** (expense-soft bg + `N days late` red chip + sorted first + never muted) | ❌ **MISSING** |
| 18 | Row category pill coloured per direction | ⚠️ PARTIAL — pills render but no amount shown next to pill, pill style differs on narrow |
| 19 | Row amount column shows `−356.70` red / `+15.XX` green depending on direction | ✅ |

## `/today` — mobile (mock `mobile-1o-today.png`)

Current `/tmp/fe-audit/mobile__today.png` renders the hero + Can-I-afford + Net worth + Upcoming BUT with these breaks:

| # | Element | Status |
|---|---|---|
| 20 | Hero + Can-I-afford visible | ✅ |
| 21 | Net worth card shows ALL ACCOUNTS list (not just 6 largest) | ⚠️ PARTIAL |
| 22 | **Bottom tab bar fixed to viewport** (Today · Ledger · `+` · Plan · Accounts) | 🐛 LAYOUT **L-01** — renders at y=770 in document flow, not fixed, overlaps content when scrolled |
| 23 | **Upcoming row shows amount + Promote → link** | 🐛 LAYOUT — row rendered without amount + action labels visible; category pill appears as empty red dot |
| 24 | Swipe hint copy `"Swipe right to promote, left to skip. Tap a row to override."` | ❌ MISSING |
| 25 | `24 in 30 days` top-right filter chip | ❌ MISSING |

## `/` (home — legacy Overview still live)

| # | Element | Status |
|---|---|---|
| 26 | `<title>Overview · Budget Planner</title>` still present | 🐛 **B-04** (not yet filed) — product rename T-R05 incomplete |
| 27 | `/` renders the legacy "Overview" dashboard (Fortune card + account list + Upcoming) rather than 302 → `/today` | 🐛 FUNCTIONAL — T-R06 not shipped |
| 28 | Overview Upcoming has `+ Planned`, `+ Recurring`, Promote/Skip/Override actions **that `/today` is missing** | ⚠️ scope conflict — the "real" Today UX partially lives on `/`, not `/today` |

## `/dev/components`

Everything renders. This surface is the proof the macro system is in place; the reason items are listed MISSING on other screens is that those screens don't call these macros.

| Component | On `/dev/components` | Used on route screens |
|---|:-:|---|
| Amount | ✅ | partially (table cells) |
| Pills | ✅ | ledger rows, settings |
| Direction badges | ✅ | ledger rows |
| Pace tags (`On track · Tight · Overdue · 13`) | ✅ | /today hero |
| Buttons (`+ Add n · Edit · Ghost`) | ✅ | widespread |
| Segmented with counts (`Actual 456 · Planned 0 · Recurring 27`) | ✅ | Ledger tabs — **but counts missing** |
| Filter chips row | ✅ | Ledger ✓ |
| Progress bar (segmented spent/committed hatch/left + 110% over) | ✅ | **not used on /today or /plan budget** |
| Heatmap cells | ✅ | /plan year ✓ (static only, not clickable) |
| Toast (`Promoted księgowa · Undo`) | ✅ | **not observed** firing after any action |
| Sparkline | ✅ | /accounts ✓ |
| Top-bar Add (`+ Add · + Planned entry · + Recurring rule`) | ✅ | **present on Ledger tabs, missing from /today Upcoming header** |

**Takeaway**: primitives are built but call-sites don't consume them. Several ❌ MISSING items would collapse to one-line template changes.
