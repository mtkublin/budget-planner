# ADR-0047: Category Color Coding — Per-Category Override with Direction Default

- **Status**: Accepted
- **Date**: 2026-10-28
- **Amends**: [ADR-0023](0023-ux-redesign-information-architecture.md) (adds a visual encoding to the category identity surface); extends F1.6 in [requirements.md](../requirements.md).

## Context

Categories currently render as plain text wherever they appear (Ledger table "Category" column, Budget monthly summary + rules + yearly grid, Transactions row partial, Recurring row partial, Planned ledger view). The one place direction *is* color-encoded is the "Direction" pill (`direction_badge`) rendered via four CSS custom properties (`--income`, `--expense`, `--transit`, `--adjust` in `app.css`).

The Ledger "Direction" column effectively doubles as a per-row color key, but only for the pill. The category name itself — the primary identity surface — stays monochrome. A quick visual scan ("where is my grocery spend relative to income?") requires reading each row's text, not glancing at color blocks.

We want to color the category *name* everywhere it renders, driven by:

1. **Default:** the category's `direction` color (identical hue to the existing direction pill).
2. **Override:** an optional per-category color the user can set from the create / edit form.

The override must survive without weakening the direction pill (direction remains an orthogonal signal — pill color is always driven by `direction`, independent of the override).

## Decision

### Storage

Add a nullable `color TEXT` column to the `categories` table. Values are a lowercase CSS hex color literal matching `^#[0-9a-f]{6}$` (6-digit RGB only, no alpha, no shorthand). `NULL` means "inherit direction color."

```sql
ALTER TABLE categories ADD COLUMN color TEXT
    CHECK (color IS NULL OR color GLOB '#[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]');
```

- `NULL` is the explicit "unset" sentinel. Direction color is resolved at render time, not stored, so changing the project's `--income` / `--expense` oklch values in `app.css` continues to re-tint all unset categories.
- `GLOB` CHECK keeps bad hex out of the DB without needing a trigger. Case is normalized to lowercase in the service layer before INSERT / UPDATE.
- No `UNIQUE` constraint — multiple categories may share a color.

### Rendering helper

New Jinja global `category_label(category)` returns a `Markup` span, mirroring the shape of the existing `direction_badge` helper:

```html
<span class="cat-name" style="color: {resolved_color}">{escaped_name}</span>
```

- `resolved_color` is either `category.color` (hex) when set, or `var(--income)` / `var(--expense)` / `var(--transit)` / `var(--adjust)` when `NULL` — chosen from a dict keyed on `category.direction.value`, same source of truth as `_DIRECTION_COLORS` in `templating.py`.
- When `category` is `None`, the helper returns an empty `Markup` (templates currently guard with `{% if row.category %}`).
- Templates replace plain `{{ row.category.name }}` / `{{ line.category_name }}` / `{{ category.name }}` with `{{ category_label(row.category) }}` or an equivalent lookup. Where the service exposes only `category_name` (budget monthly summary + yearly grid), the service also exposes `category_color` (nullable hex) and `category_direction`, and the template calls a sibling helper `category_label_from_parts(name, direction, color)` to avoid loading full `Category` DTOs into the summary projection. Both helpers share the same color-resolution function.

The direction pill (`direction_badge`) is **unchanged** — pill color always reflects direction, so the pill and the colored name may share a hue (direction = default) or differ (override active). The pill therefore keeps its role as the pure direction indicator; the colored name becomes the category-identity indicator.

### Form surface

The categories form (`partials/categories/_form.html`) gets one new field for both create and edit:

- A native `<input type="color" name="color" value="{resolved_default}">` paired with a "Use direction default" checkbox / reset button.
- When "Use direction default" is checked (or on first-time create), the hex input is disabled and the server receives an empty / absent `color` value → stored as `NULL`.
- When the user picks a custom color, the checkbox clears and the hex is stored as-is (lowercased server-side).
- The reset button is a secondary affordance that re-enables the checkbox and re-renders the color picker's displayed default to the direction color (hex equivalent of the live oklch value — hard-coded hex approximations in `templating.py`, documented alongside `_DIRECTION_COLORS`).

