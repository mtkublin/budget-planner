# T-R02 — Design tokens pipeline

- **Phase**: 1 — Foundations
- **Sequential**: yes; blocks T-R04..T-R10 and all primitives.
- **Depends on**: T-R01.
- **References**: ADR-0050 §2, ADR-0052 §2.

## Context

The Rising Dough palette, typography, radius, shadow, and motion tokens live in `docs/application_redesign_handoff/tokens.css`. For runtime consumption they need to live inside `src/budget_planner/web/static/` and be exposed to Tailwind utilities via `@theme`. Dynamic colours (category hue override, heatmap intensity) continue to use inline `style` + CSS variables, so the CSS variable form is non-negotiable.

## Deliverables

- `src/budget_planner/web/static/tokens.css` — copied byte-for-byte from `docs/application_redesign_handoff/tokens.css`.
- `src/budget_planner/web/static/css/app.css` `@theme` block populated per ADR-0052 §1 (every token aliased to a Tailwind theme variable).
- New pre-commit hook: `token-diff` that asserts `tokens.css` matches the handoff file. One-liner `diff -q` wrapped in a hook definition.
- `README.md` note on where tokens live and how to update them.

## Acceptance criteria

- `diff docs/application_redesign_handoff/tokens.css src/budget_planner/web/static/tokens.css` is empty.
- `grep -r "oklch" src/budget_planner/web/static/ | grep -v tokens.css` returns zero hits (stylelint rule T-R08 later asserts this in CI).
- `just css` emits a `static/tailwind.css` that includes `--color-paper` as a theme-generated utility (grep for `.bg-paper` in output).
- `token-diff` pre-commit hook fails if a token value diverges between the two files.

## Validation hook

```sh
diff -q docs/application_redesign_handoff/tokens.css src/budget_planner/web/static/tokens.css && \
  just css && \
  grep -q "bg-paper\|--color-paper" src/budget_planner/web/static/tailwind.css
```

## Risks & gotchas

- Tailwind v4 scans the `@theme` block for variable names; mis-naming breaks utility generation silently. Spot-check `.bg-accent-soft` and `.text-expense` in a dev template after the hook runs.
- The handoff tokens use OKLCH hue 85 for warm neutrals; Chrome 111+ renders OKLCH natively. Safari < 15.4 falls back; the project's browser matrix (ADR-0027) covers modern browsers only. Document this.
- Do not inline the token values into `app.css` even for "convenience" — a future dark-mode ADR would then have to touch two files. Keep tokens.css as the single source.

## Handoff notes

- T-R03 adds `fonts.css` (same directory); keep the import order `tailwindcss → tokens.css → fonts.css → @theme`.
- T-R19 (`heatmap_cell`) will consume `--line` + `--expense-soft` directly from `tokens.css` via inline style attributes — do not add Tailwind utilities for those cells.
