# Rising Dough v2 — gaps vs. `changes_vs_original.md`

> Audit of every row in `docs/application_redesign_handoff/changes_vs_original.md` against the Phase-0..7 task set in `docs/plans/v2/tasks.md` and the per-task files under `phase-*/`.
> Rows coded **Removed / not carried over** or **Kept** are excluded unless the plan still owes work. Rows marked `Flag` are listed only in §Data flags.
>
> Legend
> - **MISSING** — no task references the item.
> - **WEAK** — item mentioned by a parent task but the specific sub-feature is not called out and would be lost without this note.
> - **CONFLICT** — plan contradicts the diff; needs reconciliation before Phase 3 lands.
>
> Target absorption: either (a) add bullets to the host task below, or (b) spawn a new T-Rxx line in `tasks.md`.

---

## 1. Global

| Ref | Status | Item | Host task / owner |
|---|---|---|---|
| 1.2 | WEAK | Explicit removal of v1 "BUDGET PLANNER · local-first" footer tag on every page. `T-R04` rewrites `base.html` but does not call out the delete. | T-R04 |
| 1.4 | WEAK | Keyboard hint badges rendered inline on each nav item (`g o`, `g l`, `g p`, `g a`, `g s`). `T-R64` registers the shortcuts; the `<kbd>` chips in the nav markup are not in `T-R06` / `T-R04`. | T-R06 (markup) |
| 1.5 | WEAK | Active nav item uses an indigo left bar on a neutral sunk fill. No task names the active-state styling. | T-R04 or T-R06 |
| 1.8 | MISSING | Shared "Page header" pattern (eyebrow + large serif title + subtitle) called out in the redesign is not a Phase 2 primitive. Each screen rebuilds it ad-hoc. | New primitive (Phase 2) or add to `T-R22` |
| 1.16 | MISSING | Legacy aliases `g b` → Plan, `g f` → Plan called out as "suggested" in the diff. Not in `T-R64` shortcut map. | T-R64 |

---

## 2. Today

| Ref | Status | Item | Host task |
|---|---|---|---|
| 2.11 | WEAK | Upcoming grouped by **date-range** headers ("Next 7 days", "5 – 12 November") and capped at **six rows** with "Showing 6 of 24 · open in Ledger" footer. `T-R25` has a segmented 7 / 30 / All control instead; grouping + cap not specified. | T-R25 |
| 2.13 | WEAK | **"Promote all due"** UI button bound to `⇧↵`. `T-R45` ships the batch endpoint; `T-R64` could register the shortcut; the on-page button is not in `T-R25`. | T-R25 (+ T-R64 shortcut) |
| 2.16 | WEAK | "+ Planned" and "+ Recurring" small buttons inside the Upcoming header. `T-R21` is context-aware for top-bar `+ Add` but does not cover the in-panel header buttons. | T-R25 |

---

## 3. Ledger

### 3.1 Shared

| Ref | Status | Item | Host task |
|---|---|---|---|
| 3.1 | MISSING | Tab counts rendered on each tab chip (`Actual 456 · Planned 0→3 · Recurring 27`). No task references counts. | T-R26 / T-R27 / T-R28 (shared tab shell) |

### 3.2 Actual

| Ref | Status | Item | Host task |
|---|---|---|---|
| 3.5 | WEAK | Each **day header** carries a **net sum** (transit excluded). The task line in `tasks.md` only says "day-grouped rows". | T-R26 (no file yet) |
| 3.9 | MISSING | Pagination labels change from "Page 1 Next" to **"← Newer / Older →"**. No task mentions pagination. | T-R26 |

### 3.4 Recurring

| Ref | Status | Item | Host task |
|---|---|---|---|
| 3.19 | MISSING | **"Monthly out ≈ 11,886 · Monthly in 27,763 PLN"** summary strip at the top of the Recurring tab. `T-R28` does not include it. (Diff flags the numbers as computed — may want a service helper.) | T-R28 (+ Phase 4 service) |

---

## 4. Plan

### 4.1 Budget

| Ref | Status | Item | Host task |
|---|---|---|---|
| 4.2 | WEAK | **"change anchor"** link inside the slim period card. Not in `T-R30`. (Anchor change itself exists in v1 Preferences; this is a shortcut from Plan.) | T-R30 (+ T-R22 period_header) |
| 4.7 | WEAK | **Overridden** planned amount rendered **bold + accent underline**. `T-R30` names the over-budget class but not the override-marker treatment. | T-R30 |

