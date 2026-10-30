# Rising Dough v2 — Implementation Plan

> Companion to `tasks.md`. Describes order, phasing, acceptance criteria, and handoff shape so subsequent agents can pick up work without re-deriving context.

---

## Guiding Principles

1. **Docs first.** ADRs 0050..0056 govern v2. Any surprise during implementation that would deviate from those ADRs stops the task until the ADR is amended.
2. **The handoff is the source of truth for design.** `docs/application_redesign_handoff/` is authoritative; `docs/plans/v2/` is authoritative for engineering choices. When they disagree, raise it as an open item and update the ADR.
3. **Primitives before screens.** Build the 13 Jinja macros against `/dev/components` first. Rebuild screens by composition.
4. **No schema change.** v2 is a re-skin + IA consolidation + backend additions that reuse existing tables. Every attempt to introduce a migration must be ADR-gated.
5. **Visual regression is a signal, not ceremony.** Every screen asserts against baselines at desktop (1440) + tablet (1024) + mobile (375). Baselines regenerate via `just test-visual-update` and are reviewed in PR.
6. **Legacy routes survive one release.** 302 shims keep bookmarks working; Phase 7 removes them.

---

## Architecture overview (v2)

```
                     Rising Dough (v1 functional surface preserved)
                                  │
┌─────────────────────────────────▼──────────────────────────────┐
│  Templates (Jinja)                                              │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  _partials/components/                                 │      │
│  │    amount · pill · badge · pace_tag · overdue_chip     │      │
│  │    button · segmented · filter_chips · table_row       │      │
│  │    heatmap_cell · progress_bar · top_bar_add · period  │      │
│  └───────────────────────────────────────────────────────┘      │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  Screens                                                │      │
│  │    today/*  ledger/*  plan/{budget,year,forecast,...}  │      │
│  │    accounts/*  settings/{categories,fx,prefs}          │      │
│  └───────────────────────────────────────────────────────┘      │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────┐
│  Routers (FastAPI)                                              │
│  routers.today  routers.ledger  routers.plan  routers.accounts │
│  routers.settings  routers.recurring  routers.transactions …   │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────┐
│  Services (pure functions)                                      │
│  services.today  services.budget  services.forecast             │
│  services.analytics  services.accounts  services.upcoming …    │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────┐
│  Repositories + SQL (unchanged tables)                          │
└────────────────────────────────────────────────────────────────┘
```

The only new leaves: `charts.py` (SVG geometry), six new endpoints (ADR-0056 §6), six new service helpers (`services.today.afford`, `services.recurring.formula.preview`, `services.accounts.last_checked`, `services.analytics.bundle`, `services.categories.archive`, `services.{recurring,planned}.batch_promote_due`).

---

## Phased delivery

### Phase 0 — Open decisions (T-R71..T-R73)

Goal: resolve the three outstanding handoff `docs/07-open-items.md` decisions as ADR amendments before any Phase 1 work lands. Each decision gates at least one Phase 3 screen.

Entry: v1 CI green; ADRs 0050..0056 Accepted.

Exit:
- T-R71 Accepted ADR on archived-categories-on-rules behaviour.
- T-R72 Accepted ADR (or explicit note in ADR-0051) on UI language (English chrome, user category names).
- T-R73 Accepted amendment on the pace-tag rule.

### Phase 1 — Foundations (T-R01..T-R10, T-R63, T-R64)

Goal: tokens, fonts, Tailwind v4, product rename, base shell with the new nav skeleton. The app still renders v1 screens afterwards — only shell + brand changed.

Entry: Phase 0 exit criteria met.

Exit criteria:
- `src/budget_planner/web/static/tokens.css` matches `docs/application_redesign_handoff/tokens.css` byte-for-byte; pre-commit diff hook asserts.
- Tailwind v4 upgrade complete; `just css` produces `static/tailwind.css` without warnings; `tailwind-check` hook passes.
- Three variable `woff2` files served from `/static/fonts/`; critical weight preloaded; `fonts.css` imports before `app.css`.
- Wordmark reads "Rising Dough" on every page; package names unchanged (`budget_planner`); `grep -r "Budget Planner" src/budget_planner/web/templates` returns only CHANGELOG-style historical refs.
- Nav skeleton renders Today · Ledger · Plan · Accounts · Settings at desktop; routes still 302 to v1 handlers until Phase 3.
- Keyboard shortcut map (`static/js/shortcuts.js`) handles every ADR-0051 shortcut; input-guards prevent capture inside form controls.
- View Transitions feature-detected in `base.html`; `prefers-reduced-motion` disables.
- `/dev/components` renders empty placeholders (one per planned macro) so Phase 2 has a target.
- `just ci` green; 90%+ coverage; `frontend-visual-audit` baseline captured at D/T/M for a canary page (`/dev/components`).

