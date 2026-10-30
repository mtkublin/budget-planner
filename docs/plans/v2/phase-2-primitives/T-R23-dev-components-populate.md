# T-R23 — `/dev/components` population

- **Phase**: 2 — Primitives
- **Sequential**: after T-R11..T-R22, T-R61, T-R62.
- **Depends on**: all primitives.
- **References**: ADR-0053 §2.

## Context

The stub route from T-R07 renders empty placeholders. This task fills every section with representative inputs so Phase 3 screen rebuilds have a visual reference and so visual-regression (T-R24) has a stable snapshot source.

## Deliverables

- `src/budget_planner/web/templates/dev/components.html` with one `<section id="{macro-name}">` per primitive, each rendering 4–10 variants.
- Side nav (sticky) jumps between sections.
- Variants for each macro:
  - `amount`: expense, income, transit, adjust, formula, FX hint, JPY (zero decimals), large, zero, over-budget.
  - `category_pill`: direction defaults, per-category hue overrides (5 swatches).
  - `direction_badge`: four directions with/without label.
  - `pace_tag`: on_track, tight, overdue.
  - `overdue_chip`: 1 day, 7 days, 30 days.
  - `button`: primary / default / ghost × base / small; with and without `<kbd>` shortcut.
  - `segmented`: 2-way, 3-way, 4-way; active in each slot.
  - `filter_chip_row`: all filters active, one active, none active.
  - `table_row`: with and without actions; overdue variant.
  - `heatmap_cell`: tier default, recurring, one-off, unset; low / mid / high values.
  - `progress_bar`: 25 %, 50 %, 95 %, over-budget; with and without committed segment.
  - `top_bar_add`: desktop variant.
  - `period_header`: start-of-period, mid-period, end-of-period, overdue state.
  - `toast`: info, success, destructive; with and without Undo.
  - `cheatsheet`: full modal render.
- Each section carries `data-component="{macro-name}"` for Playwright assertions.
- No real database access; variants are hard-coded Jinja fixtures.

## Acceptance criteria

- `/dev/components` returns 200 in local; returns 404 in production (env guard).
- Every section renders without template errors.
- Playwright can select a specific primitive by its `[data-component]` attribute (T-R24 uses this).
- Rendering the page writes no audit log entries + no DB queries beyond base context.

## Validation hook

```sh
curl -sS http://localhost:8000/dev/components | grep -c 'data-component="' | awk '{ exit $1 < 15 }'
```

## Risks & gotchas

- Variant fixtures must stay in Jinja (one file) — do not spread across many smaller files. The whole point of this page is single-glance review.
- Avoid random data; variants need to be deterministic for visual regression.

## Handoff notes

- T-R24 captures baselines from this page; downstream primitive edits must re-run baselines.
- Phase 3 screen tasks reference `/dev/components#{macro}` in their PR body to prove they used the macro, not an inline reinvention.
