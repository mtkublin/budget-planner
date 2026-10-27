# ADR-0031 — Budget Page Composition v2: Income Anchor to Settings, Rules Row Override Popup, Yearly Grid

**Status**: accepted (2026-10-27)

**Context**

Phase 6 ([ADR-0023](0023-ux-redesign-information-architecture.md)) consolidated the Budget surface into three stacked sections: Monthly summary, Rules editor, Breakdown. Phase 9 ([ADR-0025](0025-user-preferences-and-income-anchor.md)) added a "Left to spend per day" hero at the top of `/budget` and a sibling "Income anchor" preference section (currently rendered as section 2b of `/budget`). Phase 8 ([ADR-0026](0026-fab-visibility-scope.md), T-094) narrowed the Rules editor to inline-only editing with a copy hint ("Rules are per category — edit any row inline"), explicitly ruling out a create affordance.

Field use after Phase 9 surfaces four frictions on `/budget`:

1. **The income anchor is a user *preference*, not a monthly budget decision.** Set once, changes rarely, lives on `/budget` next to the per-month rules it has no interaction with. The Settings drawer already carries a Preferences tab (`/settings?tab=prefs`, `templates/settings/_prefs.html`) — moving the anchor selector there is the obvious shape. ADR-0025 point 1 explicitly describes `user_preferences` as "soon-to-be-remembered filter scopes, chart defaults" — i.e., the Settings drawer scope.

2. **The current Rules table carries three editable columns per row** (default, recurring-this-month, one-off-this-month). Users read the row as "three equal rules for this category" when the actual F4.2 resolution rule is `one_off ?? recurring ?? default`. The two override columns ship for the *displayed month only* — editing them in month N and switching to month N+1 silently drops the recurring edit from the viewport. The surface over-promises on what's being edited and under-serves the common case ("set a default budget for groceries").

3. **No explicit create path.** Users expect "+" affordances to add things. T-094 shipped a copy hint ("edit any row inline") that documents the quirk rather than fixing it. The inline columns both discoverability-fail *and* over-render — the data the user needs for the current-month decision is `default`; everything else is an override that is better authored on demand.

4. **No cross-month view.** Users planning a quarter or a year have to visit `/budget?year=…&month=…` one month at a time. The resolved budget per `(category, month)` is a derived value from the existing three tiers; a 12-column grid is a thin read + inline-edit projection of data that already exists.

**Decision**

1. **Move the income anchor UI from `/budget` to `/settings?tab=prefs`.**
   - `templates/budget/index.html` section 2b ("Income anchor") is deleted.
   - `templates/settings/_prefs.html` gains a new `<section>` with the same `<select>` + submit form that currently lives on `/budget`. The deep-link anchor `#income-anchor` is preserved on the Settings drawer URL (`/settings?tab=prefs#income-anchor`).
   - `POST /budget/preferences/income-anchor` **stays at the same URL** — moving it would ripple into `HX-Trigger: budget-stale` listeners on `/budget` that currently depend on same-origin. The route lives in `routers/budget.py` for history; `routers/settings.py` does not duplicate it.
   - The "Left to spend per day" hero caption on `/budget` keeps its `"next income {date} ({anchor_category_name or 'end of month'})"` text and gains an inline "Change anchor →" link that opens `/settings?tab=prefs#income-anchor` so discoverability does not regress.