### 4.2 Year

| Ref | Status | Item | Host task |
|---|---|---|---|
| 4.15 | CONFLICT | Diff says row totals **kept**, **column totals not shown**. `T-R31` deliverables include row + **column totals** + grand total in `<tfoot>`. Pick one before Phase 3 lands. | T-R31 — reconcile |
| 4.16 | MISSING | Unset categories (KOSZTY STAŁE, OPŁATY BANKOWE, PODATKI) **collapsed into a "3 unset" note** rather than rendered as dash rows. `T-R31` does not describe this collapse. | T-R31 |

### 4.3 Forecast

| Ref | Status | Item | Host task |
|---|---|---|---|
| 4.21 | WEAK | **Summary strip** above the chart ("Now · Sep 2027 · Peak Aug 2027"). `T-R47`/`T-R48` cover the SVG line + area + annotations but not the summary strip. | T-R32 / T-R48 |
| 4.23 | WEAK | **Inline bar** for the Net column in the monthly table (red/green by sign). Not in the T-R32 line (`reuse ADR-0043 shape`). | T-R32 |
| 4.24 | MISSING | Mobile forecast = **six representative months** stacked, not full 12. No mobile forecast task; `T-R53` only addresses narrow-table scroll. | New mobile task or T-R32 mobile branch |
| 4.25 | WEAK | Note that the **Oct row reads from the Budget summary** (so numbers never drift). Not called out as an acceptance check anywhere. | T-R32 acceptance |

### 4.4 Analytics

| Ref | Status | Item | Host task |
|---|---|---|---|
| — | Nothing new to add. Delta vs 12-mo, ranked rows, grouped bars, largest items all covered via `T-R33`, `T-R43`, `T-R47`, `T-R49`. | | |

---

## 5. Accounts

### 5 Table

| Ref | Status | Item | Host task |
|---|---|---|---|
| 5.2 | WEAK | **Net worth 44 px headline** treatment with Assets / Liabilities beside it. `T-R34` not written as a file; the diff should be baked into deliverables. | T-R34 (no file yet) |
| 5.5 | WEAK | Snapshots are **moved into the Reconcile slide-over** as a "Previous checks" section (and dropped from the Accounts row). Needs an explicit "remove snapshot accordion from Accounts row" acceptance in `T-R34` and a "render previous checks" deliverable in `T-R39`. | T-R34 + T-R39 |
| 5.7 | WEAK | Credit-card accounts render an **inline limit / available / used % bar** under the row. Not in `T-R34` deliverables. | T-R34 |
| 5.8 | MISSING | Sort order: **by balance, assets first, liability last** (v1 is alphabetical). No task specifies ordering. | T-R34 or a service helper |

### 5.1 Reconcile

| Ref | Status | Item | Host task |
|---|---|---|---|
| 5.14 | WEAK | **"Record as" category selector** inside the slide-over, defaulting to Reconciliation (system) but allowing any category. `T-R39` tasks.md line only mentions "signed-amount" phrasing. | T-R39 (no file yet) |
| 5.15 | WEAK | **"Also save a balance snapshot"** checkbox that merges the Snapshot action into Reconcile. | T-R39 |
| 5.16 | WEAK | **Previous checks list** rendered inside Reconcile (sourced from snapshots + prior reconciles). | T-R39 |

---

## 6. Add / edit forms

| Ref | Status | Item | Host task |
|---|---|---|---|
| 6.8 | CONFLICT | Mobile add sheet mock (1t) still shows the Expense / Income / Transit segmented control. Diff §6.2 and `T-R38` deliverables say **direction is derived from category** — no switch. `T-R52` needs an explicit "no direction segmented control" acceptance so the mobile mock inconsistency is resolved during implementation. | T-R52 + T-R38 |

---

## 7. Settings

| Ref | Status | Item | Host task |
|---|---|---|---|
| 7.4 | WEAK | Colour override rendered as **swatch + "Override · magenta"** text (not just a tinted name). `T-R35` says "colour source indicator" but does not specify the swatch + text label pattern. | T-R35 |
| 7.7 | WEAK | FX and Preferences tabs **content is not designed** in the handoff. `T-R36` ships read-only FX cache, `T-R37` mirrors the income-anchor link. Both are placeholder-grade and should either (a) ship as such with explicit "no further design" acceptance or (b) spawn a design-first follow-up task. | T-R36 + T-R37 |

---

