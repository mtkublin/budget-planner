# Manual Audit — Remediation Plan

**Source:** `docs/plans/v2/manual-audit.md` (57 issues, ids 0–56)
**Design source of truth:** `docs/application_redesign_handoff/screens/*.html` + `styles.css`
**Scope:** desktop first (mockups are desktop-centric); re-check mobile at the end
**Branch target:** `feat/v2-rising-dough`

The designer HTML mockups are canonical. When a current implementation deviates from the mockup, the mockup wins. Pixel-level match is not the goal, but structure, hierarchy, column layout, token usage, and copy must match.

---

## 0 · Guiding principles

1. **Mockup = spec.** Every change must point back to a mockup file + line.
2. **Tokens only.** All colors, spacings, type sizes come from `rising-dough.css` tokens (which mirror `styles.css` in the handoff). No hex literals in templates.
3. **Thin templates.** Markup changes only touch Jinja partials + CSS; business logic lives in services. Where mockup implies a new field (e.g., category direction on upcoming rows, assets/liabilities split, year-grid formula-vs-oneoff flag), extend the services first, then surface in the template.
4. **Doc-first (CLAUDE.md policy).** Each phase lands with:
   - entry in `docs/CHANGELOG.md`
   - ADR update where structural (e.g., modal unification = new ADR referencing redesign)
   - task line in `docs/tasks.md` prefixed `✅`
5. **Visual audit before done.** Per CLAUDE.md "Frontend validation (MANDATORY)" — run `frontend-visual-audit` on affected routes at **1440 / 1024 / 375** after each phase; attach findings to the handoff.

---

## 1 · Phase ordering

Phases are ordered to maximize reuse: global primitives first, then the three heaviest screens, then the long tail.

| # | Phase                        | Covers audit ids                        | Est. complexity |
|---|------------------------------|------------------------------------------|-----------------|
| A | Global shell + modals        | 15, 16, 17, 18, 19, 20, 21               | High            |
| B | Today                        | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 | High |
| C | Ledger                       | 22, 23, 24, 25, 26, 27, 28, 29, 30, 31  | High            |
| D | Plan — Budget                | 32, 33, 34, 35                           | Medium          |
| E | Plan — Year                  | 36, 37, 38, 39, 40, 41                   | Medium          |
| F | Plan — Forecast              | 42, 43, 44, 45                           | Medium          |
| G | Plan — Analytics             | 46, 47, 48, 49                           | Medium          |
| H | Accounts                     | 50, 51                                   | Low-Medium      |
| I | Settings                     | 52, 53, 54, 55, 56                       | Medium          |
| J | Cross-cutting verification   | –                                        | Low             |

Each phase ships as one commit (or small series) following conventional-commits with task id.

---

## Phase A — Global shell + modals

### A.1 Navigation: Settings at bottom with separator  _(audit #18)_
- **Mockup:** `desktop-01-today.html:3` — Settings rendered after a spacer `<div style="flex:1">`, with `border-top:1px solid var(--line);border-radius:0;padding-top:14px`.
- **Current:** `src/budget_planner/web/templates/partials/_nav.html` (sidebar list).
- **Work:**
  - Introduce `.rd-rail__footer` region in rail layout; move Settings link into it.
  - Add top-border separator via existing `--line` token.
  - Keep keyboard shortcut badge.
- **Accept:** Settings visually pinned at the bottom of the rail across viewport heights; separator visible; no gap on 1024/1440; collapses sensibly on 375.

### A.2 Page footer: remove redundant title  _(audit #19)_
- **Mockup:** no screen renders a repeated title in the footer area.
- **Current:** `base.html` and/or main layout render page title again below the content region. Grep for the string pattern.
- **Work:** Delete the duplicated title block. If it was powering nothing else, remove any related context var. Verify no screen depends on it.
- **Accept:** No screen shows the page title twice. Visual audit shows single `<h1>` per route.

### A.3 Unified entry modal — Actual / Planned / Recurring  _(audit #15, 16, 17, 20, 21)_
This is the biggest piece. Mockups treat all three as the same slide-over with a single top segment switcher.

- **Mockups:**
  - `overlay-13-add-fixed.html` (Add Actual + related fixed variant)
  - `overlay-12-add-formula.html` (Add Recurring w/ formula amount)
  - Note: in each mockup there is **one** `Happened / Planned / Repeats` segmented at the top, no duplicate inside the body.
