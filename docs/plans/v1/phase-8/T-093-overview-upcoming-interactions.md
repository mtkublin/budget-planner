# T-093 [S] Overview — upcoming interactions

**Phase:** 8 — Post-redesign UX fixes
**Group:** G4
**Depends on:** T-063 (overview composition), T-069 (slide-over)
**Size:** S
**Status:** planned

## Scope

Fix two defects on the Upcoming panel:

1. Range segmented (7 / 30 / all) swaps `#upcoming-list` innerHTML but the segmented buttons never update their own active state. With empty data every range looks identical → user reports clicks are inert.
2. `+ Planned` button is a placeholder: `data-add-kind="planned"` with no `hx-*` wire → fully inert.

Server-side fix preferred (zero new JS, matches Phase 6 bar).

## Changes

- `src/budget_planner/web/templates/home/_upcoming_panel.html`:
  - Give the segmented group an id, e.g. `#upcoming-range`, and change the swap target of each range button from `#upcoming-list` to the whole panel header fragment (or add an `hx-select-oob` to re-render the segmented).
  - Simpler alternative: change `hx-target` to `#upcoming` and `hx-swap="outerHTML"`, re-render the whole panel from `/overview/upcoming`. Requires the fragment endpoint to return the panel wrapper, not just the list.
  - Preferred: keep list-only swap, add an **out-of-band swap** of the segmented group. `/overview/upcoming` returns:
    ```html
    {% include "home/_upcoming_list.html" %}
    <div id="upcoming-range" hx-swap-oob="outerHTML">
      {# re-rendered segmented with correct aria-pressed #}
    </div>
    ```
    Extract segmented markup into `home/_upcoming_range.html` so panel and fragment share one partial.

- `+ Planned` button:
  ```html
  <button type="button"
          class="btn-ghost panel__add"
          hx-get="/planned/new"
          hx-target="#modal-root"
          hx-swap="innerHTML"
          aria-label="Add planned payment">+ Planned</button>
  ```
  Drop the `data-add-kind` attribute.

- `src/budget_planner/web/routers/home.py`:
  - `upcoming_fragment` returns both the list include and the oob segmented block. Pass `window_label` into the segmented partial so active state resolves server-side.
  - No new route.

## Non-goals

- No change to planned data model.
- No change to `/planned/new` endpoint.
- No new JS file.
- No change to `#upcoming-list` live-event wiring (`txn-created`, `planned-stale`).

## Test plan

- Integration: GET `/overview/upcoming?window=7` returns both the list and the `hx-swap-oob` segmented block with `aria-pressed="true"` on the 7-days button.
- Integration: GET `/planned/new` returns the slide-over partial (already covered by T-069 tests — assert unchanged).
- E2E: click 30 days on Overview → segmented active state visibly moves + list reloads. Click `+ Planned` → slide-over opens.

## Docs

- `docs/CHANGELOG.md` — one dated line.
- `docs/plans/v1/tasks.md` — mark `✅ T-093`.
- No ADR (bug fix + copy wiring).