The direction `<select>` keeps its existing create-only visibility (direction remains immutable post-create per `PatchCategory`'s docstring in `domain/categories.py`); only `name` + `color` are editable on an existing category.

### Service / repository changes

- `domain/categories.py`:
  - `Category` grows `color: str | None` (frozen dataclass field).
  - `NewCategory` grows `color: str | None = None`.
  - `PatchCategory` grows `color: str | None = None` plus a sentinel pattern for "explicit reset to NULL": the service layer accepts a separate `clear_color: bool` DTO flag so a `None` on `PatchCategory.color` continues to mean "no change" (consistent with existing `as_dict` semantics). On explicit reset the service issues `UPDATE … SET color = NULL`.
- `repositories/categories.py` adds `color` to `_COLUMNS`, `_row_to_category`, `create`, and `update`.
- `web/routers/categories.py` validates and normalizes the color input: strips whitespace, lowercases, re-validates against the same regex the SQL CHECK enforces. On invalid input returns 422 with field error `color`.
- Audit log entries (`AuditOperation.CREATE` / `UPDATE`) implicitly cover the new column via the existing `mutate` helper which snapshots full before/after rows.

### Template rollout

Replace the raw-name references in these templates with the helper call:

| Template | Current reference |
|---|---|
| `partials/categories/_row.html` | `{{ category.name }}` |
| `partials/transactions/_row.html` | `{{ txn.category.name if txn.category else '' }}` |
| `partials/recurring/_row.html` | `{{ category.name if category else '—' }}` |
| `ledger/_table.html` (actual, planned, recurring views) | `{{ row.category.name if row.category else '' }}` |
| `budget/index.html` (summary lines + rules rows) | `{{ line.category_name }}` / `{{ row.category_name }}` |
| `budget/_yearly.html` | `{{ row.category_name }}` |

Where only `category_name` is available (budget service projections `CategoryBudgetLine`, `YearlyRow`, and the rules row DTO), the dataclasses grow `category_color: str | None` and `category_direction: Direction` fields populated from the already-loaded `Category` objects in the same service pass. No extra SQL round-trip.

### Scope — where coloring applies

**Everywhere the category name is rendered.** That is the full list in the Template rollout table above. Direction pills, "Direction" column headers, "Category" column headers, and non-category text (description, amount, account) are **not** color-coded.

Charts (`budget/_breakdown.html` spend-by-category, `forecast/_chart.html`) are **out of scope** for v1 — their palette is currently Plotly's default. A follow-up ADR can wire category color into chart traces if the user requests it; it does not block this ADR because the color column + resolution helper give the chart layer a trivial lookup path.

### Accessibility

- The colored name sits on `--surface` / `--surface-raised` (oklch(98.5% / 96.5% …)). The four direction defaults were chosen in Phase 3 at ~55% lightness, which clears WCAG AA (4.5:1) against both surfaces.
- User-chosen colors are **not** contrast-checked at save time in v1. The create / edit form previews the color against the surface so the user can self-correct. A client-side warning (not a hard block) is a follow-up.
- Reduced-motion / dark-mode: no changes — the color is used only for `color:` not for backgrounds, matches the existing pill treatment, and reduced-motion is unrelated.

## Consequences

- **DB migration cost:** one additive `ALTER TABLE` (0010). No table rebuild, no FK pragma toggle. Backward-compatible — pre-ADR-0047 rows get `color = NULL` by column default and continue to render in direction color exactly as before.
- **Service surface widens by three fields** (`Category.color`, `NewCategory.color`, `PatchCategory.color` + `clear_color`). All optional; no caller is forced to pass them.
- **Visual change is broad** (every Ledger row, Budget row, Recurring row, Planned row). Visual regression suite under `tests/visual/` will have baselines rewritten in this task's PR; the frontend-visual-audit skill run gates the merge per `CLAUDE.md`.
- **Direction pill retains its single-purpose semantic.** It is still the only direction signal; color overrides on category names cannot confuse "is this income or expense" because the pill answers that question regardless of the name's hue.
- **CSV / Parquet exports** (F1.4) do not include color. Color is a presentation concern; exports stay data-only.

## Alternatives Considered

- **Classify color via `direction` lookup only, no override.** Rejected: user explicitly asked for an override; blanket direction-only coloring also reads as redundant with the pill.
- **Store color as an integer sRGB triple or a palette index.** Rejected: hex is the universal exchange format for CSS and the `<input type="color">` DOM API; integer storage adds a conversion step with zero storage saving in SQLite.
- **Compute the pill-tinted background as the name background instead of coloring the text.** Rejected: Ledger table rows are already dense; background-tinting every category cell would overwhelm the hairline-rhythm grid defined by the editorial direction in `app.css`. Coloring the text keeps the row calm and lets the pill carry the "chip" affordance it already has.
- **Store color as a reference to a seeded palette table.** Rejected: adds a join on every ledger row for a value the user picks per category once, with no sharing or theming benefit at single-user scale.
