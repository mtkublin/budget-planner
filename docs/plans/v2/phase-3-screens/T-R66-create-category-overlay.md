# T-R66 — Create category overlay reskin

- **Phase**: 3 — Screens
- **Sequential**: after T-R24, T-R35.
- **Depends on**: T-R35 (Settings · Categories), T-R24 (primitives).
- **References**: handoff screen 2d, ADR-0048, ADR-0023.

## Context

Create and Edit category share one overlay. Rising Dough version adds colour swatches with a live preview of the pill + badge.

## Deliverables

- `templates/settings/_category_form.html`:
  - Name field.
  - Direction radio: Expense / Income (immutable after any usage; locked for system categories).
  - Colour source: direction default or one of 10 swatches (ADR-0048 hue values).
  - Live preview panel rendering the pill + direction badge via `category_pill` + `direction_badge` macros (T-R12, T-R13) using the current field values.
- `POST /categories` + `PATCH /categories/{id}` behaviour unchanged.
- Live preview wired via Alpine (small reactive block) or vanilla event listeners (choose the lighter path).
- Visual-regression baselines at D/T/M matching handoff `overlay-2d-create-category.png`.

## Acceptance criteria

- Choosing a swatch updates the preview pill without a server round-trip.
- "Use direction default" resets the hue override to the direction base (ADR-0048).
- Direction radio excludes `transit` + `adjustment` (ADR-0023; system-category guard).
- Edit path pre-fills every field; direction locked if any txn/planned/recurring references the category.

## Validation hook

```sh
pytest tests/integration/web/test_categories.py::test_create_category_overlay && \
  just test-visual --filter create-category
```

## Risks & gotchas

- Live preview must update on every keystroke in the name field — pills should feel responsive. Debounce only if the preview flickers.
- Direction immutability check must survive HTMX re-render (422 branch).

## Handoff notes

- T-R35 Settings · Categories list links `Edit` to this overlay.
