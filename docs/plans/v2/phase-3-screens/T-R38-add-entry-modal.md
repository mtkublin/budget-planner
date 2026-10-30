# T-R38 — Add entry modal (Fixed · Formula)

- **Phase**: 3 — Screens
- **Sequential**: after T-R24, T-R41.
- **Depends on**: T-R24 primitives, T-R41 (`POST /recurring/formula/preview`), ADR-0030 primitives.
- **References**: handoff §Add entry (1l formula, 2e fixed, mobile 1t), ADR-0056 §4.

## Context

Single modal handles three When-states (Happened / Planned / Repeats) and two Amount-shapes (Fixed · Formula). Direction is derived from the chosen category — no separate direction selector. Transit category reveals From/To account fields (same-currency guard per F7.5).

## Deliverables

- `templates/transactions/_add_form.html` with three stacked segments:
  1. **When** — `segmented(["Happened", "Planned", "Repeats"])`; selection swaps the submit endpoint + extra fields (cadence for Repeats).
  2. **Category** — `combobox` over live categories; selection sets a derived direction badge (via T-R13 macro) + reveals Transit extras (From/To) when category is the system Transit.
  3. **Amount** — `segmented(["Fixed", "Formula"])` (hidden for Happened state; only Repeats supports Formula per ADR-0047):
     - Fixed: single `amount` input + "per-day impact" sub-line computed server-side via a tiny preview endpoint (reuse T-R40 shape).
     - Formula: dynamic term list; add/remove term buttons; sign + source combobox + coefficient %; live preview via T-R41 debounced 200 ms.
- Account + date + note shared across states; date defaults to today in `display_timezone` (ADR-0007).
- Repeats cadence selector (monthly / quarterly / yearly) + next-due date.
- Submit routes:
  - Happened → `POST /transactions`.
  - Planned → `POST /planned`.
  - Repeats (Fixed) → `POST /recurring`.
  - Repeats (Formula) → `POST /recurring` with `amount_formula` payload per ADR-0047 schema v2.
- `⌘↵` / `Ctrl+↵` saves and keeps the modal open for the next entry.
- Amount field is focused first on mobile (narrow viewport branch sets `autofocus` on the amount input).
- Integration tests cover: Fixed Happened path, Fixed Planned, Fixed Repeats, Formula Repeats, Transit From/To reveal, same-currency enforcement, `⌘↵` keep-open.

## Acceptance criteria

- Visual-regression at D/T/M matches handoff `overlay-1l-add-formula.png`, `overlay-2e-add-fixed.png`, `mobile-1t-add-sheet.png`.
- Choosing Transit category reveals From/To account combo boxes; both must be the same currency; submit 422s otherwise with inline error.
- Formula preview updates ≤ 250 ms after a keystroke; non-positive result blocks save with inline error (ADR-0047).
- Cycle detection in Formula source selection fires inline (reused from T-R41 server validation).
- `⌘↵` posts the form, keeps the modal open, resets the amount field, keeps the category selection.

## Validation hook

```sh
pytest tests/integration/web/test_add_entry.py && \
  just test-visual --filter add-entry
```

## Risks & gotchas

- Direction badge updates on category change — do not rely on a round-trip; derive client-side from the combobox option's `data-direction` attribute, then re-validate server-side at submit.
- Repeats + Formula + ADR-0047: payload shape is `{schema_version: 2, terms: [{sign, coefficient_bps, source_category_ids}]}`. Reuse Phase 11 form parser.
- Mobile (sheet mode via T-R52): When segment collapses to a horizontal pill; amount focused first; the three segmented controls stay reachable via tab.

## Handoff notes

- T-R52 bottom sheet wraps this form at ≤ 640 px.
- T-R41 formula preview endpoint consumed here; keep the request shape stable.
