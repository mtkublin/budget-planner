# 01 · Today & Home

## `/today` — desktop (mock `desktop-1d-today.png`)

| # | Delta | Status |
|---|---|---|
| 1 | **Hero segmented bar** (spent / committed / left — committed uses diagonal hatch). Current shows a plain divider + spent total only. | ✅ `T-R25` + `T-R20` (progress-bar primitive) |
| 2 | Pace tag positioned **inline next to the hero number**. Current pushes it to the far right of the header row. | ✅ `T-R14` + `T-R25` |
| 3 | **Breakdown line** below hero: `2,572 PLN left · 9 days left · 6,059 PLN spent` style vs mock which also shows the committed figure. | ✅ `T-R25` |
| 4 | **"Can I afford" input + live per-day preview with delta.** Current renders the input but no debounced result rendering. | ✅ `T-R25` + `T-R40` |
| 5 | **Net worth card** on the right rail (hero number, Assets / Liabilities, six largest balances, link to Accounts + Forecast). Current renders most of the right card but no link to Forecast. | ✅ `T-R25` |
| 6 | **Upcoming grouped by date range** (`NEXT 7 DAYS`, then `5 – 12 November`). Current is a flat list sorted by date. | 📎 `T-R25` (weak — `missing-from-plan.md §2.11`) |
| 7 | **"Promote all due" button** bound to `⇧↵`, in Upcoming header. Current is missing it. | 📎 `T-R25` + `T-R45` (weak — `missing-from-plan.md §2.13`) |
| 8 | **"+ Planned" and "+ Recurring" buttons inside Upcoming header.** Current renders them on `/` (legacy Overview) but **not** on `/today`. | 📎 `T-R25` (weak — `missing-from-plan.md §2.16`) |
| 9 | **Row expand-in-place** on Promote → inline `account | date | amount | Confirm ↩ | Esc`, no modal. | ❓ **UNCOVERED** → <a id="u-01"></a>**U-01** |
| 10 | **"Showing 6 of 24 · open in Ledger" footer** on Upcoming (6-row cap). Current renders all upcoming rows. | ❓ **UNCOVERED** → <a id="u-02"></a>**U-02** |
| 11 | **Overdue row visual** = expense-soft background + "N days late" red chip + sorted first + never muted. Current has no overdue styling. | ❓ **UNCOVERED** → <a id="u-03"></a>**U-03** (also applies to `/ledger?view=planned`) |
| 12 | **Per-row action set** on `/today` Upcoming: `Promote / Skip / Override · ⋯`. Current only shows a single `Promote` chip. | ✅ `T-R25` (deliverable) |
| 13 | Page title still contains `· Budget Planner` suffix on `/`. On `/today` title reads `Rising Dough` (checked header). | 📎 `T-R05` (rename pending) |

## `/today` — mobile (mock `mobile-1o-today.png`)

Current `mobile__today.png` is almost entirely broken (overflow = 20): the desktop rail stays in flow, hero squeezed, nav labels floating mid-page. Nothing matches mock chrome.

| # | Delta | Status |
|---|---|---|
| 14 | Mobile uses **bottom tab bar** (Today / Ledger / `+` / Plan / Accounts), **no** left rail. | ✅ `T-R51` (pending) |
| 15 | Hero card with large serif number + "LEFT TO SPEND PER DAY" eyebrow + progress bar below. Current renders desktop hero scaled down. | ✅ `T-R51` + `T-R25` responsive |
| 16 | Upcoming shows **row swipe hint**: *"Swipe right to promote, left to skip. Tap a row to override."* No current equivalent copy. | ❓ **UNCOVERED** — add bullet to `T-R51` or new T-R |
| 17 | Mock mobile also shows **"24 in 30 days" top-right link** on Upcoming (header-level filter chip). Current absent. | ✅ `T-R51` + `T-R25` |

## `/` (home, legacy Overview) — not in design

`/` still serves the v1 `templates/home/overview.html` dashboard. `T-R06` plans a 302 → `/today`, which has not shipped.

| # | Delta | Status |
|---|---|---|
| 18 | `<title>Overview · Budget Planner</title>` still present on `/`. | 🐛 **B-07** (also 📎 `T-R05`) |
| 19 | Dashboard renders Fortune card + account list + Upcoming — **duplicates** content on `/today` and `/accounts`. Mock has no equivalent. | ✅ `T-R06` (route redirect pending) |
| 20 | Upcoming on `/` includes `+ Planned`, `+ Recurring`, Promote/Skip/Override actions — the UI that *should* live on `/today`. | ✅ `T-R06` + `T-R25` (migrate when `/` is retired) |
