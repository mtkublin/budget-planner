# Phase 8 — Post-redesign UX fixes

> Driven by hands-on report (2026-10-27) after Phase 6 landed. Ten observations, consolidated into five change groups. Scope is **UX bugfix + polish only**; no new features, no new data, no scope creep into Phase 9 (user preferences) or Phase 7/v2.

## Observations (raw)

1. Pages behave like fixed-width — horizontal scroll appears instead of flex-fit.
2. Nav rail height overflows — nav should always be fully visible.
3. Round `+` FAB visible on every page; expected only on Ledger (and maybe Overview).
4. New-transaction slide-over fields are a 2-column grid — should be one input per row.
5. Ledger segmented control (Actual / Planned / Recurring) does nothing when clicked.
6. No visible path to create a Planned or Recurring entry.
7. Overview → Upcoming: segmented (7 / 30 / all) appears inert; `+ Planned` button is unclickable.
8. Budget → Rules table has no `+ Rule` affordance.
9. Add-category form: same 2-column layout problem as (4).
10. New-account form: same 2-column layout problem as (4), (9).

## Root-cause analysis

| # | Root cause | Evidence |
|---|---|---|
| 1 | `.app-shell__main` has `max-width: 1200px` but no `min-width: 0`; children tables (budget rules, ledger) can push past the grid column, forcing body scroll. `.app-shell` is `min-height: 100dvh` (not `height`) so content below the fold scrolls, which is correct behaviour but combined with (2) feels broken. | `src/budget_planner/web/static/app.css:160-204` |
| 2 | `.app-shell__rail` has fixed padding + gaps; on short viewports the 4-item list + wordmark + Settings footer overflow 100dvh with no scroll affordance. | `app.css:167-241` |
| 3 | FAB is unconditionally rendered in `base.html` via `{% include "partials/_fab.html" %}`. `fab_target_for` defaults every non-ledger page to `/transactions/new`. | `base.html:43`, `web/context.py:15-35` |
| 4,9,10 | All `_form.html` partials use `class="grid grid-cols-2 gap-3"` — a hard 2-col grid regardless of container width. Slide-over width is 480px → each column ≈ 220px → cramped. | `partials/transactions/_form.html:5`, `partials/accounts/_form.html:4`, `partials/categories/_form.html:4`, `partials/planned/_form.html:4`, `partials/recurring/_form.html:4` |
| 5 | **Hard bug.** Segmented buttons `hx-target="#ledger-table"`; the rendered table id is `txn-table` / `planned-table` / `recurring-table` (preserved from legacy). HTMX swap finds no target → no-op. | `ledger/index.html:23`, `ledger/_table.html:9-14` |
| 6 | Planned/Recurring create pages exist (`/planned/new`, `/recurring/new`); FAB already routes to them when `view=planned|recurring`. But (5) means the user never changes view, so FAB keeps targeting `/transactions/new`. Fix (5) → fix (6). | `web/context.py:20-35`, `ledger_types.py` |
| 7a | Overview upcoming segmented `hx-swap="innerHTML"` on `#upcoming-list` works — but no visible active-state update on the segmented buttons themselves, and when the planned log is empty every range returns the same empty message, so clicks look inert. | `templates/home/_upcoming_panel.html:10-18` |
| 7b | `+ Planned` button has `data-add-kind="planned"` and no `hx-*` wire → fully inert. | `templates/home/_upcoming_panel.html:19-23` |
| 8 | Budget rules table renders one row per existing category with inline `default / recurring / one-off` forms. Discoverability is poor: there's no explicit `+` affordance and the eyebrow "Rules" header offers no instruction. The data model doesn't need an `add rule` — rules are per-category — so this is a UX wording / affordance issue, not a missing endpoint. | `budget/index.html:118-203` |

## Change groups

Five groups; each has acceptance criteria. Order is bottom-up (least-risky first).

### G1 — Shell + rail layout fit (obs 1, 2)

- `.app-shell__main` adds `min-width: 0; overflow-x: auto` on child tables (via `.ledger` and `.budget-rules-table` wrappers), not on `main` itself (prevents hiding real overflow).
- `.app-shell__rail` becomes a flex column with `overflow-y: auto` only when its intrinsic height exceeds viewport (`max-height: 100dvh; min-height: 0;`). Reduce vertical rhythm (`--space-5` → `--space-4` on nav gap) so the 4-item list + wordmark + Settings fit without scroll on 720px viewports.
- No markup changes to `base.html` beyond adding a wrapping class on tables that are known to overflow (optional; CSS-only path preferred).
- Acceptance: at 1280×720 and 1024×768 the shell renders with zero horizontal scroll and the rail footer (Settings) is visible without scrolling.