- **Current:**
  - `partials/_add_entry_overlay.html` — host overlay with tab buttons.
  - `partials/transactions/_form.html` — Actual form; has a `When` selector (duplicate).
  - `partials/planned/_form.html` — Planned form.
  - `partials/recurring/_form.html` — Recurring form (formula UI + checkbox list).
- **Work (ordered):**
  1. Introduce a shared `partials/_entry_modal_shell.html` that owns:
     - Slide-over frame
     - Single `Happened / Planned / Repeats` segmented at the top
     - DEST field living next to ACCOUNT (grid 2-col), DATE + NOTE on the row below (grid 2-col)
     - Submit button bar
  2. Rewrite each `_form.html` as a body partial consumed by the shell. Remove the inner `When` selector from Actual form.
  3. Planned + Recurring reach visual + structural parity with Actual: labels, field order, spacing, segmented buttons styled with `.rd-segmented`.
  4. Recurring formula UI:
     - Replace current checklist look with the mockup layout: coefficient `%`, source selector, baseline amount, preview row.
     - Numbers use `.num` + `.cur` conventions.
  5. HTMX swap targets re-wired so the segmented switcher swaps the body only (not the shell).
- **Accept:**
  - Only one segmented at the top of the modal.
  - DEST is adjacent to ACCOUNT.
  - DATE + NOTE sit on the next row.
  - Recurring formula block visually matches `overlay-12-add-formula.html`.
  - All three modes submit via existing POST endpoints (no behavior regression).
  - Visual audit on 1440 / 1024 / 375.

**Doc:** New ADR describing the unified entry modal (supersedes any prior split-modal ADR). Update `docs/tasks.md`.

---

## Phase B — Today

