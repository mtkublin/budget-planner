# Rising Dough v2 — Redesign Work Plan

> v2 scope: full UI/UX redesign of the v1 app, codenamed **Rising Dough**. v1's functional surface and data model are preserved; the templates, CSS, interactions, and nav shape are rebuilt against the design handoff at `docs/application_redesign_handoff/`.
>
> **Non-goals**: dark mode, command palette, CSV import, any schema change, remote deployment (that is v3).

---

## Contents

- [`implementation_plan.md`](implementation_plan.md) — phased delivery with acceptance gates.
- [`tasks.md`](tasks.md) — flat task index (T-R01…T-R60), referenced from the phase docs.
- [`phase-1-foundations/`](phase-1-foundations/) — Tailwind v4, tokens, fonts, product rename, base shell.
- [`phase-2-primitives/`](phase-2-primitives/) — Jinja component macros + `/dev/components` reference page.
- [`phase-3-screens/`](phase-3-screens/) — rebuild Today, Ledger, Plan, Accounts, Settings.
- [`phase-4-backend/`](phase-4-backend/) — six new / amended endpoints implied by the design.
- [`phase-5-charts/`](phase-5-charts/) — Plotly removal, server-rendered SVG rendering, data-table fallbacks.
- [`phase-6-responsive/`](phase-6-responsive/) — mobile tab bar, bottom sheet, narrow-table scroll wrappers.
- [`phase-7-cleanup/`](phase-7-cleanup/) — retire legacy routes (one release after v2 ships), remove dead CSS, drop the FAB.

---

## At a glance

| Phase | What | Gate |
|---|---|---|
| 1 — Foundations | Tailwind v4 upgrade, token wiring, self-hosted fonts, product rename, base shell + nav skeleton | `/dev/components` renders; visual-regression baseline fresh; `just ci` green |
| 2 — Primitives | 13 Jinja component macros, `/dev/components` page, stylelint rules | Every macro covered by Playwright snapshot at D/T/M; baselines in |
| 3 — Screens | Rebuild Today, Ledger (3 tabs), Plan (4 tabs), Accounts, Settings | Every screen passes `frontend-visual-audit` at 1440/1024/375 with zero overflow/console/duplicate-id findings |
| 4 — Backend | `/today/afford`, `/recurring/formula/preview`, `/accounts/last-checked`, `/plan/analytics`, category archive/restore, batch promote-due | Each endpoint ≥ 90% coverage; service-layer pure; HX-Trigger wiring verified |
| 5 — Charts | Plotly removal; `charts.py` + two chart templates (line+area, grouped bars, horizontal bars); data-table fallbacks | Bundle drops ≥ 1.5 MB; `/plan/forecast` and `/plan/analytics` pixel-matched to mocks |
| 6 — Responsive | Mobile tab bar + Add bottom sheet; sticky-first-column scroll wrappers; year grid cards | 375 px viewports render every screen without `horizontalScroll`; tap targets ≥ 44 px |
| 7 — Cleanup | Retire v1 routes + FAB code, prune dead CSS, delete `#drawer-root` | `grep -r 'FloatingActionButton\|drawer-root\|/categories ' src/` returns empty; v1 302 shims removed |

---

## Dependencies

- **Phase 1 → everything.** Nothing renders correctly until tokens + Tailwind v4 + fonts land.
- **Phase 2 → Phase 3.** Screens compose from primitives; building a screen before its primitives duplicates work.
- **Phase 4 ∥ Phase 3.** Backend endpoints can be built in parallel; each is independent and bounded.
- **Phase 5 depends on Phase 2** (chart primitives are leaves of the component system).
- **Phase 6 depends on Phase 3** (responsive tuning per screen is more efficient than a global pass).
- **Phase 7 depends on Phases 3–6.** Legacy removal only after new paths prove green in production use.

---

## Change policy

Per repo `CLAUDE.md`:

- Any ADR-0050..0056 scope change requires an amendment to the relevant ADR before code lands.
- Every merged task line in `tasks.md` carries a `✅`; the commit references the task id (`feat(T-Rxx): ...`).
- Every frontend-touching task invokes `frontend-visual-audit` at D/T/M viewports and references findings in the PR / commit body.
- The `docs/application_redesign_handoff/` folder is the design source of truth; `docs/plans/v2/` is the engineering source of truth.
- `docs/CHANGELOG.md` gains a dated line per merged task.
- Visual-regression baselines regenerate only via `just test-visual-update`; drift otherwise fails CI (ADR-0027).
