# T-R04 — Base shell refactor

- **Phase**: 1 — Foundations
- **Sequential**: yes; blocks T-R05..T-R09.
- **Depends on**: T-R02, T-R03.
- **References**: ADR-0051 §1, ADR-0055 §1, ADR-0050 §1.

## Context

`src/budget_planner/web/templates/base.html` is the shell every page extends. The redesign changes the shell shape fundamentally: hairline rail with Rising Dough wordmark + top-bar `+ Add` on desktop, bottom-tab-bar slot on mobile (filled in Phase 6), retire the drawer slot (deferred until Phase 7).

## Deliverables

- Rewritten `base.html` with:
  - `<header class="rail">` on desktop (≥ 1100 px): wordmark + four primary tabs + top-bar `+ Add` slot.
  - `<nav class="rail__nav">` lists Today · Ledger · Plan · Accounts with Settings pinned to the bottom.
  - `<main>` block kept with the same name so existing templates continue to render.
  - `<footer class="tab-bar">` stub for mobile (empty in Phase 1; T-R51 fills).
  - `#drawer-root` + `#modal-root` + `#toast-root` divs preserved (drawer-root retired in T-R59).
- `static/css/components/rail.css` + `tab-bar.css` + `top-bar.css` with hairline borders, `--paper` background, `--ink` text.
- Legacy Jinja blocks (`title`, `head_extra`, `nav`, `main`, `scripts`) preserved so Phase 3 can rebuild screens incrementally without a flag day.

## Acceptance criteria

- Every v1 screen renders without template errors (`just test-integration` passes).
- `base.html` references Rising Dough tokens via class utilities only; no inline colours.
- Keyboard focus ring visible on every nav link.
- `grep "fab\|floating-action" src/budget_planner/web/templates/base.html` returns zero (FAB moves out of base — Phase 7 deletes it entirely).
- Visual-regression snapshot for a representative v1 page captured as the "pre-redesign baseline"; replaces on T-R09.

## Validation hook

```sh
just test-integration && \
  invoke frontend-visual-audit at desktop 1440 against /today (still 302s to /) and /ledger
```

## Risks & gotchas

- Removing the FAB from `base.html` while Phase 3 is in flight means the Add path falls to `n` keyboard shortcut + top-bar `+ Add` button only on desktop. Mobile users keep the old FAB until T-R51 lands; add a one-line comment in `base.html` noting this transitional state.
- Legacy `/categories` / `/transactions` / etc. still render via their v1 handlers — they just appear inside the new shell. Confirm by hitting each URL.
- Keep `#drawer-root` present during Phase 2–6; T-R59 removes it.

## Handoff notes

- T-R05 (product rename) only touches the wordmark text + title; it can run in parallel.
- T-R06 (nav skeleton + 302 shims) is sequential after this task since it registers canonical routes against the new shell.
