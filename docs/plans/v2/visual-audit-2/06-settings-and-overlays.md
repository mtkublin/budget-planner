# 06 · Settings and Overlays

## `/settings` — Categories tab (mock `desktop-1n-settings-categories.png`)

| # | Element | Status |
|---|---|---|
| 1 | Shell + eyebrow `SETTINGS` + title `Categories` + tabs `Categories · Currency & FX · Preferences` | ✅ |
| 2 | `+ New category` button in top-right | ✅ |
| 3 | **Duplicate `+ New category` button in-body** below `TAXONOMY · Categories` heading | ⚠️ PARTIAL — duplicate affordance |
| 4 | **Income anchor selector** pinned at top (`Income anchor · starts each paycheck window → WYPŁATA`) | ❌ MISSING |
| 5 | **Grouped sections** `Expense (N) / Income (N) / System (read-only)` | ❌ MISSING — current renders a flat alphabetical list; locked system rows (Reconciliation, Transit) sit mid-list with `(system)` suffix |
| 6 | **Row shape**: pill + direction badge + **colour source indicator** (`Direction default` / `Override · magenta`) + `Edit · Archive` | ⚠️ PARTIAL — pill ✓, direction ✓, **no colour source indicator**, actions are `Edit · Delete` (not Archive) |
| 7 | `Archive` action (not Delete) with soft-delete + restore | ⚠️ PARTIAL — Archive/Restore endpoints exist (T-R44 code shipped) but UI still says `Delete` |
| 8 | **Footer copy** `"Archive" hides a category but keeps its history; archived categories are restorable. System categories cannot be edited.` | ❌ MISSING |
| 9 | **System group row visual**: `RECONCILIATION (SYSTEM) · ±ADJUST · locked` | ⚠️ PARTIAL — current shows `Reconciliation (system)` + `ADJUSTMENT` pill but no `locked` affordance |
| 10 | FAB visible | 🐛 L-05 |

## `/settings` — Currency & FX tab

Handoff did not design this surface. T-R36 is still ◻ in `tasks.md`. Current tab panel is a placeholder.

| Element | Status |
|---|---|
| Tab reachable, shell renders | ✅ |
| Panel content | ❌ MISSING (expected: read-only FX cache + base currency + timezone display per T-R36 placeholder) |

## `/settings` — Preferences tab

Same as above. T-R37 ◻. Mirror link to income-anchor control on Categories.

| Element | Status |
|---|---|
| Tab reachable | ✅ |
| Panel content | ❌ MISSING (expected: mirror link to income-anchor + any other prefs) |

---

## Overlay: Add entry (mock `overlay-2e-add-fixed.png` + `overlay-1l-add-formula.png`)

Triggered by `+ Add` on `/today` (and `+ Planned entry` / `+ Recurring rule` on respective Ledger tabs). **Three separate overlays, not one unified entry.**

| # | Element | Status |
|---|---|---|
| 11 | **Overlay opens via HTMX from host page** | ✅ (direct URL to `/transactions/new`, `/planned/new`, `/recurring/new` is bare partial — **B-03**) |
| 12 | **`Happened / Planned / Repeats` segmented tabs** inside overlay | ❌ MISSING — three separate forms exist instead; no unified tab UI |
| 13 | **Category combobox renders pill + direction badge preview** | ❌ MISSING — current uses native `<select>` with no pill preview |
| 14 | **`Fixed value / Formula ƒ` toggle on Amount row** | ❌ MISSING on `/transactions/new`; partial on `/recurring/new` (radio buttons `Fixed · Formula (linear combination of other rules)`) |
| 15 | **Large serif amount display** (`32.00 PLN`) with per-day preview `leaves 187.87 / day after this` | ❌ MISSING — plain `number` input |
| 16 | **Formula editor rows** (`sign · source rule · coefficient % · resulting value`) + `+ Add term` + live `result = ...` | ❌ MISSING — `/recurring/new` just has an Amount text input even when Formula radio selected |
| 17 | **Transit `From / To` fields** reveal only when Transit category chosen | ⚠️ PARTIAL — `Dest (transit)` field always rendered on `/transactions/new`, not conditionally |
| 18 | **`save and add another` footer button** on the left | ❌ MISSING |
| 19 | Primary button labelled `Save ↩` | ⚠️ PARTIAL — reads `Save` (no `↩` glyph) |

See **F-04** for the unified-add-entry gap.

## Overlay: Create account (mock `overlay-2c-create-account.png`) — T-R65 ✅

| # | Element | Status |
|---|---|---|
| 20 | Opens via `+ New account` button HTMX → `#modal-root` | ✅ |
| 21 | Name / Currency / Type fields | ✅ |
| 22 | Opening balance + As-of date | ✅ |
| 23 | **Toggle switch** `This is a liability` | ⚠️ PARTIAL — present as checkbox (per `create_account_form_validate` probe, selector didn't match toggle role=switch). May render as checkbox not a styled toggle switch. |
| 24 | **Credit limit field** rendered only when liability toggle is on | not verified end-to-end — form fill probe failed due to selector; needs manual re-check |
| 25 | `Create account ↩` primary button | ⚠️ PARTIAL — primary button exists with label `Create account` (no `↩` glyph) |

## Overlay: Create category (mock `overlay-2d-create-category.png`) — T-R66 ✅

| # | Element | Status |
|---|---|---|
| 26 | Opens via `+ New category` HTMX | ✅ |
| 27 | Name input | ✅ |
| 28 | **Direction segmented** `↓ Expense / ↑ Income` | ⚠️ PARTIAL — renders but as radio buttons, not a segmented control |
| 29 | **Colour swatches** (`Use direction colour` + 10 coloured circles) | ⚠️ PARTIAL — swatches present but render as `<input type=radio>` + `Pick #hex` text labels in bare partial; styled version only appears via HTMX in-shell render |
| 30 | **Live preview card** (`PREVIEW · [pill] · [direction badge]`) | ⚠️ PARTIAL — only text preview, no styled card chrome |
| 31 | `Create category ↩` button | ⚠️ PARTIAL — plain `Create category` label |
