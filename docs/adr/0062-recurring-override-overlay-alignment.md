# ADR-0062: Recurring Override Overlay — Align With Plan/Budget `rd-override` Card

- **Status**: Accepted
- **Date**: 2026-10-30
- **Related**: ADR-0031 (budget page composition), ADR-0030 (shared form interaction primitives), ADR-0050 (visual direction), ADR-0060 (unified entry modal)

## Context

The Ledger/Recurring tab exposes an "Override" kebab action and an "Override next…" row button. Both open `partials/recurring/_override_form.html`, which previously rendered a `form-stack` layout with a separate year number input, a 1-12 month `<select>`, and a labelled amount input. That form predates the v2 Rising Dough visual system and now looks jarringly different from the two overlays the user reaches from the Plan surface:

- **Plan/Budget** — `partials/budget/_override_form.html`, rendered as a compact `rd-override` card with a single amount input + save button + tier hint.
- **Plan/Year** — same `rd-override` card, triggered from a heatmap cell with the month/year preset.

Both surfaces also share the compact `rd-period-nav` combined year/month picker (details/summary popover with a 3×4 month grid), used in the top-right of Plan/Budget and Plan/Analytics headers.

The recurring overlay felt out of place. Users have to switch mental models between a Plan-shaped card and a legacy stacked form.

## Decision

Restyle `partials/recurring/_override_form.html` to visually match the Plan surfaces:

1. Keep the `.slide-over-root` modal shell (centered scrim modal per `app.css:1391`) — the overlay is still reached from `#modal-root`, so the shell stays. Dismissal rules (backdrop click, Esc via `shortcuts.js`, close button) are unchanged.
2. Replace the inner body with an `rd-override` card using a new `rd-override--standalone` modifier that strips the standalone border/shadow (the modal shell already supplies them) and lets the card fill the modal body.
3. Add a single `rd-period-nav` combined year/month selector in the card header, mirroring the top-right picker on Plan/Budget + Plan/Analytics. Prev/next step one month, the summary opens the 3×4 month grid with year +/- arrows. Hidden `year` + `month` form inputs are updated by the picker and submitted with the amount, so the server contract (`occurrence_in_month(rule, year, month)`) is unchanged.
4. Render the amount row with the shared `.rd-override__input` + `.rd-btn.rd-btn--primary` pair exactly as Plan/Budget does.
5. Keep the "Override occurrence" title + `aria-labelledby="recurring-override-title"` so dialog semantics and existing tests (`test_recurring_overrides_new_form_renders`, `..._defaults_to_next_due`) continue to hold.

## Consequences

- Visual consistency: both override entry points — Plan surfaces and Ledger/Recurring kebab — now share the same card primitive and the same period picker.
- No server changes. `GET /recurring/{id}/overrides/new` and `POST /recurring/{id}/overrides` remain untouched; the picker emits the same `year` + `month` form fields.
- New CSS surface: `rd-override--standalone`, `rd-override__head`, `rd-override__period`. The `rd-period-nav` family keeps its existing selectors — buttons swapped in for anchor tags inside the modal, which inherits cleanly from the existing rules.
- A small inline script wires the picker (prev/next arrows, year arrows, month grid). It is self-contained and scoped by `[data-recurring-override-form]`, so re-opens via HTMX re-wire correctly.
- Future: when the generalised "unified entry modal" lands (ADR-0060) this partial can be re-skinned on top of it; until then the Plan/Budget-shaped overlay is the canonical pattern.