### Phase 2 — Component primitives (T-R11..T-R24, T-R61, T-R62)

Goal: 15 Jinja macros (13 ADR-0053 + toast + cheatsheet) + `/dev/components` reference page + stylelint rules asserting no hard-coded colours outside `tokens.css`.

Entry: Phase 1 exit criteria met.

Exit criteria:
- Each macro in ADR-0053 §1 exists under `_partials/components/` with its documented signature.
- `/dev/components` renders every macro with representative inputs (OK, overdue, formula, over-budget, muted).
- Playwright visual-regression baseline covers `/dev/components` at D/T/M; CI fails on drift.
- Stylelint custom rule rejects hard-coded `oklch`/`rgb`/`hsl` outside `tokens.css` and `fonts.css`.
- Jinja macros have unit coverage via Jinja fixtures (parse + rendered output assertions).

### Phase 3 — Screen rebuild (T-R25..T-R39, T-R65..T-R67, T-R69..T-R70)

Goal: every v2 screen renders from primitives against the design mocks.

Entry: Phase 2 exit criteria met.

Order within phase (ADR-0051 reading order):

1. **Today** (T-R25) — hero + Can-I-afford + Net worth + Upcoming.
2. **Ledger · Actual** (T-R26) — reuses v1 shell with new row shape.
3. **Ledger · Planned** (T-R27).
4. **Ledger · Recurring** (T-R28) — overrides accordion + formula derivation.
5. **Plan shell + Period header** (T-R29) — shared across the four Plan tabs.
6. **Plan · Budget** (T-R30).
7. **Plan · Year** (T-R31) — heatmap + cell edit popover.
8. **Plan · Forecast** (T-R32) — depends on Phase 5 chart.
9. **Plan · Analytics** (T-R33) — depends on Phase 5 chart + Phase 4 bundle endpoint.
10. **Accounts** (T-R34) — sparkline + last-checked column.
11. **Settings · Categories** (T-R35) — colour + archive + income-anchor.
12. **Settings · Currency & FX** (T-R36).
13. **Settings · Preferences** (T-R37).
14. **Add entry modal** (T-R38) — Fixed / Formula paths.
15. **Reconcile slide-over reskin** (T-R39).
16. **Create account overlay reskin** (T-R65).
17. **Create category overlay reskin** (T-R66).
18. **Accounts ⋯ menu** (T-R67).
19. **Ledger bulk-select toolbar** (T-R69).
20. **"Recently deleted" surface** (T-R70).

Exit criteria (per screen):
- Visual-regression baseline matches at D/T/M.
- `frontend-visual-audit` returns zero `horizontalScroll`, `overflowingElements`, `duplicateIds`, `consoleErrors`, `requestFailures`.
- Keyboard shortcuts route correctly; focus ring visible on every interactive element.
- Routes under new canonical path (`/today`, `/plan?tab=…`, …) resolve; v1 paths 302 to the new path.
- Integration tests update to assert new structural selectors (CSS classes + ARIA roles) and `HX-Trigger` wiring.

### Phase 4 — Backend additions (T-R40..T-R46) — parallel-safe with Phase 3

Goal: six new / amended endpoints land as pure, tested service helpers + thin routers.

Exit criteria:
- Each endpoint has ≥ 90% coverage (unit + integration).
- Service helpers are pure functions returning frozen dataclasses.
- `HX-Trigger` events documented in `routers/README.md` HTMX event table (if not already present).
- No new persistence tables; migrations folder unchanged.

### Phase 5 — Charts (T-R47..T-R50, T-R68)

Goal: Plotly removed; SVG rendering drives Forecast + Analytics; data-table fallback on every chart.

Entry: Phase 2 exit criteria met; Phase 4 analytics bundle endpoint usable in dev.

Exit criteria:
- `plotly.js` + wrapper code deleted; `grep -r plotly src/` returns zero hits outside historical ADRs.
- `charts.py` ships three chart-geometry helpers (line+area, grouped bars, horizontal bars) with unit coverage ≥ 95%.
- `/plan/forecast` and `/plan/analytics` render on-brand SVG; data table fallback inside `<details>` on each `<figure>`.
- `role="img" aria-labelledby` on every chart; keyboard users reach the data table via the next tab stop.
- Bundle delta: `static/tailwind.css` + JS footprint drops ≥ 1.5 MB.
- `sparkline()` helper lands in `charts.py`; Accounts table renders inline SVG trend per row (T-R68).