### B.1 Left-to-spend-per-day card  _(audit #0, 1, 2, 3, 4)_
- **Mockup:** `desktop-01-today.html:7–12`.
- **Current:** `templates/today/index.html` (main card), `templates/today/_afford_preview.html`, services `services/today.py`.
- **Work:**
  - **Layout order (fix #0, 1):**
    - Row 1: eyebrow `Left to spend per day` + status pill (`On track` / `Over limit`).
    - Row 2: big number + `PLN / day`.
    - Row 3: `{{left}} left · {{days}} days until next income ({payment reset mention})`.
    - Row 4: Progress bar.
    - Row 5: Legend `Spent / Committed / Left · of total`.
    - Row 6: `Period <start> → <end> · day X of Y`.
  - **Period definition (fix #1):** emit the period line below the bar. Data should come from `summary` object; extend the view-model if the field is missing.
  - **Can-I-afford calculation (fix #2):** audit `services/today.py` + any afford helper. Expected mockup math: `per_day_after = (left - afford_amount) / days_remaining`; `delta_per_day = per_day_after - current_per_day`. Fix formula bugs, add tests.
  - **"Overdue" wording (fix #3):** rename the pace tag that currently returns `"overdue"` to `"over_limit"`; thread the new label through template + CSS classes. Keep the backend enum/string consistent.
  - **Delta display (fix #4):** render as `<span class="num">per_day_after</span>` + `<span class="num neg|pos">±delta / day</span>`. Match mockup `desktop-01-today.html:12`.
  - **Input styling (fix #4):** adopt the bordered + 3px accent-shadow look (`border:1px solid var(--acc); box-shadow:0 0 0 3px var(--accs)`).
- **Accept:**
  - Order of elements matches mockup exactly.
  - Afford math verified by unit tests (new).
  - No "overdue" string on this card.
  - Visual audit at 1440 / 1024 / 375.

### B.2 Net worth card  _(audit #5, 6, 7)_
- **Mockup:** `desktop-01-today.html:13–15`.
- **Current:** same `today/index.html`.
- **Work:**
  - **Assets / Liabilities split (fix #5):** compute totals in the Today router (aggregate accounts by `is_liability`). Render as `<div class="mut num" style="font-size:12px">Assets X · Liabilities Y</div>` directly beneath the net worth total.
  - **Formatting (fix #6):** use `<span class="cur">PLN</span>` not `<small>`; set font size to 30px via existing token (introduce if missing). Match row styling of per-account breakdown (`.row` grid, `padding:8px 0`, `font-size:13.5px`).
  - **Forecast link (fix #7):** add `<a href="/plan/forecast">Forecast →</a>` to the footer row next to `All N accounts →`.
- **Accept:** Assets / Liabilities visible; Forecast link navigates; typography matches mockup.

### B.3 Upcoming section  _(audit #8, 9, 10, 11, 12, 13, 14)_
- **Mockup:** `desktop-01-today.html:16–22`.
- **Current:** `templates/today/_upcoming.html`, router + service producing `UpcomingItem` / `UpcomingRow`.
- **Work:**
  - **Header layout (fix #8, 9):** left group = title `Upcoming` + segmented `7 days / 30 days / All` next to it. Right group buttons: `Promote all due ⇧↵`, `+ Planned`, `+ Recurring` (that order, that copy).
  - **Table structure (fix #10):**
    - Replace `<table>` with `.row` grid rows (as in mockup): columns `52px 1fr 150px 140px 200px` (date / description+account / category pill / amount / actions).
    - Group heading above each date band uses eyebrow styling.
  - **Category field on every row (fix #11):** extend `UpcomingRow` dataclass with `category_id` + `category_name` + `category_direction` + `category_color`. Fetch from service. Render `.pill` with mockup color scheme (OKLCH triplets per category); fall back to a neutral pill if not set.
  - **Direction-aware amount (fix #12):** amount gets `.pos` if the category direction is income, `.neg` if expense; add `+` prefix for income (matches mockup `+20,945.45`).
  - **Inline promote form (fix #13, 14):**
    - Replace button-only inline promote with the mockup card: outlined accent border (`1.5px solid var(--acc)`, `background: var(--accs)`), grid `52px 1.3fr 130px 140px 140px`.
    - Inside: category + account selector, date, amount (highlighted input with 3px white shadow), action pair `Confirm ↵` / `Esc`.
    - Explanatory line below: `Inline confirm, no modal. Records a real transaction and advances next due to <date>`.
    - Wire HTMX so Confirm POSTs to the existing promote endpoint; Esc swaps back to the collapsed row.
- **Accept:**
  - Every row shows a category pill tied to the category's own color.
  - Income amounts render green/pos; expenses neutral; direction derived from category.
  - Inline promote expands into the mockup design and submits successfully.
  - Visual audit at 1440 / 1024 / 375.

---

## Phase C — Ledger

### C.1 Toolbar / search / tab-note  _(audit #22, 23, 24)_
- **Mockup:** `desktop-02-ledger-actual.html:5–6`.
- **Current:** `templates/ledger/index.html`.
- **Work:**
  - **Single-row search bar (fix #22):** rebuild `.rd-chips` (or wrapper) so segmented tabs + filter chips + search input live on one row and never wrap on desktop. Search input must be fixed-width (e.g., 240px) and anchored right.
  - **Tab shortcut note (fix #23):** move the `[` `]` keyboard shortcut hint from the header actions to directly below the segmented tabs, matching the mockup placement.
  - **Bulk select / delete / export bar (fix #24):** delete the dark `.rd-bulk-toolbar`. Replace with nothing by default; if the feature is retained, surface it only when rows are selected and style it with page tokens (not inverse ink).
- **Accept:** Search in a single visible row; shortcut hint sits where mockup shows it; dark bulk bar is gone.

### C.2 Table columns, grouping, formatting  _(audit #25, 26, 27, 28, 29)_
- **Mockup:**
  - Actual: `desktop-02-ledger-actual.html:7–9`.
  - Planned: `desktop-03-ledger-planned.html:7–8`.
  - Recurring: `desktop-04-ledger-recurring.html:7–13`.
- **Current:** `templates/ledger/_table.html`.
- **Work:**
  - **Column order + spacing (fix #25):**
    - Actual table: match mockup column layout (date / description+account / category / amount / actions) using a CSS grid-based row instead of `<table>` cells where mockup does.
    - Recurring table: 6 columns `Next due | Rule | Category | Amount | Overrides | Actions`. Drop current `Cadence` dedicated column (fold into Rule), drop `Active` column (status surfaces in Rule or as muted suffix).
  - **Day grouping with net (fix #26):** day header row renders `Day Mon DD` on the left and `net ±X.XX` on the right, computed from non-transit rows for that day. Add a service helper if needed.
  - **Income styling (fix #27):** apply `.pos` to amounts when category direction is income; render `+N.NN` with `.cur` suffix.
  - **Actions header (fix #28):** empty `<th></th>`; row-level action is the ⋯ kebab icon only.
  - **Pagination buttons (fix #29):** style Newer / Older as `.btn.s` with chevron (`← Newer`, `Older →`), remove the muted-link look.
- **Accept:** Column order matches mockup per tab; day groups show net; incomes positively colored; actions header empty; pagination uses buttons.

### C.3 Recurring expansion row  _(audit #30)_
- **Mockup:** `desktop-04-ledger-recurring.html:10–13` — expand row reveals a grid showing overrides AND the formula derivation.
- **Current:** `templates/ledger/_table.html:217-238` — accordion exists but only shows overrides.
- **Work:**
  - Extend the expand-row template to render:
    - Overrides grid (existing).
    - Formula panel: baseline amount, coefficient %, source (e.g., referenced category or recurring rule), computed amount at the current date.
  - Service: expose a `derive_recurring_breakdown(rule_id)` helper if not already present; it should return structured data for the panel.
- **Accept:** Clicking expand on a formula-based recurring row shows both overrides and the computed formula.

### C.4 Remove FAB  _(audit #31)_
- **Mockup:** no screen shows a FAB.
- **Current:** `rising-dough.css` still defines `.fab`; it's hidden on mobile but visible on desktop.
- **Work:** Delete FAB template usage + CSS block. Keep the `n` keyboard shortcut and the `+ Add` pill in the top bar as the only entry affordance.
- **Accept:** No FAB on any route, any breakpoint.

---

## Phase D — Plan: Budget tab

### D.1 Period selector logic + widget  _(audit #32, 33)_
- **Mockup:**
  - Budget: `desktop-05-plan-budget.html:4` — monthly selector with left/right arrows and the current month label.
  - Year/Forecast: different selectors in that same slot.
- **Current:** `templates/plan/index.html` renders a static month label; year/forecast expose their selectors inside the tab body.
- **Work:**
  - Make the top-right period selector tab-aware:
    - `Budget` and `Analytics`: monthly selector (arrows + label, clickable, HTMX swap).
    - `Year`: year selector (arrows + label).
    - `Forecast`: forecast horizon segmented (`3 / 6 / 12 / 24`).
  - Remove the duplicate selectors from the individual tab bodies (year selector in Year, horizon in Forecast).
- **Accept:** Only one period selector visible per Plan tab, in the top-right slot; it works via HTMX and reflects the active tab.

### D.2 Budget top bar (period + left/day)  _(audit #34)_
- **Mockup:** `desktop-05-plan-budget.html:5`.
- **Current:** `templates/plan/_budget_tab.html:15–37` (`.rd-period`).
- **Work:**
  - Rebuild the top bar as a grid matching the mockup: left — period dates `Oct · 1 → 31`, center — bar + legend, right — left-per-day number.
  - Tokenize paddings / font-sizes to match card density.
- **Accept:** Visual match with the mockup; no three-up uneven columns.

### D.3 Budget override UI  _(audit #35)_
- **Mockup:** `desktop-05-plan-budget.html:9` — override as a compact inline card with tier chips, amount input, apply.
- **Current:** `templates/partials/budget/_override_form.html`.
- **Work:**
  - Replace existing form with mockup card:
    - Row 1: category pill + current amount summary.
    - Row 2: tier chips (`.pill`-style buttons, selectable).
    - Row 3: amount input + `Save` button.
  - Keep POST endpoint; just update markup.
- **Accept:** Override opens inline, matches mockup card layout, saves correctly.

---

## Phase E — Plan: Year tab

### E.1 Year selector widget  _(audit #40, 41)_
- **Mockup:** `desktop-06-plan-year.html:6` — slim segmented or arrow pair in the shared top-right slot.
- **Current:** `templates/plan/_year_tab.html:4–14` renders in-page.
- **Work:**
  - Move the year selector into the global Plan selector slot (per D.1).
  - Remove the duplicate sub-header + comment above the grid; collapse into help text under the heading or into a tooltip on the legend.
- **Accept:** Only one year selector in the Plan header; redundant subheader removed.

### E.2 Grid formatting  _(audit #37)_
- **Mockup:** `desktop-06-plan-year.html:6–7`.
- **Current:** `templates/plan/_year_tab.html:20–49` + `rising-dough.css`.
- **Work:**
  - Match cell padding, font-weights (header 600, body 500), muted text for zero cells, bold for one-off months, hatched background for recurring months (use `repeating-linear-gradient`).
  - Verify grid line colors use `--line`.
- **Accept:** Side-by-side visual parity with mockup.

### E.3 Legend above grid  _(audit #38)_
- **Mockup:** `desktop-06-plan-year.html` — small legend row explaining swatches (one-off / recurring / unset).
- **Current:** none.
- **Work:** Add a small legend above the grid, built from `.pill` + icon swatches.
- **Accept:** Legend visible, tokenized.

### E.4 Comment below grid + collapse unset budgets  _(audit #39)_
- **Mockup:** `desktop-06-plan-year.html` — hint text at the bottom + collapsed state for categories without a budget.
- **Work:**
  - Add the help text block below the grid.
  - Default-collapse categories whose yearly budget is unset; add a `Show N categories without a budget` toggle (HTMX reveal).
- **Accept:** Unset categories are collapsed by default; toggle restores them.

### E.5 Year tab override  _(audit #36)_
- **Work:** Reuse Phase D.3 override card; apply to Year grid cells. Shared partial.
- **Accept:** Year override uses the same card UI as Budget override.

---

## Phase F — Plan: Forecast tab

### F.1 Period selector  _(audit #42)_
- **Work:**
  - Move horizon selector to the shared top-right slot (per D.1).
  - Change value labels from `6 mo` to `6`, `12 mo` to `12`, etc.
- **Accept:** Horizon segmented is in the header slot and labels are numeric only.

### F.2 Summary values above graph  _(audit #43)_
- **Mockup:** `desktop-07-plan-forecast.html` — three values laid out as a tidy row with eyebrows and large numerals.
- **Current:** `templates/plan/_forecast_tab.html:22–37`.
- **Work:** Rebuild as a 3-up grid; eyebrow + large number + muted suffix; right-align numerics with `.num`.
- **Accept:** Matches mockup layout + typography.

### F.3 Table formatting  _(audit #44)_
- **Mockup:** `desktop-07-plan-forecast.html:8`.
- **Current:** `templates/plan/_forecast_tab.html:107–119`.
- **Work:**
  - `EOM` column uses `font-weight:700`.
  - `NET` column: when value negative, apply `.neg` class + a tinted background cell.
- **Accept:** EOM bold; negative NET visually distinct.

### F.4 Graph monthly dots  _(audit #45)_
- **Mockup:** `desktop-07-plan-forecast.html:7` — dots on each month tick.
- **Current:** `templates/plan/_forecast_tab.html:51–68` (SVG).
- **Work:** Add `<circle>` markers at every month boundary of the forecast line.
- **Accept:** Dots visible, aligned with x-axis ticks.

---

## Phase G — Plan: Analytics tab

### G.1 Box sizing + layout  _(audit #46, 49)_
- **Mockup:** `desktop-08-plan-analytics.html`.
- **Current:** `templates/plan/_analytics_tab.html`, `_analytics_bundle.html`.
- **Work:** Rebuild the bento grid using CSS grid with the exact column/row proportions from the mockup; cap card paddings; apply uniform heading styles.
- **Accept:** Side-by-side parity on 1440.

### G.2 Remove expandable data table + chart fallback  _(audit #47)_
- **Work:** Delete the expandable table + fallback markup from `_analytics_bundle.html`. Keep chart-only view. Prune any orphaned server data.
- **Accept:** No expandable table remains; charts render alone.

### G.3 "Largest single item" cap  _(audit #48)_
- **Work:** Service returns top N (3–5) items only; truncate names with ellipsis.
- **Accept:** Box never shows more than N rows.

---

## Phase H — Accounts

### H.1 New account modal  _(audit #50)_
- **Mockup:** `overlay-14-create-account.html`.
- **Current:** `partials/accounts/_form.html`.
- **Work:**
  - Wrap in slide-over frame (reuse `_slideover_page.html` once standardized).
  - Convert label/input pairs to `.rd-field` + `.rd-input`.
  - Replace liability checkbox with `.rd-toggle-card`.
  - Apply mockup grid for two-column fields (name/currency, type/liability).
- **Accept:** Modal matches mockup; submits successfully.

### H.2 Accounts page body  _(audit #51)_
- **Mockup:** `desktop-09-accounts.html:6–7`.
- **Current:** `templates/accounts/index.html`.
- **Work:** Audit each visible region (summary row, accounts table, `Checked` tag) and bring styling in line. Table uses `.row` grid rhythm, numeric alignment via `.num`.
- **Accept:** Visual parity with mockup across sections.

---

## Phase I — Settings

### I.1 Income anchor relocation + Preferences cleanup  _(audit #52, 54)_
- **Mockups:**
  - Categories page: `desktop-10-settings-categories.html:6`.
  - Preferences no longer owns the anchor.
- **Current:** `templates/settings/_prefs.html:27–52` (anchor still there); `templates/settings/_categories.html:6–24`.
- **Work:**
  - Delete anchor selector + save button from Preferences.
  - On Categories, move anchor to a compact bar at the top matching the mockup; auto-save on change (HTMX) — no Save button.
- **Accept:** Anchor exists only on Categories; auto-saves without a button.

### I.2 Categories table formatting  _(audit #53)_
- **Mockup:** `desktop-10-settings-categories.html:7–8`.
- **Current:** `templates/settings/_categories.html:28–91`.
- **Work:** Rebuild rows with `.row` grid, aligned columns (name, color, direction, actions). Font-sizes tokenized.
- **Accept:** Visual parity.

### I.3 Category modal preview + styling  _(audit #55, 56)_
- **Mockup:** `overlay-15-create-category.html`.
- **Current:** `partials/categories/_form.html:99–120`.
- **Work:**
  - Fix preview: ensure JS listener re-renders the preview chip on color + name + direction change (HTMX hyperscript or small `addEventListener('input')` block scoped to the modal).
  - Match mockup swatch layout, preview-box spacing + fonts.
- **Accept:** Preview updates live; styling matches mockup.

---

## Phase J — Cross-cutting verification

For each of the above phases, upon implementation:

1. Run `just ci` (lint, typecheck, tests, pre-commit).
2. Run `frontend-visual-audit` skill against the routes touched at `1440 / 1024 / 375`.
3. Zero tolerance for: `horizontalScroll`, `overflowingElements`, `duplicateIds`, `consoleErrors`, `requestFailures`.
4. Compare against the matching mockup via side-by-side screenshots.
5. Append dated entry to `docs/CHANGELOG.md`.
6. Mark the related `docs/tasks.md` line with `✅` and the phase id.
7. Where a decision was made (e.g., unified entry modal; Settings auto-save), add/update an ADR under `docs/adr/`.

A final sweep after all phases:

- Re-run visual audit against **every** route listed in `docs/plans/v2/visual-audit-2/*` to ensure no regressions.
- Smoke-test the keyboard shortcuts (`g o`, `g l`, `g p`, `g a`, `g s`, `n`, `⇧↵`, `[`, `]`, `⌘K`).
- Verify dark mode (if applicable) and reduced-motion still behave.

---

## 2 · Acceptance criteria (global)

The plan is complete when all of the following hold:

1. Every id 0–56 in `docs/plans/v2/manual-audit.md` has a matching remediation commit in `feat/v2-rising-dough`.
2. Each of the 24 designer mockup HTML files has at least one implemented screen that visually corresponds to it at 1440.
3. `frontend-visual-audit` on `/`, `/ledger`, `/plan/budget`, `/plan/year`, `/plan/forecast`, `/plan/analytics`, `/accounts`, `/settings/categories`, `/settings/preferences` returns zero blocking signals at 1440 / 1024 / 375.
4. `just ci` is green.
5. `docs/CHANGELOG.md`, `docs/tasks.md`, and relevant ADRs are updated and committed.
6. The branch is rebased on `main` and ready to open as a PR with a test plan derived from this document.

---

## 3 · Risks and open questions

| Risk / question | Mitigation |
|---|---|
| Unified entry modal may break HTMX swap targets elsewhere | Grep all `hx-target` referencing `#add-entry` and update tests. |
| Category direction field may be missing on upcoming rows | Service work before template work. Add tests. |
| Day-group net calculation duplicates logic in ledger service | Introduce a single helper `ledger_day_net()`; both grouping views call it. |
| Analytics bento layout at 1024 | Mobile-first fallback: stack into single column; mockup is desktop-only. |
| "Over limit" vs "over the limit" wording | Pick one and apply consistently; recorded in the ADR. |
| Keyboard shortcuts in modal footer (⌘K, ↵, Esc) must stay functional | Add a dedicated test for the inline-promote flow. |

---

## 4 · Deliverables checklist

- [ ] Phase A commit(s)
- [ ] Phase B commit(s)
- [ ] Phase C commit(s)
- [ ] Phase D commit(s)
- [ ] Phase E commit(s)
- [ ] Phase F commit(s)
- [ ] Phase G commit(s)
- [ ] Phase H commit(s)
- [ ] Phase I commit(s)
- [ ] Phase J final verification pass
- [ ] ADR(s) added / updated
- [ ] `docs/CHANGELOG.md` entries
- [ ] `docs/tasks.md` ✅ lines
- [ ] PR opened with full test plan
