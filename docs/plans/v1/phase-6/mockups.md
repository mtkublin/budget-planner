# Phase 6 — ASCII Mockups

> Copied verbatim from the approved plan. Reference these when composing templates in T-061…T-069.

## Mockups (ASCII)

### Shell

```
┌──────────────┬────────────────────────────────────────────────────────────────────┐
│              │  Overview                                           ⌘K  ⚙         │
│   BUDGET     │                                                                    │
│   PLANNER    │  ─────────────────────────────────────────────────────────────    │
│              │                                                                    │
│   Overview ■ │                                                                    │
│   Ledger     │                 (page content here)                                │
│   Accounts   │                                                                    │
│   Budget     │                                                                    │
│              │                                                                    │
│              │                                                                    │
│   ⚙ Settings │                                                                    │
└──────────────┴─────────────────────────────────────────────────────────────  (+)─┘
   220 px rail         fluid gutter, max content width ~1200 px        FAB bottom-right
```

### Overview

```
Overview

┌──────────────────────────────────────────────────┬──────────────────────────┐
│ FORTUNE                                          │ THIS MONTH               │
│                                                  │                          │
│    147 823,42 PLN                                │  1 580,00 PLN left       │
│                                                  │                          │
│ EUR  18 420,00    USD  2 410,55   CHF  12,00     │  spent 3 420 / 5 000     │
│                                                  │  ████████▓░░░░ 68 %      │
│ ─────────────────────────────────────────────    │  11 days left · on track │
│ Checking · bank · PLN            14 203,55       │                          │
│ Savings  · bank · PLN            48 920,00       │  See forecast →          │
│ Credit   · card · EUR    −1 240,00  (−5 320,00)  │  Budget breakdown →      │
│ Cash     · cash · PLN               420,00       │                          │
│ Revolut  · bank · EUR     3 100,00  (13 290,00)  │                          │
│ ─────────────────────────────────────────────    │                          │
│ All accounts                   147 823,42 PLN    │                          │
└──────────────────────────────────────────────────┴──────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ UPCOMING                              7 days · 30 days · all   [+ Planned] │
│                                                                            │
│  overdue  2026-10-23  expense    −120,00  Transport  Checking  Uber   [›]  │
│  overdue  2026-10-24  expense     −45,00  Fun        Credit    HBO    [›]  │
│  ─────────────────────────────────────────────────────────────────────     │
│  2026-10-25  expense  −2 400,00  Rent      Checking   October rent   [›]  │
│  2026-10-27  income   +6 500,00  Salary    Checking   October        [›]  │
│  2026-10-28  expense   −280,00   Groceries Checking   Biedronka      [›]  │
│  2026-11-01  expense    −45,00   Fun       Credit     Netflix        [›]  │
│  2026-11-05  expense  −1 200,00  Transport Credit     Flights        [›]  │
│                                                                            │
│  overdue rows are muted + italic; today-or-later rows are full emphasis    │
└────────────────────────────────────────────────────────────────────────────┘
```

### Ledger

```
Ledger

┌───────────────────────────────────────────────────────────────────────────┐
│ [ Actual · Planned · Recurring ]           Filter: all   search: ______   │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│ Date       Dir     Amount       Category    Account      Description      │
│ ─────────────────────────────────────────────────────────────────────────  │
│ 2026-10-24 expense     −280,00  Groceries   Checking     Biedronka         │
│ 2026-10-23 income     +6 500,00  Salary     Checking     October           │
│ 2026-10-22 transit      1 000,00 Internal   Checking→Sav Round-up         │
│ 2026-10-22 expense       −45,00  Fun        Credit       Netflix           │
│ 2026-10-21 expense      −120,00  Transport  Checking     Uber ×3           │
│   …                                                                        │
└───────────────────────────────────────────────────────────────────────────┘
                                                              ‹ 1 2 3 … 12 ›
```

Planned view differs by: `Promoted?` column + a `Promote →` button on each row.
Recurring view differs by: `Cadence` + `Next due` columns + accordion-reveal for overrides.

### Accounts

```
Accounts

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ Checking · PLN      │  │ Savings · PLN       │  │ Credit · EUR        │
│   14 203,55          │   48 920,00            │  −   1 240,00          │
│   ╭─╮  ╭──╮         │  │ ╭─╮╭───╮  ╭─╮      │  │   ╭──╮              │
│  ╱   ╲╱    ╲────    │  ╱   ╯    ╲╱   ╲       │  ╱    ╲─╮╭──╮         │
│                     │  │                     │  │                     │
│  120 txns · last 2h │  │  12 txns · last 3d  │  │  28 txns · last 1h  │
│  [Reconcile]        │  │  [Reconcile]        │  │  [Reconcile]        │
│  Show snapshots ⌵   │  │  Show snapshots ⌵   │  │  Show snapshots ⌵   │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

### Command palette

```
          ┌───────────────────────────────────────────────────────┐
          │  >  _________________________________________        │
          │                                                       │
          │  NAVIGATE                                             │
          │   › Go to Overview                              g o   │
          │     Go to Ledger                                g l   │
          │     Go to Accounts                              g a   │
          │     Go to Budget                                g b   │
          │                                                       │
          │  ACTIONS                                              │
          │     New transaction                              n    │
          │     New planned                                  N    │
          │     Reconcile account…                           r    │
          │                                                       │
          │  JUMP                                                 │
          │     Account · Checking                                │
          │     Category · Groceries                              │
          └───────────────────────────────────────────────────────┘
```

### Quick-add slide-over

```
                                                            ┌──────────────────┐
                                                            │ New transaction  │
                                                            │                  │
                                                            │ DATE             │
                                                            │ [ 2026-10-24   ] │
                                                            │                  │
                                                            │ AMOUNT           │
                                                            │ [        280,00] │
                                                            │                  │
                                                            │ CATEGORY         │
                                                            │ [ Groceries   ▾] │
                                                            │                  │
                                                            │ ACCOUNT          │
                                                            │ [ Checking    ▾] │
                                                            │                  │
                                                            │ DESCRIPTION      │
                                                            │ [              ] │
                                                            │                  │
                                                            │        [Cancel]  │
                                                            │        [ Save ]  │
                                                            └──────────────────┘
```
