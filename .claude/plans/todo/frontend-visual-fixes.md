# Frontend Visual Audit — fix list (post-sweep 2026-10-29)

Audit ran at desktop 1440 against live app + every modal captured. Each
line below quotes the mockup file + the live screenshot where the delta
shows up. All mockups live under `docs/application_redesign_handoff/`
(screens/ for raw HTML, mockups/screenshots/ for PNG renders).

Legend: **S** = screen, **M** = modal.

## Critical: modal paradigm

Every mockup overlay is a CENTERED modal card (scrim behind). Current
implementation renders every overlay as a right-slide-over, which is a
whole-shape divergence.

- **M · all overlays** · `partials/_slideover_page.html` + `partials/_slideover.html` + `partials/_add_entry_overlay.html` → rebuild as `.rd-modal` centered-scrim shell. Current slide-over markup + CSS stays only for narrow mobile (`@media (width <= 640px)` sheet-up variant).
- **M · add-entry** · host markup must be a centered `.rd-modal` card max-width 560–640px; header carries `New entry` + `Esc` chip right.
- **M · create-account / create-category / reconcile** · same centered pattern.

## Today — `desktop___today.png`

- **S · hero amount** · mockup `desktop-01-today.html:8` renders big number in `font: 400 96px 'Newsreader'`. Current (`rd-hero__amount > span.num`) forces IBM Plex Mono. Remove `.num` from span, let `.rd-hero__amount` use `var(--font-display)` + `font-variant-numeric: tabular-nums`. Separate `.rd-hero__cur` already OK.
- **S · promote-all-due button** · mockup `desktop-01-today.html:17` renders all three buttons as `.btn.s` (grey outline). Current renders `Promote all due` with `rd-btn--primary` (blue). Drop `--primary`, keep ghost. All three identical.

## Ledger — `desktop___ledger.png`

- **S · columns** · mockup `desktop-02-ledger-actual.html:7-9` has: Description(+account subtitle) | Category pill | Direction chip | Amount | ⋯. Current adds Date column + drops Direction column. Fix: delete Date `<th>` and date `<td>`, restore Direction `<th>` + `<td>` with `direction_badge`.
- **S · description cell** · mockup renders `<strong>cinema city</strong><br><span class="mut">karta kredytowa</span>`. Current renders `<strong>desc</strong>` on one line + account on a separate col. Collapse into one cell `<strong>desc</strong><br><small class="mut">account</small>`.
- **S · day group header** · OK (left date band + right net).
- **S · pagination** · "← Newer / Older →" as `.btn.s` outline buttons. Already applied.

## Accounts — `desktop___accounts.png`

- **S · account cell** · mockup `desktop-09-accounts.html:7` has name + type inline (`<span serif>IKZE (mBank)</span> <span mut 12px>investment</span>`). Current renders name on top + type in `<small>` on next line. Switch to inline.
- **S · kebab column** · mockup has NO `⋯` kebab column; only `Reconcile` button. Delete the trailing kebab TD (actions header already `.sr-only`).
- **S · liability row** · mockup `desktop-09-accounts.html:7` last row shows `<span class="pill rd-pill--expense">credit card · liability</span>` inline next to the account name + a limit bar + "Limit N · Available N · Used N%" line. Current partially matches but liability pill wraps on second line because it's inside `.rd-desc` instead of inline next to the name.
- **S · "Checked" chip** · mockup varies ("today" / "14 Oct" / "14 days ago"). My live screenshot shows all rows "01 Apr" — fixture seed doesn't exercise the branch; verify tag logic + colour tokens.

## Plan — Budget — `desktop___plan_tab_budget.png`

OK overall. Minor:

- **S · top-right period selector** · mockup label is "October 2026" (no change) — ✓.
- **S · bar top-row amount** · number is mono 26px per mockup — ✓.

## Plan — Year — `desktop___plan_tab_year.png`

