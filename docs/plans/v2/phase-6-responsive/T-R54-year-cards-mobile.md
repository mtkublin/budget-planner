# T-R54 — Year grid → category cards (mobile)

- **Phase**: 6 — Responsive
- **Sequential**: after T-R31.
- **Depends on**: T-R31 (Plan · Year).
- **References**: ADR-0055 §5, handoff mobile Plan · Year lower region (screen 1q).

## Context

At ≤ 640 px the 12-column heatmap grid is unreadable. Replace with per-category horizontal strip cards: one row per category showing a 12-month strip (tap target per cell = full column height). Tap opens the same cell-edit popover from T-R31.

## Deliverables

- `templates/plan/_year_cards.html` with:
  - One `<article class="year-card">` per budgeted category.
  - Card header: category pill + total for the year.
  - Horizontal strip of 12 cells (via `heatmap_cell` macro); each cell = ~`calc((100vw - 2 * var(--space-page-x)) / 12)` wide; min tap target 32 × 44 px.
  - Overflow: unbudgeted categories collapse under a "Spend without budget" expandable section.
- Switch logic:
  - `@media (width <= 640px)` renders `_year_cards.html`; wider viewports render the Phase 3 `_year.html` table.
  - Both templates consume the same `services.budget.yearly_grid(conn, year)` return.
- Cell tap opens `GET /plan/year/cell/{category_id}/{year}/{month}/edit` popover (same endpoint as T-R31).
- Visual-regression baseline at 375 px matches handoff.

## Acceptance criteria

- At 375 px every budgeted category renders a 12-cell strip; horizontal scroll inside the card only if 12 cells don't fit (shouldn't on standard phones).
- Tap on any cell opens the popover centred on the viewport (not anchored — tiny screen means popover takes 90 vw).
- `frontend-visual-audit` at 375 px returns zero `horizontalScroll` on the page level.
- Keyboard: tab reaches each cell; Enter opens the popover; Esc closes.

## Validation hook

```sh
just test-visual --filter year-cards-mobile && \
  invoke frontend-visual-audit at 375 against "/plan?tab=year"
```

## Risks & gotchas

- The popover from T-R31 was designed around CSS Anchor Positioning on a wide viewport; on mobile it must centre on the viewport, not anchor to the tiny cell. Add a `--popover-anchor: viewport` CSS custom property that mobile overrides.
- Totals in the card header must match the year-table totals exactly (same service, same arithmetic).
- Reduced motion disables the card expand/collapse transition.

## Handoff notes

- T-R56 regenerates mobile visual-regression baselines; include this card view in the sweep.
