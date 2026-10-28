# T-R63 — View Transitions wiring

- **Phase**: 1 — Foundations
- **Parallel-safe**: after T-R04.
- **Depends on**: T-R04.
- **References**: ADR-0056 §7, ADR-0050 §5.

## Context

Browsers that support `document.startViewTransition` (Chrome 111+, Safari 18+) can morph DOM swaps as a single animation. HTMX exposes this via `hx-swap="... transition:true"`. Tab changes within Plan + promote-in-place row collapse read as one motion when enabled. Reduced-motion disables.

## Deliverables

- `src/budget_planner/web/static/js/view-transitions.js` — feature-detects `document.startViewTransition` and sets `htmx.config.globalViewTransitions = true` when available and when `matchMedia('(prefers-reduced-motion: reduce)')` is false.
- Loaded via `<script src="/static/js/view-transitions.js" defer>` in `base.html` just before HTMX.
- CSS `view-transition-name: *` tokens on key elements (hero number, promoted row, segmented control thumb) in `static/css/components/transitions.css`.
- Unit test fixture asserts graceful degradation on unsupported browsers (no feature-detection error).

## Acceptance criteria

- With Chrome 125: switching Plan tabs animates the content region; promoting a row animates row collapse + hero-number update.
- With `prefers-reduced-motion: reduce`: no view transitions fire; HTMX swaps instantly.
- With Firefox / Safari pre-18: no error, no transition.
- `grep "startViewTransition\|globalViewTransitions" src/budget_planner/web/static/` returns the single `view-transitions.js` hit.

## Validation hook

```sh
# Playwright test under tests/e2e/test_view_transitions.py
pytest tests/e2e/test_view_transitions.py
```

## Risks & gotchas

- `view-transition-name` must be unique per element on the page at the time the transition fires. Duplicates cause the browser to drop the transition silently. Reserve names: `hero-number`, `plan-tab-content`, `promote-row-{id}`.
- Reduced-motion check must re-evaluate on media-query change — register a listener.
- Do not enable globally for every HTMX swap; some fragment swaps (e.g. filter chips) look worse animated. Opt in per hx target with `hx-swap-oob="... transition:true"` where appropriate.

## Handoff notes

- Phase 3 screens that want transitions add `view-transition-name` CSS tokens to the elements that should morph.
- Phase 7 cleanup checks that no obsolete `view-transition-name` references remain after screen churn.
