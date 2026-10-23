# Phase 5 — Polish · Plan Index

> Goal of the phase: not embarrassing to show someone. README quick-start works on a clean clone, validation errors render inline, no a11y regressions on main flows, and the UI avoids the generic template look called out by the global `web/design-quality.md` rule.

Phase gate (from `docs/implementation_plan.md`, section "Phase 5 — Polish"):

- README quick-start works end to end on a clean machine.
- Validation errors rendered inline.
- No a11y regressions on main flows.
- UI avoids the generic template look (see global `web/design-quality.md` rule).

Scope guard: Phase 6 features (CSV import, auth, DuckDB, trend-based forecast, rollover budgets, hierarchical categories, deployment) are **out of scope**. See `docs/requirements.md` section 3.8.

Tasks (all `[P]` — can be worked in any order once Phase 4 is green):

| # | File | Purpose |
|---|------|---------|
| T-050 | [T-050-readme.md](T-050-readme.md) | Top-level `README.md`: prereqs, quick start, docs map, commands cheat-sheet, troubleshooting. |
| T-051 | [T-051-error-handling-and-flash.md](T-051-error-handling-and-flash.md) | Centralised exception handlers, inline validation errors via HTMX partials, flash message partial, consistent 4xx/5xx template surface, structured server-side logging. |
| T-052 | [T-052-accessibility-pass.md](T-052-accessibility-pass.md) | Semantic landmarks, label-for coverage, focus-visible styles, keyboard navigation + modal focus trap check, `aria-live` for HTMX swaps, axe-core / pa11y automation on main routes. |
| T-053 | [T-053-visual-polish.md](T-053-visual-polish.md) | CSS custom-property token layer (palette / type scale / spacing / radius / elevation) layered on Tailwind CDN; apply tokens to nav, dashboard cards, forecast chart surround, forms. Direction: **editorial / Swiss** (see T-053). |

Order of execution: parallel-safe. Recommended landing order for an agent working alone is T-051 → T-053 → T-052 → T-050 so that accessibility and README cover the final shape of the UI. T-050 must be the last to land because it documents the finished state.

## Binding standards

- Global `rules/web/design-quality.md` is the binding anti-template standard for T-053. Any surface shipped in Phase 5 must demonstrate at least four of the "required qualities" listed there.
- Global `rules/web/testing.md` (section "Accessibility") is the binding a11y bar for T-052.
- Global `rules/web/performance.md` is the binding performance bar — do not regress CWV targets while polishing.

## Definition of Done (v1)

Copied verbatim from `docs/implementation_plan.md` section "Definition of Done (v1)" with a per-item status column. All items pending at the start of Phase 5.

| # | Criterion | Status |
|---|-----------|--------|
| 1 | All functional requirements in `docs/requirements.md` section 2 reachable via the UI. | pending |
| 2 | `just ci` green on `main`. | pending |
| 3 | Coverage ≥ 90%. | pending |
| 4 | README up to date; `just dev` works on a clean clone. | pending |
| 5 | All ADRs committed. | pending |
| 6 | No TODO/FIXME in `src/` without an attached issue reference. | pending |

Phase 5 exit also requires:

| # | Criterion | Status |
|---|-----------|--------|
| 7 | README quick-start works end to end on a clean machine. (T-050) | pending |
| 8 | Validation errors rendered inline without full-page reload. (T-051) | pending |
| 9 | No a11y regressions on main flows; automated axe/pa11y pass with zero WCAG-A violations on the eight primary routes. (T-052) | pending |
| 10 | UI avoids the generic template look; design tokens live in `src/budget_planner/web/static/css/tokens.css` and are referenced consistently. (T-053) | pending |

## Downstream artifact

End of Phase 5 is the v1 release artifact. Nothing in Phase 6 is to be shipped as part of this phase. The CHANGELOG entry for the final task should be dated and tagged `v1.0.0` by the committing agent.
