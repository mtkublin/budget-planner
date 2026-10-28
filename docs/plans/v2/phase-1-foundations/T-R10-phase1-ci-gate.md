# T-R10 — Phase-1 CI gate

- **Phase**: 1 — Foundations
- **Sequential**: last Phase 1 task.
- **Depends on**: T-R01..T-R09, T-R63, T-R64.
- **References**: ADR-0027 (frontend toolchain).

## Context

Close Phase 1 with every new hook, every new baseline, every new static file participating in CI. This task is the acceptance signal that Phase 2 can begin.

## Deliverables

- `just ci` recipe extended (if needed) so every Phase 1 addition runs:
  - `tailwind-check` (regen `static/tailwind.css` and diff).
  - `token-diff` (handoff tokens.css == repo tokens.css).
  - `stylelint` with the new OKLCH-outside-tokens rule.
  - `pytest` coverage ≥ 90 %.
  - `just test-visual --filter canary` passes (T-R09 baseline).
- `.github/workflows/ci.yml` matrix updated if any job needed a new step.
- Append dated line to `docs/CHANGELOG.md` with Phase 1 ✅ summary.
- Mark every Phase 1 task line in `tasks.md` with `✅`.

## Acceptance criteria

- `just ci` green on a fresh clone.
- A deliberate token drift (edit `src/.../tokens.css`, run hook) fails `token-diff`.
- A deliberate hard-coded `oklch` in `_amount.html` fails `stylelint`.
- A deliberate stale `static/tailwind.css` fails `tailwind-check`.
- Visual-regression baseline matches on first run; a 1-px drift fails the suite.

## Validation hook

```sh
just ci
```

## Risks & gotchas

- Node 20 required for Tailwind v4 CLI; the GitHub Actions matrix already pins Node 20 per `docs/requirements.md` §3.6.
- Visual-regression on CI must set `TZ=Europe/Warsaw` so date-dependent screenshots do not drift against local baselines.

## Handoff notes

- Phase 2 opens with T-R11; depends only on this gate.
- Any Phase 1 task reopened after T-R10 requires re-running this gate and reasserting all four hooks.
