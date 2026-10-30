# Phase 3 — Screen rebuild

> Rebuild every v2 screen from Phase 2 primitives. Order is "reading order" per ADR-0051: Today → Ledger → Plan → Accounts → Settings → modals.
>
> Each task runs `frontend-visual-audit` at desktop 1440, tablet 1024, mobile 375. Baselines regenerate per task; drift blocks merge.

Entry: Phase 2 exit criteria met.

Exit: every screen passes the visual-audit sweep; keyboard shortcuts route correctly; new canonical routes resolve; legacy routes 302.

Tasks: T-R25..T-R39 + T-R65..T-R67 + T-R69..T-R70.

- T-R25 Today
- T-R26 Ledger · Actual
- T-R27 Ledger · Planned
- T-R28 Ledger · Recurring
- T-R29 Plan shell + Period header
- T-R30 Plan · Budget
- T-R31 Plan · Year
- T-R32 Plan · Forecast (depends on Phase 5 chart)
- T-R33 Plan · Analytics (depends on Phase 5 chart + Phase 4 bundle)
- T-R34 Accounts
- T-R35 Settings · Categories
- T-R36 Settings · Currency & FX
- T-R37 Settings · Preferences
- T-R38 Add entry modal (Fixed / Formula)
- T-R39 Reconcile slide-over reskin
- T-R65 Create account overlay reskin
- T-R66 Create category overlay reskin
- T-R67 Accounts ⋯ menu
- T-R69 Ledger bulk-select toolbar
- T-R70 "Recently deleted" surface

ADR references: 0051, 0053, 0056, 0038, 0043, 0048, 0023 (prior IA — superseded).

Handoff: `docs/application_redesign_handoff/docs/03-screen-specs.md` is the design source of truth per screen.
