# Phase 6 — UX Redesign (IA consolidation + appeal pass)

> Status: pending. Scope: web layer only; no new domain behaviour; v1 only.

## Overview

Phase 6 collapses the 9-tab horizontal nav into a **4-tab left rail + Settings drawer** and lifts the surfaces from "default-looking admin UI" to a composition that answers jobs instead of listing entities. The design direction (editorial / Swiss) from T-053 is preserved; this phase changes composition and interaction, not tokens.

Primary destinations:

| New top-level | Collapses | URL |
|---|---|---|
| Overview | Home + Forecast summary + Analytics headline | `/` |
| Ledger   | Transactions + Planned + Recurring         | `/ledger` |
| Accounts | Accounts + Snapshots + Reconcile           | `/accounts` |
| Budget   | Budget rules + monthly summary + breakdown | `/budget` |

Secondary: **Settings drawer** (Categories, FX, Preferences) opened by gear icon or `g s`.

Decision: see [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md).

## Task table

| ID | Task | Dep |
|---|---|---|
| T-060 | ADR-0023 — UX redesign: 9→4 IA consolidation + command-palette interaction model | — |
| T-061 | Base shell refactor: left rail + `#drawer-root` + `#modal-root` + FAB slot in `base.html`; preserve `base.html` block names | T-060 |
| T-062 | Nav partial rewrite (`partials/_nav.html`), active-page highlight, keyboard shortcuts attribute data | T-061 |
| T-063 | Overview composition: three-panel layout (Accounts list + sum, Budget-left headline, Upcoming planned with overdue muting) + new fragment `/overview/upcoming?window=…` + reuse existing account-balance and budget-summary services | T-061, T-062 |
| T-064 | Ledger unification: `/ledger` router + segmented control + shared filter form + `/ledger/table` dispatch fragment + alias old fragment routes | T-061, T-062 |
| T-065 | Accounts polish: per-card sparkline + inline reconcile + snapshot disclosure | T-061 |
| T-066 | Budget consolidation: `/budget` page with three sections (summary, rules, breakdown) + reuse analytics figures | T-061 |
| T-067 | Settings drawer: `/settings?tab=…` fragment, category CRUD lifted into drawer, FX read-only panel, Preferences read-only panel | T-061 |
| T-068 | Command palette + keyboard shortcuts: `partials/_palette.html` + `static/js/palette.js` (~60 lines vanilla) + `?` cheatsheet partial | T-062 |
| T-069 | Quick-add FAB + slide-over integration with Ledger context awareness | T-061, T-064 |
| T-070 | Redirect map: old URLs 302 → new URLs; `/transactions`, `/planned`, `/recurring`, `/categories`, `/analytics` return redirects; integration tests cover each | T-064, T-066, T-067 |
| T-071 | Accessibility re-audit against new surfaces: focus trap in drawer + palette, Esc behaviour, aria-current on nav, reduced-motion branches, contrast on new tiles | T-063…T-069 |
| T-072 | README + CHANGELOG update: screenshot, new keyboard map, migration note; link ADR-0023 | T-071 |

## Dependency map

- **T-060** → unblocks everything.
- **T-061** → precondition for every surface task (new shell slots).
- **T-062** → precondition for T-063, T-064, T-068.
- **Parallel-safe set once T-061/T-062 are in**: `{T-063, T-064, T-065, T-066, T-067}`.
- **T-068** pairs with T-062 (nav shortcut attrs feed the palette).
- **T-069** pairs with T-064 (FAB context dispatch depends on ledger `view` param).
- **T-070** waits on T-064, T-066, T-067 (needs the new homes to exist).
- **T-071** runs last against the new surfaces (T-063…T-069).
- **T-072** closes the phase after T-071.

Est. size: each task ≤ 1 day; whole phase ~2 weeks sequential, ~1 week fan-out.

## Exit criteria (verification checklist)

Local, end-to-end, no new tooling:

- [ ] `just dev` — click through: Overview loads with Accounts panel + Budget-left panel + Upcoming planned list without reload. Ledger segmented control cycles between actual / planned / recurring with HTMX swaps and no full-page reload. Accounts cards render sparklines. Budget page shows summary + rules + breakdown without duplicate scrollbars. Settings drawer opens from the gear icon and from `g s`.
- [ ] Keyboard-only walk: `g o / g l / g a / g b / g s`, `n` on each tab, `⌘K` opens palette, `?` opens cheatsheet, `⎋` closes drawer / palette / modal (topmost-overlay rule).
- [ ] `just test` — new integration tests cover: `/ledger?view=…` returns correct subset, old URLs 302 to new homes, drawer fragment returns valid HTML per tab, command-palette partial renders without JS context.
- [ ] `just lint` + `just typecheck` + `just ci` all green.
- [ ] Lighthouse on `/`, `/ledger`, `/budget`: LCP < 2.5 s, INP < 200 ms, CLS < 0.1 (per `rules/web/performance.md`).
- [ ] Axe (manual or Playwright): no regressions vs. T-052 baseline on the four new primary pages + the drawer + the palette.
- [ ] `grep` guard still passes (no hard-coded palette values outside `tokens.css`).
- [ ] `docs/CHANGELOG.md` entry for the phase landing day.
- [ ] `README.md` updated with keyboard map + migration note.

## See also

- Decision: [`docs/adr/0023-ux-redesign-information-architecture.md`](../../../adr/0023-ux-redesign-information-architecture.md)
- Mockups: [`./mockups.md`](./mockups.md)
- Prior phase: [`../phase-5/`](../phase-5/)
