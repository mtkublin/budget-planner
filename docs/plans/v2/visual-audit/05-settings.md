# 05 · Settings

## `/settings` — Categories tab (mock `desktop-1n-settings-categories.png`)

Current shell + tabs row ✓. Everything inside the Categories panel is still v1 shape.

| # | Delta | Status |
|---|---|---|
| 1 | **Income anchor selector pinned at the top** (`Income anchor · starts each paycheck window → WYPŁATA`). Current absent. | ✅ `T-R35` + `T-R37` (mirror link) |
| 2 | **Grouped sections `Expense (16)` / `Income (6)` / `System (read-only)`**. Current renders a flat alphabetical list; locked system rows (Reconciliation, Transit) sit mid-list without a group heading. | ✅ `T-R35` |
| 3 | **Row shape**: pill + direction badge + colour source indicator (`Direction default`, `Override · magenta`, `Override · cyan`) + `Edit · Archive`. Current = pill + direction + `Edit · Delete`. | ✅ `T-R35` + 📎 colour source as "swatch + Override · {colour name}" (weak — `missing-from-plan.md §7.4`) |
| 4 | **Archive affordance** (not Delete). Archived rows still restorable. | ✅ `T-R35` + `T-R44` (archive/restore endpoints) |
| 5 | **Footer copy** at bottom: *"Archive" hides a category but keeps its history; archived categories are restorable. System categories cannot be edited.* Current absent. | ✅ `T-R35` |
| 6 | **System group** shows `RECONCILIATION (SYSTEM) · ±ADJUST · Direction default · locked` + `TRANSIT · ↹ TRANSIT · Direction default · locked`. Current renders them inline with `(system)` suffix on the name but same table shape. | ✅ `T-R35` |

## `/settings` — Currency & FX tab (handoff: minimal)

Current tab renders but content not yet designed (per handoff). `T-R36` scopes a read-only FX cache + base currency / timezone display. No design mock in `screenshots/`.

| # | Delta | Status |
|---|---|---|
| 7 | Tab reachable ✓, panel not yet reskinned. | ✅ `T-R36` (ships placeholder-grade per `missing-from-plan.md §7.7`) |

## `/settings` — Preferences tab (handoff: minimal)

Mirror link to income-anchor control from Categories tab. No design mock.

| # | Delta | Status |
|---|---|---|
| 8 | Tab reachable ✓, panel not yet reskinned. | ✅ `T-R37` (placeholder per `missing-from-plan.md §7.7`) |
