# T-094 [S] FAB visibility scope + Budget rules affordance

**Phase:** 8 — Post-redesign UX fixes
**Group:** G5
**Depends on:** T-069 (FAB), T-092 (segmented wiring — so FAB routing has somewhere to go)
**Size:** S
**Status:** planned

## Scope

1. Narrow FAB visibility to Overview + Ledger only. Hidden on Accounts, Budget, Settings, Forecast, Analytics. Current behaviour of showing the FAB on every page produces an irrelevant `+ Transaction` on surfaces where it is the wrong action.
2. Budget rules section already contains per-category rows for default / recurring / one-off. There is no missing endpoint. Add a one-line hint in the section header so the inline-edit model reads as intentional, closing the discoverability gap.

Decision captured in **ADR-0026** — narrows ADR-0023 affordance #4 (quick-add FAB) to the surfaces where the "add a money event" action is primary.

## Changes

- `src/budget_planner/web/context.py`:
  - `fab_target_for(request)` returns `str | None`.
  - Allow-list: path `== "/"` → `/transactions/new`; path starts with `/ledger` → view-aware (unchanged logic for planned/recurring).
  - Everything else → `None`.
  - Keep docstring in sync; cite ADR-0026.

- `src/budget_planner/web/templating.py`:
  - Jinja global `fab_target_for` unchanged (returns `None` is fine).

- `src/budget_planner/web/templates/base.html`:
  - Wrap the FAB include:
    ```jinja
    {% block fab %}
      {% if fab_target_for(request) %}
        {% include "partials/_fab.html" %}
      {% endif %}
    {% endblock %}
    ```

- `src/budget_planner/web/templates/budget/index.html` — rules section header gets an inline hint, e.g.:
  ```html
  <p class="text-muted text-sm">
    Rules are per category. Edit any row inline — one-off wins over recurring wins over default. Totals recalculate on save.
  </p>
  ```
  Replace the existing muted line in the Rules section header.

## Non-goals

- No new endpoint for "add rule". Rules are per-category; the enumeration already covers every category.
- No change to budget service or repository.
- FAB does **not** gain a new target type (no `/budget/rules/new`).
- No change to keyboard shortcut `n` — if no FAB on the current page, `n` falls back to the command palette (already wired in `shortcuts.js:64-70`).

## Test plan

- Unit: `fab_target_for` returns `None` for `/accounts`, `/budget`, `/settings`, `/forecast`, `/analytics`.
- Unit: `fab_target_for` returns correct URL for `/`, `/ledger`, `/ledger?view=planned`, `/ledger?view=recurring`.
- Integration: GET `/accounts` HTML does not contain `data-fab`.
- Integration: GET `/` and `/ledger` do contain `data-fab`.
- Keyboard regression: pressing `n` on `/budget` opens the command palette (fallback path).

## Docs

- **New ADR-0026** — "Quick-add FAB visibility scope". Status: Accepted. References ADR-0023 (does not supersede — IA decision stands; only narrows affordance #4). Explains the Overview + Ledger allow-list and the rationale for not adding a `+ Rule` affordance on Budget.
- `docs/adr/README.md` — new entry for ADR-0026.
- `docs/CHANGELOG.md` — dated line.
- `docs/plans/v1/tasks.md` — mark `✅ T-094`.
- `docs/requirements.md` — section covering nav + quick-add gets a one-line clarification referencing ADR-0026.