- **S · year selector** · mockup `desktop-06-plan-year.html:4` places selector in header slot — ✓.
- **S · cell colouring** · mockup cells use `--expense-soft` background on all expense months. Current renders mostly red fills with heavier contrast; verify `heatmap_cell` tier colours against mockup swatches.
- **S · legend ordering** · mockup has 4 swatches with the labels I've shipped — ✓.

## Plan — Forecast — `desktop___plan_tab_forecast.png`

Mockup `desktop-07-plan-forecast.html`:

- **S · annotation strip** · mockup renders a muted `Oct 2026 → Sep 2027 · PLN · budget overlay on` caption directly beneath the h1. Current drops it. Add.
- **S · chart annotations** · mockup shows per-dot callouts (e.g. "Mar: +43,200 unit8 PROFIT SHARE" + "Sep: 22,195 planned, incl. 16,000 holiday"). Current never emits these. Add service-level annotation extraction; for now wire data=None path gracefully.
- **S · footer caption** · "Oct row comes from the Budget summary so both pages agree. All figures in PLN base." Current drops it. Add.
- **S · NET column** · mockup shows per-row dot marker alongside the value (green/red). Current renders colour-only. Dot marker is cosmetic; keep deferred.

## Plan — Analytics — `desktop___plan_tab_analytics.png`

- **S · period selector in body** · mockup `desktop-08-plan-analytics.html:5` places month-nav + Month/3 months/YTD/12 months segmented INSIDE the tab body (not in the shared Plan header). Current puts them in the shared header. Move back into the body + duplicate month-nav from shared slot when `tab == "analytics"` to match. (D.1 was over-eager; Analytics selector is a different widget.)
- **S · "VS 12-MO AVG" column** · mockup shows raw signed delta `+1,162.90` / `−205.12`, not a percent. Current shows `+236% vs 12-mo avg` label. Fix: render the raw delta as `.num.{pos|neg}`.
- **S · column headers** · mockup emits `CATEGORY | OCTOBER | VS 12-MO AVG` eyebrow headers above the list. Current list has no column headers. Add.
- **S · footer caption** · "Click a category to open its transactions in Ledger. Red means above the 12-month average." Current already renders this.
- **S · Income-vs-expense panel** · mockup caption below bars: "Bars follow your current chart (approximate). Oct: about +11.2k surplus." Current drops it.
- **S · Largest items** · mockup: `VAT · 15 Oct` left, `5,441.00` right. Current shows: name + date together left, amount right. OK.

## Settings — Categories — `desktop___settings_tab_categories.png`

- **S · anchor bar** · mockup `desktop-10-settings-categories.html:6` is single-line: `<p class="eyebrow">Income anchor</p>` + body + green pill selector right. Current wraps into 2–3 lines. Rebuild as flex row.
- **S · column headers** · mockup has NO `NAME DIRECTION COLOUR ACTIONS` row. Each section (`Expense 16`, `Income 6`, `System read-only`) is just a short header + rows. Remove `<thead>`.
- **S · section headers** · mockup renders `Expense 16` with light-weight prefix + size badge. Current renders uppercase eyebrow `EXPENSE · 16`. Convert to display font `h3 class="rd-settings-cats__group"` with inline count badge.
- **S · row actions** · mockup renders `Edit · Archive` as plain text links separated by middle-dot. Current uses button-styled chips. Convert to `<a>`-styled text links.
- **S · colour cell** · mockup renders `<span class="dot" style="background:#hex"></span> Override · magenta` (name of hue). Current shows `● Override`. Add colour name.

## Settings — modal (Create category)

- **M · overlay chrome** · as above: must be centered modal, not right slide-over.
- **M · preview strip** · mockup `overlay-15-create-category.html` renders a tinted strip at bottom "PREVIEW   zwierzęta ↓ EXPENSE". Current shows preview but needs the muted strip background wrap.
- **M · colour swatches** · mockup renders filled circles (not oklch rings). Current uses `.rd-swatch` with `--swatch` filled circle — likely close; verify size + border.

## Modal — Create account

- Wrap in centered modal.
- Row layout matches mockup after that.

## Modal — Add entry (Happened)

