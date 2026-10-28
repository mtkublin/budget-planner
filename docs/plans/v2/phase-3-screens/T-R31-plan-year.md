# T-R31 — Plan · Year

- **Phase**: 3 — Screens
- **Sequential**: after T-R19, T-R29.
- **Depends on**: T-R19 (heatmap_cell), T-R29 (Plan shell).
- **References**: handoff §Plan · Year, ADR-0014 (three-tier resolution), ADR-0031 (yearly table + inline edit), ADR-0056 §2 (cell edit popover).

## Context

12-month heatmap. Rows = live expense categories. Columns = Jan..Dec of the selected year. Cell colour intensity scales with amount via `heatmap_cell` macro (sqrt, capped at 1,600). Tier markers encode which of the three tiers (default · recurring · one-off) resolved the budget. Click a cell → popover with amount input + One-off / Every-year radio + Save / Reset to default.

## Deliverables

- `templates/plan/_year.html`:
  - Year switch (`← 2026 →`) via HTMX fragment `GET /plan/year?year=…`.
  - Sticky-first-column scroll wrapper (`.table-scroll`, T-R53 pattern applies but Phase 6 does the mobile card variant via T-R54).
  - 12-month `<table>`; row totals + column totals + grand total in `<tfoot>`.
  - Each cell renders via `heatmap_cell` macro with tier marker.
- Cell edit popover:
  - `GET /plan/year/cell/{category_id}/{year}/{month}/edit` returns the popover fragment anchored by CSS Anchor Positioning (Chrome 125+) or fallback via Alpine data component for Safari < 17.4.
  - Form fields: amount, radio `One-off {month YYYY} / Every year · {month}`, Save, Reset-to-default button.
  - Save POSTs to existing `POST /budget/one-off/{id}/{year}/{month}` or `POST /budget/recurring/{id}/{month}` depending on radio value.
  - Reset-to-default DELETEs the matching override row and reloads the cell fragment.
  - Keyboard: cell receives arrow-key navigation; Enter opens popover; Esc closes; Save on `↵` inside the amount field.
- Reuse `services.budget.yearly_grid(conn, year)` from Phase 11 unchanged.
- Integration tests cover: year switch, cell click → popover render, Save with one-off tier, Save with recurring tier, Reset-to-default, keyboard navigation across cells, over-cap colour clamp.

## Acceptance criteria

- Visual-regression baselines match handoff `desktop-1h-plan-year.png` at D/T.
- Mobile (375 px) renders per-category cards per T-R54 (not this task's job but tests cross-check).
- Cell tier marker correctness: bold + outline on one-off; italic + diagonal hatch on recurring; plain on default; em-dash on unset.
- Keyboard: arrow keys move focus between cells; current cell has visible focus ring (ADR-0050 §4).
- `frontend-visual-audit` returns zero `horizontalScroll` at desktop; sticky first column stays visible on scroll.

## Validation hook

```sh
pytest tests/integration/web/test_plan_year.py && \
  invoke frontend-visual-audit at 1440 1024 against "/plan?tab=year"
```

## Risks & gotchas

- CSS Anchor Positioning is Chrome-only at Phase 3 timing; the Alpine fallback must compute popover position from `getBoundingClientRect` + viewport clamping (keep inside the content region).
- Popover must trap focus; Esc returns focus to the originating cell.
- Reset-to-default on a cell that only has a default raises inline info "no override to reset" without a 500.
- Column total in `<tfoot>` sums resolved budgets; row total sums resolved budgets across months. Make the computation match ADR-0014 exactly (one-off wins over recurring over default).

## Handoff notes

- T-R54 (mobile cards) consumes the same `yearly_grid` service return; keep the service shape stable.
- Over-cap colour clamp (amount > 1,600 units) renders at maximum chroma; raising the cap requires a new ADR.