### G2 — One-field-per-row form layout (obs 4, 9, 10)

- Introduce a shared `.form-stack` component in `app.css` (vertical flex, consistent label/input rhythm, right-aligned action row).
- Replace `grid grid-cols-2 gap-3 p-4 border …` on every `partials/*/_form.html` with `class="form-stack"`.
- Keep `col-span-2` behaviour via `.form-stack__full` for action row.
- Numeric inputs stay right-aligned (already handled by `input[name="amount"]` rule).
- Acceptance: every create/edit form (Transaction, Planned, Recurring, Account, Category) in the slide-over or inline shows one labeled input per row, consistent gap, action row flush right.

### G3 — Ledger segmented wiring fix (obs 5, 6)

- Pick **one** target convention. Preferred: wrap `_table.html` in `<div id="ledger-table">` *and* keep legacy `#txn-table` / `#planned-table` / `#recurring-table` ids on the inner table/div for test compatibility.
- Segmented `hx-target="#ledger-table"` then swaps the correct wrapper. The response fragment must include the same wrapper id (not just the inner element) — a one-line change in `_table.html`.
- `hx-swap` stays `outerHTML`.
- Side-effect: FAB `fab_target_for` begins routing per-view correctly once users can actually switch views (resolves obs 6 without code change in `context.py`).
- Acceptance: integration test asserts clicking each segmented button swaps the table body and keeps `#ledger-table` present. Legacy test selectors still pass.

### G4 — Overview upcoming interactions (obs 7)

- Wire `+ Planned` button: add `hx-get="/planned/new" hx-target="#modal-root" hx-swap="innerHTML"` and remove `data-add-kind` placeholder.
- Fix segmented active-state after swap: either swap the whole `panel__header` region (change `hx-target` to `#upcoming` with a dedicated `oob` swap of the segmented block), or add 4 lines of JS listening on `htmx:afterSwap` to re-apply `aria-pressed` + `--active` class based on the clicked button. Prefer the server-side approach (keeps the "no new JS" bar from T-068).
- Empty-state copy already distinguishes "no planned payments in this window" vs. no planned at all — unchanged.
- Acceptance: clicking 7 / 30 / all swaps content *and* visibly moves active state; clicking `+ Planned` opens the planned form slide-over.

### G5 — FAB visibility + Budget rules affordance (obs 3, 8)

- `fab_target_for` returns `None` on `/accounts`, `/budget`, `/settings`, `/forecast`, `/analytics` → base template skips the include when `None`.
- FAB stays visible on `/` (Overview) → defaults to `/transactions/new`.
- FAB stays visible on `/ledger` (any view) with view-aware target.
- Budget rules section header gets a plain-text hint ("Edit per-category rules inline — one row per category. Totals recalculate on save.") so the lack of a `+` button reads as intentional. No new endpoint.
- Decision captured in **new ADR-0026** (narrows ADR-0023 affordance #4 scope). ADR-0023 is referenced, not superseded (the IA decision stands).
- Acceptance: FAB does not render on Accounts / Budget / Settings / Forecast / Analytics; still renders and context-routes on Overview + Ledger. Budget rules copy clarifies editing model.

## Phase 8 handoff

- Each group has a task file in this directory (`T-090`..`T-094`) with scope, test plan, and docs-to-touch. IDs chosen as successors to Phase 7 (last `T-086`); Phase 9 (user preferences) uses `T-095..T-101` as successors to this phase.
- Group order: G1 → G2 → G3 → G4 → G5 (so form layout exists before FAB scope changes assume a correct slide-over).
- Every task updates `docs/CHANGELOG.md`, `docs/plans/v1/tasks.md`, and either `docs/requirements.md` (if UX-user-facing) or an ADR (G5 only).
- All tasks are **S** (sequential within phase), small, bug-fix / polish — not architectural.

## Non-goals

- No new routes, no new DB tables, no new services.
- No new JS framework; command-palette + shortcuts stays as-is.
- Budget "add rule" is **not** added — rules are per-category and already enumerated.
- Phase 9 (user preferences / income anchor) is independent and continues on its own track.