- **M · remove Dest field** · mockup `overlay-13-add-fixed.html` has only Category / Amount / Account+Date / Note. Dest is Repeats-only.
- **M · Amount block** · mockup renders big display-font amount `32.00 PLN` with underline accent + "leaves 187.87 / day after this" callout. Current renders Amount as a plain text input w/ cur suffix. Add live preview below the input.
- **M · "Fixed value / Formula ƒ" segmented** · mockup places this on the Amount row, right-aligned. Current puts it only inside the Recurring tab. For Actual + Planned the segmented should still show (even if Formula is disabled for Actual) — defer.
- **M · footer** · mockup footer: left = `⌘↵ save and add another`, right = `Cancel` `Save ↩`. Current has only right side. Add the left-side hint.

## Modal — Add entry (Repeats, formula)

Mockup `overlay-12-add-formula.html`:

- **M · Repeats sub-label** · tab reads `Repeats · monthly` when cadence is picked. Current shows `Repeats`.
- **M · Transit indicator** · when category is Transit, header shows two chips (`TRANSIT`, `⇄ TRANSIT`) + "direction comes from the category" muted. Add.
- **M · From / To row** · when transit, Account splits into From | To. Current only has Account | Dest. Rename to From / To when direction is transit; omit Dest for non-transit.
- **M · Formula terms row grid** · mockup is `62px 1fr 76px 120px` grid: `+ ▾` sign chip | source selector | `100 %` | computed amount. Current renders chips + checkbox list below each term. Flatten to a single row per term.
- **M · Result footer** · mockup shows `+ Add term` left + `result 15,650.66 PLN` right. Current only has `+ Add term`.
- **M · Description + Next due row** · mockup: Description (full-width input) + Next due · Cadence (2-chip row). Current has Day of month + Note. Add Next due date + cadence selector.
- **M · Save button copy** · "Save rule ↩" (not generic "Add rule").

## Modal — Budget override

- **S/M · placement** · mockup `desktop-05-plan-budget.html:9` renders the override as an INLINE card beneath the table (not a modal). Current launches as a modal. Fix: GET `/budget/rules/{id}/overrides/new` should return a fragment that mounts into `#budget-override-slot` under the table; close by HTMX swap replacing the slot.
- **M · card chrome** · once inline, use accent-border card w/ segmented tier chips + bordered amount input + Save button + default hint. Already have the markup — just change host from `#modal-root` to a dedicated slot.

## Modal — Reconcile

Mockup `overlay-11-reconcile.html`:

- **M · chrome** · centered modal (not slide-over).
- **M · step chips** · ① Open your bank · ② Enter its balance · ③ Review. Already present in `T-R39` but formatting looks off in live render — verify after moving to modal.
- **M · two-input layout** · `RISING DOUGH SAYS | YOUR BANK SAYS` with big display-font numbers. Already present.
- **M · Difference callout** · amber-tinted block showing `−28.90 PLN` + explanatory copy. Present.
- **M · Record-as combobox** · select category for the adjustment (defaults to `± ADJUST Reconciliation (system)`). May be stubbed in current markup.

## Execution order (impact-ranked)

1. **Centered-modal shell** (one CSS pattern, applied to every overlay host) → single commit fixes shape for 5 overlays. ✅ `6ddb4e0`
2. **Today hero typography fix** (remove `.num` from big amount span). ✅ `6ddb4e0`
3. **Today promote-all-due** button variant swap. ✅ `6ddb4e0`
4. **Ledger column rewrite** (desc+account, drop Date, restore Direction). ✅ `6ddb4e0`
5. **Accounts row rewrite** (inline name + type, drop kebab col, inline liability pill).
6. **Settings Categories rewrite** (remove thead, inline anchor bar, Edit·Archive links).
7. **Plan Analytics** (selector back into tab body, raw delta column, column headers).
8. **Budget override inline** (not modal).
9. **Add-entry modal field order** (no Dest, big amount preview, footer hint).
10. **Add-entry Repeats formula** (From/To, flat term grid, Next due row).
11. **Plan Forecast caption + annotations** (muted strip + footer).

