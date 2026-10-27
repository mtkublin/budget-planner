# T-101 — `/budget` Card + `/budget/manage` Anchor Selector

> Phase 9 — Left Daily Spend. Status: pending.

## Purpose

Make the metric visible and the anchor settable from the web UI. One new card on `/budget`, one new section on `/budget/manage`, one new POST endpoint. HTMX refresh so changing the anchor updates the main page without a hard reload.

## Inputs / prerequisites

- Upstream tasks: T-036 (existing budget router + templates), T-100 (`MonthSummary` extension).
- Binding standards:
  - [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — `/budget` is a workflow surface; the metric belongs here, not on Overview.
  - [`ADR-0025`](../../../adr/0025-user-preferences-and-income-anchor.md).
  - `rules/web/design-quality.md` — no default-template look.
- Adjacent precedents:
  - `src/budget_planner/web/routers/budget.py` — existing endpoints and `HX-Trigger: budget-stale` convention.
  - `src/budget_planner/web/templates/budget/manage.html` — existing three-tier override form shape to mirror.
  - T-063 Overview "Budget-left headline" composition for display-size numerics (see `docs/plans/v1/phase-6/T-063-overview-composition.md`).

## Deliverables

Updated files:

- `src/budget_planner/web/routers/budget.py`:
  - `GET /budget` passes `today = datetime.now(ZoneInfo(settings.display_timezone)).date()` into `services.budget.month_summary(..., today=today)` and keeps the current template context key names.
  - `GET /budget/manage` adds two new context keys:
    - `income_categories: list[Category]` — all live categories with `direction == INCOME`.
    - `current_anchor_id: int | None` — from `preferences_svc.get_income_anchor_category_id(conn)`.
  - New endpoint `POST /budget/preferences/income-anchor`:
    - Form body `category_id: str` — accepts a numeric string or empty string.
    - Empty string → `preferences_svc.set_income_anchor_category_id(conn, user_id=1, category_id=None)`.
    - Numeric → parsed to `int`; on `ValueError` return 422 with inline `_form_errors.html`.
    - On `InvalidAnchorCategoryError` return 422 with inline error.
    - On success emit `HX-Trigger: budget-stale` and return the updated manage-page fragment or 204 (choose per existing HTMX conventions on sibling endpoints).

- `src/budget_planner/web/templates/budget/index.html`:
  - New `<section class="surface surface--raised" aria-labelledby="lds-heading">` at the top of the page, above the existing table.
  - Display-size `{{ summary.left_daily_spend_minor|money(base_ccy) }}` (or `—` when `None`).
  - Caption line: `{{ summary.totals.remaining_minor|money(base_ccy) }} ÷ {{ summary.days_until_next_income }} day{{ 's' if summary.days_until_next_income != 1 else '' }}, next income {{ summary.next_income_date|date_fmt }} ({{ summary.anchor_category_name or 'end of month' }})`.
  - Use existing T-053 tokens for typography scale, surface treatment, and hairline rules. Avoid stock card-grid look.

- `src/budget_planner/web/templates/budget/manage.html`:
  - New `<section id="income-anchor" ...>` with a `<form hx-post="/budget/preferences/income-anchor" hx-swap="outerHTML">`:
    - `<label for="anchor-select">Income anchor</label>`.
    - `<select name="category_id" id="anchor-select">` with a `<option value="">— none —</option>` and one `<option value="{{ c.id }}" {{ 'selected' if c.id == current_anchor_id else '' }}>{{ c.name }}</option>` per income category.
    - Short helper copy explaining what the anchor controls (link to `#left-daily-spend` on `/budget`).

New tests under `tests/integration/web/test_budget.py` (or sibling file if the current one is large):

- `test_left_daily_spend_card_renders_number_and_caption` — pre-seed anchor + planned income → assert both the money and the caption text appear in the HTML of `GET /budget`.
- `test_left_daily_spend_card_renders_dash_when_zero_budget` — no budget defaults set → card shows `—`.
- `test_left_daily_spend_card_shows_end_of_month_fallback_when_anchor_unset`.
- `test_manage_page_lists_income_categories_in_select`.
- `test_post_anchor_sets_preference` — POST valid id → `preferences_repo.get(...)` returns the row.
- `test_post_anchor_empty_clears_preference`.
- `test_post_anchor_rejects_non_income_category` — returns 422 with inline error.
- `test_post_anchor_rejects_unknown_category` — returns 422.
- `test_post_anchor_emits_hx_trigger_budget_stale`.
- `test_stale_anchor_renders_fallback_without_500` — set anchor, soft-delete the category, GET `/budget` → 200, caption shows "end of month".

## Step-by-step

1. **Router: `GET /budget`.** Add the `today` computation (`ZoneInfo(settings.display_timezone)`); thread it into `month_summary`. All other context keys stay the same.
2. **Router: `GET /budget/manage`.** Query live income categories (`[c for c in categories_repo.list_all(conn) if c.direction is Direction.INCOME and c.deleted_at is None]`) and fetch the current anchor id. Pass both to the template.
3. **Router: new POST.** Define the handler per the semantics above. Follow the existing `_render_error_fragment` pattern used by sibling endpoints. Emit the `HX-Trigger` header via the shared `trigger(response, ...)` helper from `web/htmx.py`.
4. **Template `index.html`.** Insert the card as the first block of the page `<main>`. Use design-quality tokens: display-size numeric, hairline rule under the caption, mono tabular numerals for the number. Keep the structure semantic — `<section>` + `<h2>` + `<p class="eyebrow">` for caption. Avoid utility soup.
5. **Template `manage.html`.** Add the anchor section above the existing default/recurring/one-off override forms. Keep tab order sensible for keyboard users.
6. **Accessibility.** Match T-052 patterns: labelled `<select>`, `aria-live="polite"` on the card so the HTMX swap announces changes to screen readers.
7. **Reduced motion.** The HTMX swap uses token motion durations (ADR-0023); nothing new to configure.

## Validation / acceptance

- All new tests pass; existing budget tests still pass.
- Coverage ≥ 95% on `web/routers/budget.py`.
- `just dev`: manually set anchor, change category, add planned one-off income — observe the card update after HTMX swap or page reload.
- `just lint` + `just typecheck` + `just ci` green.
- `GET /budget` returns 200 even when the anchor references a soft-deleted category (fallback path exercised).

## Risks & gotchas

- **Timezone.** The `today` computation **must** use `settings.display_timezone`, not UTC. Mid-month-boundary bug otherwise — a user in Warsaw at 00:30 on Feb 1 would see Jan 31's view.
- **Form POST shape.** HTML forms serialise `<select>` as `category_id=<value>`; an unselected empty option sends `category_id=` (empty string). Service layer must treat empty-string as "clear".
- **HTMX trigger coverage.** The existing `/budget` page listens for `budget-stale`; the manage page does not reload itself. Verify the trigger routing: emitting on the POST tells any page listening to refresh. If `/budget/manage` should visibly update the select on save, return a swap fragment with the new `selected` option; otherwise document the behaviour (page reload is sufficient).
- **No new design tokens.** Keep to the T-053 token set. Any new palette value is a scope breach — flag and defer.
- **Stale-anchor regression test.** `test_stale_anchor_renders_fallback_without_500` is a cheap guard against a real failure mode. Do not skip it.

## Handoff notes

- Hand-off to README update (future task if needed): the `/budget` surface now has a prominent metric worth mentioning in the project README's "Daily commands + what you see" section.
- Commit shape: `feat(T-101): /budget — left daily spend card + anchor selector (ADR-0025, F4.6, F4.7)`.
