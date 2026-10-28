# Phase 1 — Foundations

> Tailwind v4, tokens pipeline, self-hosted fonts, product rename, nav skeleton + legacy 302 shims, `/dev/components` stub, stylelint rules, visual-regression canary.
>
> Blocks every later phase. Scope is **web platform only** — no screen rebuilds yet, every v1 screen must still render after Phase 1.

Entry: v1 CI green on `main`; ADRs 0050..0056 Accepted.

Exit: see `../implementation_plan.md` §Phase 1.

Tasks: T-R01..T-R10. Order:

1. T-R01 Tailwind v4 upgrade — baseline shift, everything hangs off this.
2. T-R02 tokens pipeline — tokens.css + `@theme`.
3. T-R03 self-hosted fonts.
4. T-R04 base shell refactor.
5. T-R05 product rename (parallel-safe with T-R04 but must land before Phase 2).
6. T-R06 nav skeleton + legacy 302 shims.
7. T-R07 `/dev/components` stub.
8. T-R08 stylelint custom rules.
9. T-R09 visual-regression canary baseline.
10. T-R10 Phase-1 CI gate + CHANGELOG line.

ADR references: 0050, 0051, 0052, 0027.
