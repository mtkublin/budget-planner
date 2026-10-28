# Phase 2 — Component primitives

> 13 Jinja macros under `_partials/components/` + `/dev/components` reference page + stylelint rule asserting no hard-coded colours outside `tokens.css`.
>
> Parallel-safe within phase (except T-R23 + T-R24 which join at the end).

Entry: Phase 1 exit criteria met.

Exit: every macro in ADR-0053 §1 ships; `/dev/components` renders them all; visual-regression baseline covers D/T/M; stylelint rule in CI.

Tasks: T-R11..T-R24.

- T-R11 amount
- T-R12 category_pill
- T-R13 direction_badge
- T-R14 pace_tag + overdue_chip
- T-R15 button
- T-R16 segmented
- T-R17 filter_chip_row
- T-R18 table_row
- T-R19 heatmap_cell
- T-R20 progress_bar
- T-R21 top_bar_add
- T-R22 period_header
- T-R23 `/dev/components` population
- T-R24 primitive VR baselines

ADR references: 0053, 0048, 0028, 0052.