## 9. Mobile / tablet coverage gaps

Six redesign surfaces have **no mobile mock** in the handoff and no mobile branch in a Phase 3 or Phase 6 task. Phase 6 only covers nav (`T-R51`), add sheet (`T-R52`), narrow-table scroll (`T-R53`), year cards (`T-R54`), settings tab-bar scroll (`T-R55`), and VR baselines (`T-R56`). The following still need an explicit mobile deliverable:

| Surface | Current state | Fix |
|---|---|---|
| Ledger · Planned | `T-R27` has no mobile section. | Add mobile card variant to T-R27 or new T-Rxx. |
| Ledger · Recurring | `T-R28` has no mobile section. | Add mobile card + accordion-on-tap to T-R28. |
| Plan · Analytics | `T-R33` has no mobile section; `T-R53` only wraps tables. | Add stacked-list mobile variant to T-R33. |
| Settings · Categories | `T-R35` row shape not specified at 375 px. | Add mobile card shape to T-R35; `T-R55` only covers the tab-bar. |
| Create-account overlay | `T-R65` ✅ shipped but no mobile mock reference. | Verify 375 px baseline in follow-up VR sweep. |
| Create-category overlay | `T-R66` ✅ shipped but no mobile mock reference. | Verify 375 px baseline in follow-up VR sweep. |
| Reconcile slide-over | `T-R39` has no mobile section. | Add bottom-sheet mobile variant to T-R39 or spawn new T-Rxx. |

**Tablet (1024 px)**: the diff flags that the handoff produced **no tablet mockups** for any of the 13 routes. The audit sweep runs at 1024 but there is no design intent to match against. Decide between (a) accept "tablet = desktop with narrower columns" (document in an ADR amendment) or (b) commission tablet mocks before Phase 3 lands.

---

## 11. Data flags (informational — invented values that need source-of-truth confirmation)

| Ref | Area | What is invented |
|---|---|---|
| 2.17 | Today / Recurring | `na osobiste` upcoming amount: `−2,781.34` (original) vs. `15,650.66` (redesign). Numbers disagree between source screens. |
| 3.14 | Ledger · Planned | Three pending planned items + one promoted dentist visit. Real data has none. |
| 3.20 | Ledger · Recurring | Three override rows on `unit8 wypłata` (Dec amount, Jan skipped, Feb moved). Contents invented. |
| 4.18 | Plan · Year | `SAMOCHÓD` March 5,000 recurring-annual override — invented. |
| 4.30 | Plan · Analytics | "Largest single items" ranking is designer's; values are real 15 Oct items. |
| 4.32 | Plan · Analytics | Income-vs-expense bar heights approximated from the existing chart, not exact. |
| 5.4 | Accounts | "Checked N days ago" dates + sparkline shapes — invented. |
| 5.17 | Reconcile | Bank balance `4,702.18` + previous checks list — invented. |

Treat these as reminders during Phase 3 integration tests: fixtures should reflect real DB state, not the mock values.

---

## 12. Known gaps already acknowledged in the diff (no action needed beyond what's planned)

- `⌘K` command palette — **deferred** (listed under `tasks.md` §Deferred past v2).
- Dark mode — **out of scope** per brief.
- Cashflow-by-account chart — intentionally **dropped** (Plotly removal `T-R50`).
- YTD avg + Δ prev columns — intentionally **dropped** on Budget.

---

## Summary

- **Items requiring a plan edit before Phase 3**: 24 (listed above as MISSING / WEAK / CONFLICT).
- **Decisions needed first**:
  - §4.15 column totals on Year grid (plan says include; diff says drop).
  - §6.8 mobile add-sheet direction control (plan says derive from category; mock 1t keeps the segmented control).
  - §9 tablet design: adopt desktop fallback or commission mocks.
  - §7.7 FX + Preferences design — ship placeholder or design first.
- **Easiest wins** (bullet additions to existing task files, no new T-R):
  - 1.2, 1.4, 1.5, 2.11, 2.13, 2.16, 3.1, 3.5, 3.9, 3.19, 4.2, 4.7, 4.16, 4.21, 4.23, 4.25, 5.2, 5.5, 5.7, 5.8, 5.14, 5.15, 5.16, 7.4.
- **New sub-tasks likely needed**:
  - Mobile branches for `T-R27`, `T-R28`, `T-R33`, `T-R35`, `T-R39`.
  - Mobile forecast layout (§4.24).
  - Shared Page header primitive (§1.8).
