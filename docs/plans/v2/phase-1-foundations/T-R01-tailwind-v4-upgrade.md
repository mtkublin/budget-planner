# T-R01 — Tailwind v4 upgrade

- **Phase**: 1 — Foundations
- **Sequential**: yes; blocks every later Phase 1 task.
- **Depends on**: none (v1 CI green on `main`).
- **References**: ADR-0052 §1, ADR-0027 (frontend toolchain).

## Context

Upgrade the Tailwind build chain from v3 (JS config + CLI) to v4 (CSS-first `@theme`). v4 is a prerequisite for ADR-0050's OKLCH token wiring — Tailwind v3 cannot expose CSS variables as named utilities via `@theme`. The upgrade also removes the `tailwind.config.ts` file in favour of a single `static/css/app.css` entry.

## Deliverables

- `package.json`: `tailwindcss` → `^4.0`.
- `package-lock.json` / `npm ci` reproducible.
- New entry file: `src/budget_planner/web/static/css/app.css` with:
  ```css
  @import "tailwindcss";
  @import "../tokens.css";       /* added in T-R02 */
  @import "./fonts.css";          /* added in T-R03 */
  @theme { /* populated in T-R02 */ }
  ```
- Delete `tailwind.config.ts`.
- `just css` / `just css-watch` recipes untouched (names stay); verify they call the v4 CLI binary.
- `tailwind-check` pre-commit hook unchanged logic; verify it still catches stale `static/tailwind.css`.
- `.pre-commit-config.yaml` version bumps if the stylelint plugin needed a v4-compatible release.

## Acceptance criteria

- `just css` emits `static/tailwind.css` without warnings.
- `tailwind-check` fails cleanly when the output is stale (delete the file, run hook, verify red; rebuild, verify green).
- `just ci` green; no visual regression against the current baseline (v1 screens render unchanged).
- `grep "tailwind.config" .` returns no live hits.

## Validation hook

```sh
just css && just ci && npx tailwindcss --version | grep -E "^v?4\\."
```

## Risks & gotchas

- v4 renames some utilities. Any template using an obsolete utility fails at build time. Run `just css` early and triage; the `templates/**` glob is unchanged, so the compiler enumerates every utility used.
- The `@theme` block cannot sit *before* `@import "tailwindcss"`; v4 docs are specific about order.
- If visual-regression baselines drift from v3 → v4 subtleties (`fontSize` default scale changes), regenerate baselines in T-R09 against v4 output, not v3.

## Handoff notes

- The next task (T-R02) populates `tokens.css` + the `@theme` block.
- Keep this PR mechanical. If an obsolete utility blocks the build, migrate the utility inline in this PR; do not refactor templates.
