# T-095 — ADR-0025 + Requirements + Phase 9 Docs Scaffolding

> Phase 9 — Left Daily Spend. Status: landed by this task (docs-only round).

## Purpose

Lay the paper trail for Phase 9 before any code lands. Writes the ADR that governs the new `user_preferences` table and the "income anchor" concept, adds the two new requirements (F4.6, F4.7) to `docs/requirements.md`, publishes the Phase 9 task stubs under `docs/plans/v1/phase-9/`, renames the prior "Phase 8 — Deferred to v2" entry to Phase 10 so Phase 9 can slot in as the next active phase, and records the day in `docs/CHANGELOG.md`. No source files change in this task.

## Inputs / prerequisites

- Upstream tasks: none (this is the first task of the phase).
- Binding standard: `CLAUDE.md` change policy — docs come first, no exceptions.
- Adjacent precedent: [`T-060`](../phase-6/) for Phase 6 and the equivalent "T-080 docs round" that opened Phase 7 (see `docs/CHANGELOG.md` entry for 2026-10-25 → T-080 line). Mirror both.

## Deliverables

New files:

- `docs/adr/0025-user-preferences-and-income-anchor.md` — the ADR.
- `docs/plans/v1/phase-9/README.md` — Phase 9 overview + task table + exit criteria.
- `docs/plans/v1/phase-9/T-095-adr-and-docs-scaffolding.md` — this file.
- `docs/plans/v1/phase-9/T-096-migration-user-preferences.md`
- `docs/plans/v1/phase-9/T-097-domain-and-repository.md`
- `docs/plans/v1/phase-9/T-098-preferences-service.md`
- `docs/plans/v1/phase-9/T-099-next-planned-income-lookup.md`
- `docs/plans/v1/phase-9/T-100-budget-service-left-daily-spend.md`
- `docs/plans/v1/phase-9/T-101-budget-ui-anchor-selector.md`

Updated files:

- `docs/adr/README.md` — add the ADR-0025 row.
- `docs/requirements.md` — append F4.6 (left daily spend) and F4.7 (income anchor preference) to §2.4 Monthly Budget.
- `docs/plans/v1/tasks.md` — insert Phase 9 with T-095..T-101 and rename the trailing deferred list from Phase 8 to Phase 10.
- `docs/CHANGELOG.md` — dated line for the T-095 landing.

Not deliverables (explicitly out of scope here):

- No migration file.
- No new Python modules.
- No change to existing services, routers, or templates.
- No tests.

## Step-by-step

1. **Write the ADR.** Follow the ADR-0024 shape: title, status/date header, Context, Decision (numbered), Consequences (pros, cons/costs, non-goals), Alternatives Considered, References. Keep it to one page of substance.
2. **Append to the ADR index** (`docs/adr/README.md`) in strict sequential order under the ADR-0024 row.
3. **Edit `docs/requirements.md`.** After `F4.5` in §2.4, add `F4.6` and `F4.7` with the exact wording from the ADR summary. Do not shift any section numbering past §2.4.
4. **Edit `docs/plans/v1/tasks.md`.** Replace the `## Phase 8 — Deferred to v2` header with the new `## Phase 9 — Left Daily Spend` block (task entries T-095..T-101 with dependencies). Append `## Phase 10 — Deferred to v2` after the Phase 9 block preserving the existing deferred list verbatim.
5. **Create `docs/plans/v1/phase-9/`** and populate it with `README.md` plus one stub per task (`T-095..T-101`), each following the Phase 6 template (`Purpose · Inputs/prerequisites · Deliverables · Step-by-step · Validation / acceptance · Risks & gotchas · Handoff notes`).
6. **Append `docs/CHANGELOG.md`** with a dated line mirroring the Phase 6 / Phase 7 kickoff style. One paragraph is sufficient.

## Validation / acceptance

- `ls docs/adr/0025-*.md` resolves to one file.
- `grep -n "0025" docs/adr/README.md` returns the index row.
- `grep -nE "F4\\.[67]" docs/requirements.md` returns both new bullets.
- `grep -n "^## Phase " docs/plans/v1/tasks.md` returns `Phase 0..Phase 7, Phase 9, Phase 10` in order (no `Phase 8`).
- `ls docs/plans/v1/phase-9/` lists `README.md` plus seven task stubs (`T-095-*.md` through `T-101-*.md`).
- `head -n 5 docs/CHANGELOG.md` shows a new `T-095` line at the top of the current day's block.
- `just test` / `just lint` are unaffected (no code touched).

## Risks & gotchas

- **Phase number gap.** Numbering jumps from Phase 7 directly to Phase 9. This is intentional per the plan decision — the prior Phase 8 (Deferred to v2) was renumbered to Phase 10 so the active-work phases stay contiguous. Document this at the top of `docs/CHANGELOG.md` so future readers do not treat the gap as a mistake.
- **ADR-0024 and T-080..T-086 collisions.** Those are owned by Phase 7 (Liability Accounts). Do not touch them. The next free ADR is `0025`; the next free task range is `T-095..T-101`.
- **Index drift.** Add the ADR row and the task entries in the exact order used by prior phases. The ADR table is append-only.

## Handoff notes

- Hand-off to T-096: migration file name is `migrations/0005_user_preferences.sql` (prior migration `0004_add_liability_columns.sql` from Phase 7 is the last applied). Idempotent `CREATE TABLE IF NOT EXISTS` guarded, no seed row.
- Hand-off to T-097: domain module name is `src/budget_planner/domain/preferences.py`; repository module name is `src/budget_planner/repositories/preferences.py`.
- Commit shape: `docs(T-095): plan Phase 9 "Left daily spend" (ADR-0025, F4.6, F4.7)`.