## Session-3 additions (user-reported after wave-1 fixes)

**V.17 Upcoming revert after Esc.** Promote inline → Esc hits GET `/overview/upcoming` which returns `home/_upcoming_fragment.html` (the legacy Overview surface). Today's `#upcoming-root` swaps in a different template structure, breaking the pills + row grid. Fix: `/overview/upcoming` needs to detect the referer / add a `?for=today` variant that returns `today/_upcoming.html` with the categories_by_id + accounts_by_id context the new template expects. Alternatively, swap the inline promote cancel to re-fetch `/today` and `hx-select="#upcoming-root"`.

**V.18 Entry chips centered.** `.rd-entry-chips` currently `justify-content: flex-start`. Change to `justify-content: center`.

**V.19 Ledger/Planned table formatting broken.** Likely a rendering fallout from V.4 column rewrite because planned rows use `row.operation_date|date_fmt` in the muted sub-line but the old `Date` col removal left a tbody col-count mismatch. Needs a direct screenshot comparison vs `desktop-03-ledger-planned.html`.

**V.20 Budget tab month full sync.** `plan/_budget_tab.html` top bar reads `summary.period_start → summary.next_income_date` which are computed by `budget_service.month_summary(year, month)`. Threading year+month into the summary already works (the per-day amount changed in the audit). But the header `<h1>October budget</h1>` is a static title map in `plan/index.html` + the period_start/next_income_date might still reflect anchor-based calculation using *today's* position, not the start of the selected month. Verify: when month=9 (September), period_start should be in Sep. Fix the service to accept an explicit `month_start` ref, not use `today` for anchor lookup.

**V.21 Analytics month selector effect.** The shared Plan header month selector only threads year+month into `budget_service.month_summary`. Analytics bundle computed via `analytics_service.bundle(conn, today=today_d, period=period_norm)` — `today_d` is always the real today. Need to swap `today_d` for `date(year, month, 1 + last_day_of_month(year, month))` when `month != today's month` so the Analytics period respects the picker.

**V.22 Year grid colors v2.** First attempt kept the `.rd-heat` width 100% + height 34px + expense-soft bg but the tiles still render with heavy red fills. Audit — likely the `color-mix` falls back to full `--expense` at 100% weight CSS var still set from the heatmap_cell macro. Delete `--weight` plumbing + accept the plain expense-soft fill. Reference mockup inline style: `background: oklch(0.955 0.035 28)` which is `var(--expense-soft)` directly.

**V.23 Year override popover inline.** Year cell button currently HTMX-swaps into `#modal-root`. Change to inject into a `.rd-year-popover` positioned absolute beneath the clicked tile. HTMX supports this via `hx-target="closest td"` + a wrapper div.

**V.24 Modal no scroll fit.** `.slide-over` has `overflow-y: auto; max-height: calc(100vh - 80px)`. Modal body content exceeds that → scroll. Switch to `max-height: 95vh` and shrink interior padding; critical content (header + chip row + fields + footer) must fit without scroll on 1440×900. Narrow bodies via `max-width` already; need vertical compression on `.rd-form` default row gap.

**V.25 Reconcile fit.** Same fix as V.24; reconcile body is long because it has 3 steps + Previous Checks list. Hide Previous Checks on height-constrained viewports or collapse behind a toggle.

**V.26 Year header sync.** `plan/index.html` title map uses `'Budget ' ~ year` — the context key is `year` (current year from router), not `year_selected` (user picked). Line 9 fallback should read `year_selected if tab == 'year' else year`.

## Session-2 additions (user-reported after audit)

**V.9 Ledger/Planned rows missing.** Planned header shows count 2 and the forecast table emits the rows, but the Ledger `/ledger?view=planned` table body is empty. Likely a filter in the ledger router that passes `promoted=False` but reads from a different repository call than Overview. Trace `routers/ledger.py` → `_hydrate_planned_rows` → `planned_repo.list_filtered`.

