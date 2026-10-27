# T-091 [S] One-field-per-row form layout (`.form-stack`)

**Phase:** 8 — Post-redesign UX fixes
**Group:** G2
**Depends on:** T-053 (visual polish), T-069 (slide-over)
**Size:** S
**Status:** planned

## Scope

Replace the hard `grid grid-cols-2 gap-3` layout on every create/edit form with a shared `.form-stack` component so each labelled input occupies one row. 480 px slide-over currently crams two inputs per row and makes selects + date pickers unreadable. Same defect appears inline on Accounts and Categories pages.

## Changes

- `src/budget_planner/web/static/app.css`:
  - Add component block:
    ```css
    .form-stack {
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
      padding: var(--space-4);
      border: 1px solid var(--rule);
      border-radius: var(--radius-md);
    }
    .form-stack > label { display: flex; flex-direction: column; gap: var(--space-1); font-size: var(--text-sm); color: var(--muted); }
    .form-stack > label > input,
    .form-stack > label > select,
    .form-stack > label > textarea { width: 100%; }
    .form-stack__actions { display: flex; justify-content: flex-end; gap: var(--space-2); padding-top: var(--space-2); }
    ```
  - Keep the existing right-align rule for numeric inputs (`input[name="amount"]`, etc.).

- Replace in the five form partials:
  - `src/budget_planner/web/templates/partials/transactions/_form.html`
  - `src/budget_planner/web/templates/partials/accounts/_form.html`
  - `src/budget_planner/web/templates/partials/categories/_form.html`
  - `src/budget_planner/web/templates/partials/planned/_form.html`
  - `src/budget_planner/web/templates/partials/recurring/_form.html`

  For each:
  - Form root class: `form-stack`.
  - Drop `col-span-2` on description row.
  - Action row: `<div class="form-stack__actions">` instead of `<div class="col-span-2 flex justify-end gap-2">`.

## Non-goals

- No field order change.
- No new fields.
- No validation changes.
- No new form state (unchanged HTMX wiring).

## Test plan

- Existing integration tests for form POSTs stay green (selector by `name=` attribute).
- Add one Playwright snapshot per form at 480 px wide verifying inputs stack.
- Confirm the `+ Account`, `+ Category`, `+ Transaction` (slide-over), `+ Planned`, `+ Recurring` journeys still submit.

## Docs

- `docs/CHANGELOG.md` — one dated line.
- `docs/plans/v1/tasks.md` — mark `✅ T-091`.
- No ADR (component convention, not architectural).
