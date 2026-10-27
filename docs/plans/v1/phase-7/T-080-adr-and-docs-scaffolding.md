# T-080 — ADR-0024 + Requirements + Phase 7 Docs Scaffolding

> Phase 7 — Liability Accounts. Status: landed by this task (docs-only round).

## Purpose

Lay the paper trail for Phase 7 before any code lands. Writes the ADR that governs the new `is_liability` boolean and `credit_limit_minor` column on `accounts`, adds the new requirement (F2.1a) to `docs/requirements.md`, publishes the Phase 7 task stubs under `docs/plans/v1/phase-7/`, and records the day in `docs/CHANGELOG.md`. No source files change in this task.

## Inputs / prerequisites

- Upstream tasks: none (this is the first task of the phase).
- Binding standard: `CLAUDE.md` change policy — docs come first, no exceptions.
- Adjacent precedent: [`T-060`](../phase-6/) for Phase 6 and [`T-095`](../phase-9/) for Phase 9 — mirror both.

## Deliverables

New files:

- `docs/adr/0024-liability-accounts-and-credit-limit.md` — the ADR.
- `docs/plans/v1/phase-7/README.md` — Phase 7 overview + task table + exit criteria.
- `docs/plans/v1/phase-7/T-080-adr-and-docs-scaffolding.md` — this file.
- `docs/plans/v1/phase-7/T-081-migration-liability-columns.md`
- `docs/plans/v1/phase-7/T-082-domain-and-repository.md`
- `docs/plans/v1/phase-7/T-083-fortune-service.md`
- `docs/plans/v1/phase-7/T-084-web-form-and-templates.md`
- `docs/plans/v1/phase-7/T-085-transaction-form-soft-warning.md`
- `docs/plans/v1/phase-7/T-086-seed-and-e2e-journey.md`

Updated files:

- `docs/adr/README.md` — add the ADR-0024 row + mark ADR-0010 as "superseded in part by ADR-0024" for behavioural classification only.
- `docs/requirements.md` — append F2.1a (liability accounts) to §2.2 Account Management; add in-scope note under §3.8 so the deferred list does not read as a prohibition.
- `docs/CHANGELOG.md` — dated line for the T-080 landing.

Not deliverables (explicitly out of scope here):

- No migration file.
- No new Python modules.
- No change to existing services, routers, or templates.
- No tests.

## Step-by-step

1. **Write the ADR.** Follow the ADR-0022 shape: title line, status/date header, Context, Decision (numbered), Consequences, Alternatives Considered. One page of substance.
2. **Append to the ADR index** (`docs/adr/README.md`) in strict sequential order under the ADR-0023 row. Edit the ADR-0010 row to note "superseded in part by [ADR-0024](0024-liability-accounts-and-credit-limit.md) for behavioural classification; descriptive `type` unchanged".
3. **Edit `docs/requirements.md`.** After `F2.1` in §2.2, add `F2.1a` with the exact wording from the ADR summary (liability flag, credit-limit field, soft enforcement, assets/liabilities/net split). After the §3.8 bullet list, add a note that credit-card / liability accounts are **in scope** for v1 via ADR-0024, and that future liability variants (loans, mortgages, lines of credit, overdraft facilities) stay out of v1 scope but reuse the same shape.
4. **Create `docs/plans/v1/phase-7/`** and populate it with `README.md` plus one stub per task (`T-080..T-086`), each following the Phase 6 / Phase 9 template (`Purpose · Inputs/prerequisites · Deliverables · Step-by-step · Validation / acceptance · Risks & gotchas · Handoff notes`).
5. **Append `docs/CHANGELOG.md`** with a dated line mirroring the Phase 6 kickoff style. One paragraph is sufficient.

## Validation / acceptance

- `ls docs/adr/0024-*.md` resolves to one file.
- `grep -n "0024" docs/adr/README.md` returns the index row.
- `grep -n "superseded in part by.*0024" docs/adr/README.md` returns the ADR-0010 annotation.
- `grep -nE "F2\\.1a" docs/requirements.md` returns the new bullet.
- `ls docs/plans/v1/phase-7/` lists `README.md` plus seven `T-08x-*.md` files.
- `head -n 10 docs/CHANGELOG.md` shows a new `T-080` line in the current day's block.
- `just test` / `just lint` are unaffected (no code touched).

## Risks & gotchas

- **ADR numbering collision.** ADR-0023 is already owned by the Phase 6 UX redesign; the next free number is `0024`. Do not reuse `0023`.
- **Task numbering collision.** Phase 6 overflowed into T-070..T-072; the next free range for a new phase is `T-080..T-086`. Do not reuse `T-07x`.
- **ADR-0010 is not deleted.** Supersession is **in part** — descriptive `type` continues to live under ADR-0010, behavioural classification moves to ADR-0024. The two coexist cleanly because they describe orthogonal concerns.
- **Index drift.** Add the ADR row in the exact order used by prior phases. The ADR table is append-only.

## Handoff notes

- Hand-off to T-081: migration file name is `migrations/0004_add_liability_columns.sql` (prior migration `0003_seed_system_rows.sql` is the last applied). Idempotent additive `ALTER TABLE` statements only; no backfill required (defaults handle existing rows).
- Hand-off to T-082: new fields on `Account`, `NewAccount`, `PatchAccount` are `is_liability: bool = False` and `credit_limit_minor: int | None = None`.
- Commit shape: `docs(T-080): plan Phase 7 "Liability accounts" (ADR-0024, F2.1a)`.