2. **Rewrite the Rules section as `category + default + Override`.** The three-column rules table is scrapped. Each row of the Rules editor now carries:
   - **Category** — one row per live expense category (unchanged from the current list).
   - **Default** — inline-editable amount input. Submits to `POST /budget/defaults/{category_id}` (unchanged endpoint). Empty value clears the default.
   - **Override…** — a `<button hx-get="/budget/rules/{category_id}/overrides/new" hx-target="#modal-root" hx-swap="innerHTML">` opening a slide-over scoped to that category.
   - The copy hint collapses to "Default budgets edit inline; use *Override…* to add a recurring or one-off exception."

   The Override slide-over form (`partials/budget/_override_form.html`, wrapped by `partials/_slideover.html` per [ADR-0030](0030-shared-form-interaction-primitives.md) §4) carries:
   - **Tier** — radio: `recurring` (applies to this month every year) / `one-off` (applies to one specific year-month).
   - **Month** — `<select>` 1–12, visible when either tier is selected.
   - **Year** — `<input type="number">`, visible only when `tier=one-off` (per [ADR-0030](0030-shared-form-interaction-primitives.md) §6 conditional-field pattern).
   - **Amount** — digit-only input per [ADR-0030](0030-shared-form-interaction-primitives.md) §2. Empty submits as "clear this override".
   - Hidden `category_id` carried from the row.

   New router handler `POST /budget/rules/{category_id}/overrides` acts as a thin tier-dispatcher that forwards to the existing `POST /budget/recurring/{category_id}/{month}` or `POST /budget/one-off/{category_id}/{year}/{month}` repository call (via internal function invocation, not an HTTP redirect). Emits `HX-Trigger: budget-stale`. 422 re-renders the form fragment; the slide-over stays open. On success the form clears per [ADR-0030](0030-shared-form-interaction-primitives.md) §5 and the slide-over closes.

   The Rules row **does not** show the resolved value for the displayed month — the Monthly summary table above already does that; duplicating here was the design mistake. The row shows only the default, which is the per-category decision Rules is actually about.

3. **Add a new Yearly budget table under Rules.** New section `#budget-yearly` with:
   - **Row** = one per live expense category.
   - **Columns** = Category, Jan..Dec (12 cells) for the currently-viewed year (`?year=` querystring; defaults to current year in `display_timezone`).
   - **Cell** = the F4.2 resolved budget for `(category, year, month)` — i.e., `one_off ?? recurring ?? default`. Rendered as:
     - **Bold** when the resolved value comes from a one-off override.
     - **Italic** when it comes from a recurring override.
     - **Plain** when it comes from the default.
     - **Em-dash** when no tier is set.
   - **Edit** = clicking a cell swaps the readout to an inline amount input (digit-only per [ADR-0030](0030-shared-form-interaction-primitives.md) §2); Enter / blur submits to `POST /budget/one-off/{category_id}/{year}/{month}` (unchanged endpoint). Empty value clears the one-off override, letting the recurring / default re-dominate on next render.
   - **Why one-off and not tier-aware edits.** Twelve editable cells per row times N categories is a surface too dense for a tier-picking affordance per cell. The design decision: Yearly table edits always write to the one-off tier for the viewed year/month. Users wanting a recurring (every-year) override use the per-row Override button in Rules. Keeps the two surfaces explicit about intent.
   - **Row totals** footer column: Σ of resolved values across the 12 months, read-only.
   - **Column totals** footer row: Σ of resolved values across categories for each month, read-only.
   - Year picker (prev / next arrows + `<input type="number">`) in the section header, mirroring the existing month picker on the Monthly summary section.
   - New HTMX fragment endpoint `GET /budget/yearly?year=…` returns the yearly table partial so year-switching does not force a full-page reload.

4. **No "+ Rule" button.** Earlier drafts of this ADR proposed one; the row-scoped Override pattern makes a global add-new button redundant (every expense category already has its own row). Users onboarding a new category create the category first (Settings → Categories), which immediately gives it a row in Rules; the default amount is edited inline on that row.

**Consequences**

Pros:

- Settings tab becomes the canonical home for preferences. ADR-0025's hypothesis ("many more preferences will accrete") now has a visible home for them.
- The Rules section surfaces exactly one decision per row (the default). Overrides are deliberate, opt-in, authored on demand — the surface no longer bluffs about editing three equal tiers.
- Yearly table unlocks the planning-across-months use case that Phase 6/9 did not cover. Zero new persistence; it is a projection over `budget_defaults` + `budget_recurring_overrides` + `budget_one_off_overrides`.
- Zero new database shape. All existing endpoints are the single source of truth for mutation; the Override slide-over dispatches to the two existing tier endpoints; the Yearly cell edits write to the one-off endpoint directly.
- Tier dominance is visible in the Yearly table via typography — users can see at a glance which months are overridden and how.

