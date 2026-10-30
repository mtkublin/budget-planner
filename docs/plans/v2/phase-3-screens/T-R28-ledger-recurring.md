# T-R28 — Ledger · Recurring

- **Phase**: 3 — Screens
- **Sequential**: after T-R24, T-R26.
- **Depends on**: T-R24 primitives, T-R71 (archived-categories decision).
- **References**: handoff §Ledger · Recurring, ADR-0038, ADR-0047 (formula chaining), ADR-0046 (soft-consume overrides).

## Context

Most complex Ledger tab. Groups rules Monthly / Yearly, each row has override count + chevron expanding to show (a) the overrides list with Remove per override and (b) for formula rules, the signed-term derivation sourced from `_sum_category_in_month`.

## Deliverables

- `templates/ledger/_recurring.html` composing:
  - `_group_header.html` ("Monthly" / "Yearly").
  - `_recurring_row.html`: next due · rule name + account · category pill · amount (ƒ chip if formula) · override count badge · action cluster (`Edit · Skip next · ⋯ · chevron`).
  - `_recurring_accordion.html` (chevron target):
    - Overrides list — one `<li>` per non-consumed override (date, type Amount/Skipped/Moved, value, Remove button). Already shipped in a prior commit for the Ledger `next_due`-only shape; this task extends to all future overrides per ADR-0046 §Default `list_overrides` filter.
    - For formula rules: `_formula_derivation.html` showing signed terms + resolved value + source links; recursion resolved via existing `services.recurring.formula.derive(rule, when)` or new helper.
- Action menu (⋯):
  - Override next… (opens the Phase 11 slide-over pre-filled with `occurrence_date = rule.next_due`).
  - Duplicate — new `POST /recurring/{id}/duplicate` (new; service + repository + audit).
  - Deactivate — existing `POST /recurring/{id}/deactivate`.
  - Archive rule — soft-deletes the rule; distinct from Deactivate (which sets `active=0` but keeps row).
- Archived-category source rendering (per T-R71 decision outcome): if the rule's category is archived, row renders muted + warning chip "category archived — restore to edit"; derivation references archived source rules identically.
- Promote-in-place (ADR-0056 §1) reused from T-R27 shape.
- Integration tests cover: accordion opens + closes, overrides list for a rule with 3 future overrides, derivation render for a 2-term formula with chained source, Duplicate endpoint, archived-category warning chip.

## Acceptance criteria

- Visual-regression baseline matches handoff `desktop-1f-ledger-recurring.png` at D/T/M.
- `frontend-visual-audit` returns zero findings including when 3 accordions are open.
- Chevron keyboard-reachable; Enter toggles; Esc collapses.
- Duplicate action creates a new rule with the same shape, `active=1`, `next_due` set per the source rule's cadence (not past-dated).
- Derivation hyperlinks to source rules; clicking jumps to the source rule's accordion (if same category group) or filters to it.
- Promote keyboard shortcut `↵` on focused row works.

## Validation hook

```sh
pytest tests/integration/web/test_ledger_recurring.py && \
  invoke frontend-visual-audit at 1440 1024 375 against "/ledger?view=recurring"
```

## Risks & gotchas

- Formula derivation is recursive; cap display depth at 3 to avoid runaway accordions. Beyond depth 3 render "… and 2 more levels — see source rules" with links.
- Overrides list uses `list_overrides` (filters consumed); derivation uses `list_overrides_all` (includes consumed) per ADR-0046.
- Duplicate action must not duplicate overrides — new rule starts clean.
- T-R71 outcome affects whether Edit is enabled on a rule whose source category archived; the row shape must handle both decisions without a rebuild.

## Handoff notes

- Promote fragment route `GET /recurring/{id}/promote-form` is shared with Today (T-R25). Keep the shape identical.
- `Skip next` button fires existing `POST /recurring/{id}/skip-next`; toast via T-R61.
