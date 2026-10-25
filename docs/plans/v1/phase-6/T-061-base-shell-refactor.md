# T-061 — Base Shell Refactor

> Phase 6 — UX redesign. Status: pending.

## Purpose

Reshape `base.html` into the new 4-tab shell: a 220 px left rail nav, a main content region with fluid gutters, a persistent `#drawer-root` slot (Settings drawer, T-067), a persistent `#modal-root` slot (Promote modal and future overlays), and a fixed bottom-right FAB slot (Quick-add, T-069). Preserve every Jinja block name downstream templates extend so nothing silently breaks. Reuse the T-053 token layer verbatim; this task is composition only — no new tokens, no new palette.

## Inputs / prerequisites

- Upstream tasks: T-060 (ADR-0023 landed).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — defines the 4-tab IA, drawer-root / modal-root contract, FAB placement.
- Adjacent standards: [`ADR-0002`](../../../adr/0002-web-stack-fastapi-htmx-jinja.md) (FastAPI + HTMX + Jinja + Tailwind CDN), T-053 tokens (`static/css/tokens.css`, `static/css/components.css`).
- Existing shell: `src/budget_planner/web/templates/base.html` + `partials/_nav.html` (both will be mutated; T-062 rewrites `_nav.html`).

## Deliverables

Updated files:

- `src/budget_planner/web/templates/base.html`:
  - CSS grid shell: left rail column (fixed 220 px) + main column (fluid, `max-width ~1200 px`, gutter from `--page-gutter`).
  - Keep `{% block title %}`, `{% block head_extra %}`, `{% block nav %}`, `{% block main %}`, `{% block scripts %}` with their current names and positions.
  - Add after `{% block main %}`:
    - `<div id="drawer-root" aria-live="polite"></div>` — T-067 HTMX injects into this.
    - `<div id="modal-root"></div>` — Promote modal and future overlays mount here.
    - FAB slot: `{% block fab %}{% endblock %}` so pages can override; default renders the Quick-add FAB (T-069) via `{% include "partials/_fab.html" %}`.
  - Load order (unchanged except for the new slot markup): Tailwind CDN → `tokens.css` → `components.css` → `a11y.css` → page-specific head extras.

New files: none in this task. (`partials/_fab.html`, `partials/_drawer.html`, `partials/_palette.html` are owned by T-069 / T-067 / T-068.)

Not deliverables:

- No nav markup changes (T-062).
- No drawer or FAB implementation (T-067 / T-069).
- No JS listeners (T-068).

## Step-by-step

1. **Snapshot current `base.html` block names** before editing. Run `grep -nE '{% block ' src/budget_planner/web/templates/base.html` and record. The rewrite must keep `title`, `head_extra`, `nav`, `main`, `scripts` names and relative order.
2. **Introduce the grid shell.** Wrap the current `<body>` content in a 2-column CSS grid using tokens from T-053:
   ```css
   .app-shell { display: grid; grid-template-columns: 220px 1fr; min-height: 100dvh; }
   .app-shell__rail { border-right: 1px solid var(--color-hairline); }
   .app-shell__main { padding-inline: var(--page-gutter); max-width: 1200px; }
   ```
   Add the class rules to `components.css`, not inline.
3. **Reposition the nav.** Move `{% block nav %}` into `.app-shell__rail`. The block content stays empty here; T-062 rewrites `_nav.html` to populate it.
4. **Keep `{% block main %}`.** Place it inside `.app-shell__main`. Downstream templates (`home/index.html`, `accounts/_card.html`, every page) continue to extend `base.html` and override `main` with no changes.
5. **Add the slots.** After the main column, before the closing `</body>`:
   ```jinja
   <div id="drawer-root" aria-live="polite"></div>
   <div id="modal-root"></div>
   {% block fab %}{% include "partials/_fab.html" ignore missing %}{% endblock %}
   ```
   `ignore missing` lets this ship before T-069 lands.
6. **Preserve `{% block scripts %}`** at its current spot (end of body). T-068 later appends `palette.js` + `shortcuts.js` includes there.
7. **Smoke test every route.** `just dev`, then `curl -sI http://127.0.0.1:8000/` + hit each existing page. All must return 200 and render the nav (even if the rail content is still the old horizontal list from T-062's pre-rewrite state).

## Validation / acceptance

- `GET /` returns `200` and renders the left rail column, main column, `#drawer-root`, `#modal-root` in DOM order.
- `grep -nE 'id="drawer-root"|id="modal-root"' src/budget_planner/web/templates/base.html` returns both matches.
- `grep -nE "{% block (title|head_extra|nav|main|scripts) %}" src/budget_planner/web/templates/base.html` returns five matches — no block name was renamed or deleted.
- Every downstream template (`home/index.html`, `accounts/index.html`, `transactions/index.html`, `planned/index.html`, `recurring/index.html`, `categories/index.html`, `budget/index.html`, `forecast/index.html`, `analytics/index.html`) continues to render without template-not-found errors.
- No new palette values, radii, or spacing scales introduced; everything references `--color-*`, `--space-*`, `--page-gutter` from T-053 tokens.
- Integration test: new `tests/integration/web/test_shell.py::test_shell_slots_present` asserts `#drawer-root` and `#modal-root` are in the HTML of `GET /`.

## Risks & gotchas

- **Silent block rename** will break downstream templates. Keep exact names.
- **`#drawer-root` empty by default** must not create a visible gap. The element has no padding/margin; CSS treats it as a `display: contents`-like no-op until HTMX swaps content in. Verify in devtools.
- **Fluid gutter + max-width.** On a 4K monitor the main column should center with symmetric gutters. If not, the grid is wrong — the shell should center `.app-shell__main` via `margin-inline: auto` within its grid cell.
- **Tailwind CDN specificity.** The shell classes live in `components.css` (loaded after Tailwind) so Tailwind utilities on child templates still win where they should.
- **No scroll leak.** `min-height: 100dvh` on the grid, not `height: 100vh`, to avoid trapping the body scroll on short pages.

## Handoff notes

- Hand-off to T-062 (nav rewrite): the `{% block nav %}` is empty on the rail; T-062 fills it with the 4-item left-rail markup.
- Hand-off to T-067 (settings drawer): drawer HTMX swaps into `#drawer-root`. The slot is `aria-live="polite"` so screen readers announce opens.
- Hand-off to T-068 (command palette): `partials/_palette.html` mounts into a sibling root (likely `#modal-root` or a dedicated `#palette-root` — T-068 decides and documents).
- Hand-off to T-069 (FAB): `partials/_fab.html` renders inside the `{% block fab %}`. Pages that want to hide the FAB (e.g. a focused form) override the block to empty.
- Commit shape: `feat(T-061): base shell refactor — left rail, drawer-root, modal-root, FAB slot`.