Cons / costs:

- Several existing integration tests on the three-column Rules table rewrite against the new one-column + Override surface. Expected churn, called out in the task file.
- Visual-regression baselines refresh on `/budget` (Rules redesigned + Yearly added + section 2b removed) and `/settings?tab=prefs` (anchor section added).
- Yearly table renders N × 12 cells; with 50+ expense categories the table gets long. Virtualisation is out of scope for v1 — this is a read + occasional-edit surface, not a hot path. Horizontal scroll is prevented by the existing `.ledger-scroll` wrapper.
- Cell-edit UX on the Yearly table (click to reveal input + Enter/blur to submit) is one more interaction primitive. It composes from ADR-0030 §2 (digit-only) and the existing inline-form shape; no new a11y pattern.

Explicit non-goals:

- **No new preference storage.** The anchor already lives in `user_preferences` per [ADR-0025](0025-user-preferences-and-income-anchor.md); only its UI location moves.
- **No change to `MonthSummary` / `services.budget.month_summary`.** The hero card arithmetic stays identical.
- **No tier-aware edits on Yearly cells.** One-off only. Recurring overrides use the Rules row Override button.
- **No deletion flow for rules outside the inline-clear path.** Setting an empty value in the inline default / Override form / Yearly cell is the delete path; `POST` with empty amount is treated as "clear this tier" by the existing repository functions (preserved behaviour).
- **No new three-tier model.** The existing `budget_defaults` / `budget_recurring_overrides` / `budget_one_off_overrides` tables stay the single source of truth.
- **No cross-year copy / paste tooling.** Deferred until a user actually asks.

**Alternatives considered**

- *Keep the anchor on `/budget`, just add a "Preferences" subsection to the Settings drawer that cross-links to it.* Rejected — duplicates the discoverability without actually moving the preference home. The anchor is not a budget decision.
- *Keep the three-column Rules table and add a `+ Rule` button.* Rejected — the three-column surface is the actual design mistake; adding a create affordance on top does not fix the "which column am I editing?" confusion.
- *Expose tier picking per Yearly cell (click → popover with tier radio).* Rejected — 12N cells × tier picker is a surface too dense; users wanting tier control have the row Override button.
- *Render the Yearly table as a chart.* Rejected — users wanted editable cells, not a visualisation.
- *Make the Yearly table a separate route (`/budget/yearly`) instead of a section.* Rejected — the two tables share the year + category list; co-location keeps context switches cheap.

**References**

- Amends / narrows: [ADR-0025](0025-user-preferences-and-income-anchor.md) §UI placement (anchor moves to Settings drawer; data model + endpoint unchanged); [ADR-0023](0023-ux-redesign-information-architecture.md) §Budget composition (Rules redesigned; Yearly added; section 2b removed); supersedes T-094 "inline-edit hint only" scope for the Rules section.
- Related: [ADR-0026](0026-fab-visibility-scope.md) (FAB stays off `/budget`; row Override button is per-section, not a FAB expansion), [ADR-0030](0030-shared-form-interaction-primitives.md) (slide-over + combobox + digit-only + clear-on-save + conditional fields reused), [ADR-0014](0014-budget-flat-no-rollover-three-tier.md) (three-tier resolution — unchanged).
- Requirements: [§2.4](../requirements.md#24-monthly-budget) (F4.5 rewritten, F4.6/F4.7 placement, F4.8 Yearly table), [§3.9](../requirements.md#39-ui--interaction-model) (Settings drawer gains Preferences subsections).
- Task breakdown: [Phase 11 — Shared Form Primitives + Overview Enhancements + Budget Page v2 + Fixes](../plans/v1/phase-11/README.md).
