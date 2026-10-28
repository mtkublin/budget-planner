# T-R71 — Archived categories on existing recurring rules

- **Phase**: 0 — Decisions
- **Sequential**: yes; blocks T-R28, T-R35.
- **Depends on**: none.
- **References**: handoff `docs/application_redesign_handoff/docs/07-open-items.md` §Decisions needed, ADR-0048, ADR-0038.

## Context

The handoff asks: "Whether archived categories can be used on existing recurring rules." Two interpretations:

1. **Block the archive** if any live recurring rule points at the category (symmetric with system-category immutability).
2. **Allow the archive** but keep the rule running; UI shows the category pill in a muted state and new rules cannot pick an archived category.

The repository must agree with the UI; recurring promotion in `services.recurring.promote_recurring` touches `categories.id` on insert.

## Deliverables

- New ADR (next free number, likely `0057`) or amendment to ADR-0048.
- Document chosen behaviour, repository invariants, UI treatment, and migration implications.
- Update `docs/requirements.md` F1.6 if the invariant changes.

## Acceptance criteria

- ADR Accepted; status + date header filled in.
- Behaviour description unambiguous for implementers of T-R28 and T-R35.
- Repository invariant covered by at least one new regression test name in the ADR's "Implementation checkpoints" section.

## Risks & gotchas

- Allowing archive while rules run makes the "archived" state partial — users see the category pill but cannot select it in new forms. UI must make this discoverable (e.g. small "archived — restore to edit" chip on the rule row).
- Blocking the archive forces users to deactivate rules first. UX cost.

## Handoff notes

- The chosen behaviour feeds T-R35 (Settings · Categories archive button copy) and T-R28 (Ledger · Recurring row rendering when source category is archived).
