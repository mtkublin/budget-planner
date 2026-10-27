# ADR-0028: Ledger Segmented Control — Full Navigation, Not Partial Swap

- **Status**: Accepted
- **Date**: 2026-10-27
- **Related**: ADR-0023 (UX redesign — IA + interaction model), ADR-0026 (FAB visibility scope)
- **Supersedes**: implementation approach in `T-092` (ledger segmented wiring) for the segmented control only. Filter form + pagination keep their htmx partial swaps.

## Context

The Ledger surface (`/ledger`) hosts three mutually exclusive views — Actual, Planned, Recurring — selected by a segmented control. `T-092` wired the segmented buttons as `hx-get` partial swaps against `#ledger-table`, with `hx-push-url` keeping the URL bar in sync. This made the tabs feel SPA-like: no full-page paint on switch.

Field use surfaced a defect that the partial-swap approach cannot solve without additional machinery:

- The quick-add FAB (`partials/_fab.html`) is rendered once in `base.html` at full page load. Its `hx-get` attribute is set to `fab_target_for(request)` evaluated against the **initial** request.
- When the user clicks a segmented tab, htmx swaps `#ledger-table` and `hx-push-url` updates `location.pathname + search`. The FAB node is **not** inside the swap target and htmx 2 does not re-evaluate attributes on untouched nodes.
- Result: landing on `/ledger` (Actual) → clicking Recurring → URL is now `/ledger?view=recurring`, the table shows recurring rules, but the FAB still points at `/transactions/new`. Pressing `+` (or `n`) opens the wrong create form. `fab_target_for` is correct per-request but never re-runs.

This is a general problem, not specific to the FAB. Any header-level or chrome-level affordance that depends on `view` (future per-view empty-state hints, help copy, keyboard-shortcut legends) has the same staleness mode under partial swap.

Three fix shapes were considered:

1. **OOB swap the FAB** from every segmented response. `/ledger/table` returns `#ledger-table` fragment + `hx-swap-oob` FAB. Works, but every partial-swap endpoint now has to re-render the FAB; FAB concern leaks into the ledger router. Repeat for every future context-aware chrome element.
2. **Client-side FAB target resolution.** Drop server-rendered `hx-get`, add a small JS mirror of `fab_target_for` that reads `location.search` on click. Works for FAB, but duplicates the context routing in two languages and leaves the staleness class open for any future server-rendered chrome.
3. **Full-page navigation for segmented tabs.** Replace `hx-get` + `hx-push-url` on segmented buttons with plain `<a href>`. Each tab becomes a GET to `/ledger?view=X`, which rebuilds the whole document — rail nav, filters, table, FAB, chrome — from a single server render. Trade: one paint on tab switch.

## Decision

Segmented tabs on `/ledger` navigate via plain `<a href>` links. The server render is the single source of truth for `view`-dependent chrome.

- Markup change: segmented buttons become anchors with `class="segmented__btn"`, `href="/ledger?view={{ v }}"`, `aria-current="page"` on the active one. No `hx-*` attributes on the segmented control.
- Filter form keeps `hx-get="/ledger/table?view=…"` against `#ledger-table`. Filters do not affect FAB target, so their partial-swap behavior stays as-is.
- Pagination keeps its partial-swap behavior for the same reason.
- `fab_target_for(request)` is unchanged.
- Keyboard shortcuts `[` / `]` cycle views by calling `location.assign("/ledger?view=…")` instead of clicking the segmented button, so the full-page render runs through the same path as the click.

## Consequences

### Pros

- One source of truth. `base.html` + per-view template render a coherent, non-stale document for every tab.
- FAB staleness fixed. Any future `view`-dependent chrome (hints, legends, per-view CTAs) stays coherent for free.
- No new client-side mirror of `fab_target_for`. No OOB-swap discipline required of every partial endpoint.
- Simpler mental model: segmented === navigation; filter/pagination === refinement within a view.
- Browser Back/Forward and middle-click-to-new-tab work by default on segmented tabs. `hx-push-url` already gave Back/Forward, but middle-click did nothing on a `<button>`.

### Cons

- One full-document paint on tab switch instead of a scoped swap. Local-first app on `127.0.0.1`; latency is negligible, visual flicker is minor and consistent with other nav rail clicks.
- Filter state entered on one view is lost when switching tabs, because the anchor's `href` only carries `view`. Acceptable: filters are view-specific (search text has different meaning across Actual vs Recurring); preserving them silently would be surprising. If a future requirement is "carry filters across views", that's an additive change (append preserved params to each tab's `href` server-side).

### Rejected alternatives

- **OOB swap the FAB** (option 1 above). Rejected: forces every partial endpoint to know about FAB rendering and keeps the FAB tightly coupled to the ledger surface's internals. Does not generalize to other context-aware chrome.
- **Client-side FAB resolver** (option 2). Rejected: duplicates `fab_target_for` in JS, keeps the staleness class open for future chrome, and introduces a sync hazard between the Python helper and its JS mirror.
- **Keep segmented htmx + make the FAB listen for `htmx:pushedIntoHistory`** and re-fetch its own target. Rejected: adds a client-side control loop for one widget; same generalization problem as option 2.

## Follow-ups

- `T-107` (new): implement the anchor conversion, update `shortcuts.js`, update tests, run `frontend-visual-audit`.
- Revisit if a future surface introduces a tab-like control where SPA-feel is a hard requirement (none planned in v1).
