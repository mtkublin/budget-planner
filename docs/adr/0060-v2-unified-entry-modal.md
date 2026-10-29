# ADR-0060 — v2 Unified Entry Modal (Happened / Planned / Repeats)

Status: Accepted — 2026-10-29
Supersedes: parts of ADR-0030 §4 (per-mode form chrome), ADR-0051 §4 (Add Planned / Recurring overlays as separate forms).
Amends: ADR-0038 (Recurring form field order), ADR-0047 (Recurring formula UI chrome).

## Context

Manual visual-audit `docs/plans/v2/manual-audit.md` ids #15, #16, #17, #20, #21 flagged
that the Add-entry modal still diverged from the designer handoff:

- Add Planned + Add Recurring overlays still carried the legacy `.form-stack`
  chrome from v1 instead of the new Rising Dough `.rd-form` grid.
- The Happened/Planned/Repeats segmented was duplicated — once at the top of
  the slide-over (`partials/_add_entry_overlay.html`) and once inside the
  Actual form body (`partials/transactions/_form.html` `WHEN` fieldset).
- Field order in the Actual form did not match the mockup
  (`overlay-13-add-fixed.html`): current render had `[Date | Amount] / Category
  / [Account | Dest] / Description`; mockup specifies `Category / Amount /
  [Account | Dest] / [Date | Note]`.
- Recurring formula branch rendered as a nested checklist (`.form-stack__checklist`)
  with a radio-pair for sign, no coefficient suffix, and no visual grouping —
  design calls for a card-style builder with `+ ▾ / − ▾` sign chips, inline
  source chips, a `%`-suffixed coefficient input, and a per-term `Remove`
  button on each row (`overlay-12-add-formula.html`).

## Decision

1. **Single Happened/Planned/Repeats segmented control** at the top of the shared slide-over, owned by `partials/_add_entry_overlay.html`. The individual form bodies (`transactions`, `planned`, `recurring`) carry **no** mode switcher. Submission paths remain unchanged (`POST /transactions`, `POST /planned`, `POST /recurring`).
2. **Single `.rd-form` chrome** across all three mode bodies. Common primitives: `.rd-field`, `.rd-field__label`, `.rd-field__suffix`, `.rd-form-row.rd-form-row--2col`, `.rd-slideover-footer`.
3. **Field order** per mockup:
   - Actual + Planned: `Category / Amount / [Account | Dest · transit] / [Date | Note]`.
   - Recurring: `Category / [Account | Dest · transit] / Amount (Fixed value | Formula ƒ) / [Start | Cadence] / [Day of month | Note]`.
4. **Planned carries `dest_account_id`.** The domain `NewPlannedTransaction` already supported it; the web layer now parses the form field and threads it through.
5. **Recurring formula UI** uses the mockup's card layout: `.rd-formula` wraps the terms list; each term is a 4-column grid of `.rd-formula__sign` (two `.rd-chip` radios), `.rd-formula__sources` (checkbox chips), `.rd-formula__coef` (percent-suffixed numeric input), and a trailing ghost `Remove` button. A `.rd-formula__foot` provides `+ Add term` + the explanatory note.
6. The amount source toggle (`Fixed value / Formula ƒ`) is a `.rd-segmented--radio` placed inline with the `Amount` legend.

## Consequences

- The `WHEN` fieldset is removed from `transactions/_form.html` — any downstream
  consumer that expected the duplicate chip set must look at
  `partials/_add_entry_overlay.html` instead.
- `partials/planned/_form.html` and `partials/recurring/_form.html` no longer
  render `.form-stack`; CSS cleanup of orphan `.form-stack*` selectors is a
  follow-up for the final Phase J sweep.
- `test_accessibility.py::test_semantic_landmarks` dropped its `<footer>`
  assertion since no mockup carries a footer; the global page footer is
  removed by audit id #19.
- Planned router create endpoint now accepts an optional `dest_account_id`
  form field; absence remains valid and results in `None`.
- Server contracts for all three POST paths are otherwise unchanged — no DB
  migration, no new fields on existing DTOs.