**V.10 "Can I afford it?" calc broken.** `services/today.py::afford` returns `delta_minor = per_day - baseline_per_day` where `per_day` is clamped at zero when the hypothetical spend exceeds remaining. For `amount=1000` with `days_left=9` and `remaining=1910.78`, expected `per_day_after = (1910.78 - 1000) / 9 ≈ 101.20`, delta ≈ `−111.08`. Live shows `−1.11 / day` which is way off — likely a division-by-months bug or an off-by-100 (minor units). Add a focused unit test with fixed inputs and fix.

**V.11 Ledger · Recurring expand UX.** Current expand uses a `<details>` chevron accordion that renders the raw list of overrides + a formula breakdown table. Mockup `desktop-04-ledger-recurring.html:10-13` expects a single chevron per row that reveals a card showing: formula terms grid (`+ ▾ source ▾ 100 % value`) + overrides list formatted like inline chips. Current markup is both ugly and inside a `<details>` instead of HTMX reveal.

**V.12 Plan monthly selector.** `plan/index.html` renders `<a>` arrows and plain `<span>` label. (a) The links target `/plan?tab=budget&year=&month=` but the router computes `prev/next` months — need to verify the URL actually loads a different `month`; current audit shows the URL changes but the summary doesn't. (b) The label `October 2026` must be clickable → opens a lightweight month-picker (12-cell grid). Change label from `<span>` to a `<details>` disclosure OR `<button>` that renders a popover.

**V.13 Plan · Year grid colours + margins.** Mockup `desktop-06-plan-year.html:6-7` uses soft expense-wash tiles with tight 2-3 px gaps. Current `rd-table` renders tiles with large padding and heavier expense red. Shrink padding on `.rd-plan-year__table td`, swap the active-cell fill to `var(--expense-soft)` with `color: var(--expense)` text, and the one-off/recurring markers to the typography-only versions from the mockup legend.

**V.14 Analytics period selector dead.** `plan/_analytics_tab.html` currently emits `segmented(..., base_href='/plan?tab=analytics&')` — but the shared Plan header already renders the month selector and the segmented should sit INSIDE the tab body (per mockup `desktop-08-plan-analytics.html:5`). The segmented links point at `/plan?tab=analytics&period=…`; router reads `period` only via `request.query_params.get("period", "month")`. Verify URL round-trip. Likely the issue is that `period` isn't threaded into the `ctx` returned from the `/plan` dispatcher when `tab == "analytics"` — the current code only reads `period` for the fallback `else` branch, not when the shared selector loop is active.

**V.15 Add-entry chip row.** Mockup renders three chip buttons `Happened / Planned / Repeats` sharing a thin line border, with the active one filled dark (`.chip.on` → `background:var(--ink); color:var(--bg)`). Current markup uses `rd-segmented` with a tight bordered box, so the active chip blends into the modal background and the inactive text looks faint. Rebuild as free-standing `.rd-chip` pills using the same `rd-chip` util used elsewhere (not inside `.rd-segmented`).

**V.16 Modal scrim overlay.** User reports modals appear on a BLANK page — the host page vanishes when the modal opens. Root cause: HTMX `hx-get` fires with `hx-target="#modal-root"` + `hx-swap="innerHTML"` which should ONLY replace `#modal-root` contents. BUT: `transactions/new`, `planned/new`, `recurring/new`, `accounts/new`, `categories/new`, `/add` responses return a full `base.html`-extended page (not a fragment). When injected into `#modal-root` they bring their own `<header>`+`<main>`+rail, bloating the DOM, and the CSS `.slide-over-root { position:fixed; inset:0; background:oklch(82% 0.01 85) }` paints a solid tan sheet over the viewport that happens to look like a blank page. Fix:
- All modal GET endpoints must return a bare fragment (`partials/_slideover_page.html` wrapper around the form body), NEVER a full page.
- Scrim colour: switch from `oklch(82% 0.01 85)` (opaque tan matching the body!) to `color-mix(in oklab, var(--ink) 32%, transparent)` (semi-transparent ink) so the host page shows through.
