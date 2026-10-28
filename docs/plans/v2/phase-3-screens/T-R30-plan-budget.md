# T-R30 — Plan · Budget

- **Phase**: 3 — Screens
- **Sequential** within Phase 3.
- **Depends on**: T-R29 (Plan shell), Phase 2 primitives.
- **References**: ADR-0051 §5, ADR-0031 (Rules row shape), ADR-0041 (anchor window), handoff §Plan · Budget.

## Context

The Budget tab inside Plan carries the paycheck period hero, a month switch, the Rules table (one row per live expense category with planned / actual / used-bar / remaining / ⋯), and a "categories with spend but no budget" tail. All Rules behaviour already exists in v1 Phase 11 under `/budget`; this task repackages it inside the new Plan shell and the new row shape.

## Deliverables

- Route: `GET /plan?tab=budget` (registered in T-R29) renders Budget as the default tab.
- Templates:
  - `templates/plan/_budget.html` composes the hero, month switch, Rules table, unbudgeted tail.
  - `templates/plan/_budget_hero.html` with left-per-day via `amount`, committed sub-line, `pace_tag`, segmented `progress_bar`, `period_header`.
  - `templates/plan/_budget_rules.html` with `table_row` per category: category pill via `category_pill`, planned input (inline-editable; POST to existing `/budget/defaults/{id}`), actual via `amount`, `progress_bar`, remaining via `amount`, ⋯ Override.
- Reuse existing `services.budget.month_summary` + repository calls — no new service.
- Override slide-over form (`templates/plan/_override_form.html`) rebuilt from the Phase 11 variant to use the new primitives (`button`, inputs, close `×`). Dispatches to `POST /budget/rules/{id}/overrides` (existing).
- Integration tests in `tests/integration/web/test_plan_budget.py` cover: default month render, month switch via `hx-get`, planned inline edit, Override form open + submit (recurring + one-off branches + 422), unbudgeted tail rendering.

## Acceptance criteria

- `/plan?tab=budget` renders without template errors; `curl -o /dev/null -w "%{http_code}\n" ...` is `200`.
- Visual-regression baselines at D/T/M match handoff mockups `desktop-1g-plan-budget.png` and `mobile-1q-plan-budget.png` within tolerance.
- `frontend-visual-audit` on `/plan?tab=budget` returns zero `horizontalScroll`, `overflowingElements`, `duplicateIds`, `consoleErrors`, `requestFailures` at every viewport.
- `g p` lands on `/plan?tab=budget` by default.
- Hero figures match the v1 Overview hero + Budget hero to the minor unit (no drift between pre- and post-redesign numbers).

## Validation hook

```sh
pytest tests/integration/web/test_plan_budget.py && \
  invoke frontend-visual-audit at 1440 1024 375 against "/plan?tab=budget"
```

## Risks & gotchas

- The Rules row's planned column is inline-editable; the HTMX swap must target the row only (not reload the table). Reuse Phase 11 `#budget-rules` + `budget-stale` listeners.
- Over-budget remaining amounts render in `--expense` colour but must also carry the `.remaining--over` class so a screen reader hears "over budget" via `aria-label` (ADR-0050 §6 no-colour-only).
- Unbudgeted tail must NOT appear inside the Rules `<tbody>`; it's a sibling `<section>` so screen readers do not read it as a continuation of the table.

## Handoff notes

- T-R31 (Plan · Year) sits in the same Plan shell; reuse `period_header` and the month/year switch pattern established here.
- `services.budget.yearly_grid` (Phase 11) is consumed by T-R31; do not refactor it in this task.