### Phase 6 — Responsive layer (T-R51..T-R56)

Goal: mobile tab bar + Add bottom sheet + sticky-first-column scroll wrappers + Year grid cards.

Entry: Phase 3 exit criteria met (per screen).

Exit criteria:
- At 375 px every v2 route renders with zero `horizontalScroll` (verified by `frontend-visual-audit`).
- Mobile tab bar fixed at bottom; four primary tabs + centre `+ Add`; tap targets ≥ 44 px.
- `+ Add` bottom sheet opens on tap and on `popstate`; dismiss on 2xx (ADR-0030 modal dismissal scope).
- Narrow numeric tables scroll internally; first column sticky; focus-trap unaffected.
- Year grid renders as per-category cards at ≤ 640 px; each cell tap opens the Phase 3 cell-edit popover.

### Phase 7 — Cleanup (T-R57..T-R60)

Goal: retire v1 routes, delete FAB, prune dead CSS, remove `#drawer-root`. Lands one release *after* v2 is cut as green on main.

Entry: v2 has shipped a tagged release; one additional release has passed with no bookmarked-URL complaints.

Exit criteria:
- 302 shims from v1 → v2 routes removed. `grep -r "RedirectResponse.*plan\|budget\|forecast\|categories\|transactions\|planned\|recurring" src/budget_planner/web/routers/` returns zero.
- FAB template partial + CSS + JS deleted. `grep -ir "fab\|floating-action" src/` returns zero.
- `#drawer-root` div removed from `base.html`.
- `static/js/overlay-stack.js` simplified if drawer code is removable.
- Phase 11 settings-drawer tests retired or rewritten against `/settings` page.
- `docs/plans/v2/` closed with a "✅ v2 shipped" line on top of `tasks.md`.

---

## Rollout order and dependencies (compressed)

```
Phase 0  (sequential, blocks everything):
   T-R71 archived-categories ADR · T-R72 UI language ADR · T-R73 pace-tag rule ADR
            │
            ▼
Phase 1  (sequential within, blocks everything):
   T-R01 Tailwind v4 upgrade → T-R02 tokens.css import → T-R03 fonts → T-R04 base shell
   → T-R05 wordmark rename → T-R06 nav skeleton → T-R07 /dev/components stub
   → T-R08 stylelint config → T-R09 visual-regression baseline canary → T-R10 CI green
   plus parallel: T-R63 View Transitions · T-R64 shortcut map
            │
            ▼
Phase 2  (parallel within):
   T-R11..T-R24 — one macro per task + stylelint rule + unit tests
   plus: T-R61 toast · T-R62 cheatsheet
            │
            ├────────── parallel ──────────┐
            ▼                              ▼
Phase 3 screens                    Phase 4 backend
   T-R25..T-R39                       T-R40..T-R46
   plus T-R65 create account         (one per endpoint)
   plus T-R66 create category
   plus T-R67 accounts ⋯ menu
   plus T-R69 bulk toolbar
   plus T-R70 Recently deleted
            │                              │
            └────────── join ──────────────┘
                        │
                        ▼
Phase 5 charts (T-R47..T-R50, T-R68 sparkline)
                        │
                        ▼
Phase 6 responsive (T-R51..T-R56)
                        │
                        ▼
Phase 7 cleanup (T-R57..T-R60) — one release after v2 cut
```

---

## Handoff shape (per task)

Each task file in `phase-N-*/T-Rxx-*.md` MUST declare:

1. **Context** — one paragraph: why this task exists, which ADR drives it, which handoff file to read.
2. **Deliverables** — concrete file paths, macro signatures, test names, visual-regression baseline keys.
3. **Acceptance criteria** — observable signals that make the task "✅".
4. **Dependencies** — explicit `→ T-Rxx` arrows for upstream work.
5. **Validation hook** — the command the next agent (or human) runs to confirm: usually `just ci && just test-visual && invoke frontend-visual-audit at D/T/M on <route>`.

The flat index in `tasks.md` is the quick-reference view; detail lives in the task files.

---

## Guardrails

- **Do not** add a migration in v2. Any ask that requires one triggers an ADR before code lands.
- **Do not** regress v1 functionality. Every service + repository test must continue to pass.
- **Do not** merge a screen task without visual-regression baselines at D/T/M.
- **Do not** touch Plotly code in Phase 3 — Phase 5 owns chart migration.
- **Do** reference the design handoff file name in every screen task so the designer-intent is one hop away.
- **Do** append a dated line to `docs/CHANGELOG.md` after each merged task, prefixed with the task id.
- **Do** mark the task line in `docs/plans/v2/tasks.md` with `✅` on completion.
