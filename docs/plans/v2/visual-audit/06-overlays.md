# 06 · Overlays

Every overlay below was captured by **direct URL navigation** (not HTMX swap into the host page). All five currently return a bare partial without the Rising Dough chrome — see [bug B-01](08-bugs.md#b-01). The design deltas below are therefore relative to the mock *content* only; the shell + close affordance deltas are a bug, not a redesign gap.

Routes checked: `/accounts/new`, `/categories/new`, `/transactions/new`, `/recurring/new`, `/accounts/1/reconcile`.

## Reconcile — `/accounts/{id}/reconcile` (mock `overlay-1k-reconcile.png`) — host `T-R39` ✅

| # | Delta | Status |
|---|---|---|
| 1 | **Slide-over shell** with `RECONCILE` eyebrow + `osobiste (mBank)` title + Esc chip. Current renders bare partial on direct URL. | 🐛 **B-01** |
| 2 | **Three-step chip row** `① Open your bank · ② Enter its balance · ③ Review`. Current renders as ordered list (unstyled). | ✅ `T-R39` (shipped — likely only within overlay context) |
| 3 | **Side-by-side bank/app columns** (`RISING DOUGH SAYS 4,731.08` vs `YOUR BANK SAYS 4,702.18`). Current stacks them. | ✅ `T-R39` |
| 4 | **Yellow "Difference" callout** with signed amount + explanatory sentence. Current absent. | ✅ `T-R39` |
| 5 | **"Record as" category combobox** (default `±ADJUST Reconciliation (system)`, any category allowed). Current absent. | 📎 `T-R39` (weak — `missing-from-plan.md §5.14`) |
| 6 | **"Also save a balance snapshot" checkbox.** Current absent. | 📎 `T-R39` (weak — `missing-from-plan.md §5.15`) |
| 7 | **"Previous checks" list** `14 Oct · 4,980.12 / 30 Sep · 3,412.50`. Current renders a `Previous checks` ul but with unstyled dates (`01 Apr 13,687.47` etc.). | 📎 `T-R39` (weak — `missing-from-plan.md §5.16`) |
| 8 | **Primary button states the signed amount**: `Record −28.90 ↩`. Current renders `Record`. | ✅ `T-R39` (shipped per task line) |

## Add entry (fixed) — `/transactions/new` (mock `overlay-2e-add-fixed.png`) — host `T-R38` ◻

| # | Delta | Status |
|---|---|---|
| 9 | **Slide-over shell + "New entry" title + Esc chip**. Current renders bare partial. | 🐛 **B-01** |
| 10 | **Happened / Planned / Repeats segmented** at the top (currently these are separate URLs: `/transactions/new`, `/planned/new`, `/recurring/new`). | ✅ `T-R38` |
| 11 | **Category combobox renders pill + derived direction badge** (`TAKEAWAY · ↓ EXPENSE`). Current renders native select with no pill preview. | ✅ `T-R38` + `T-R12` + `T-R13` |
| 12 | **Fixed value / Formula ƒ toggle** on the Amount row (mock 1l shows the formula editor on the alternate state). Current `/transactions/new` has no toggle; the formula path lives on `/recurring/new`. | ✅ `T-R38` (unified add) |
| 13 | **Large amount display** (`32.00 PLN`) + **"leaves 187.87 / day after this"** per-day impact. Current renders a plain number input. | ✅ `T-R38` + `T-R40` |
| 14 | **"save and add another" footer button** on the left. Current absent. | ✅ `T-R38` |
| 15 | **Dest (transit) field** only appears when the Transit category is chosen. Current renders `Dest (transit)` field unconditionally. | ✅ `T-R38` |

## Add entry (formula) — `/recurring/new` (mock `overlay-1l-add-formula.png`) — host `T-R38` ◻

| # | Delta | Status |
|---|---|---|
| 16 | **Formula term rows** (`sign · source rule · coefficient % · resulting value`) with `+ Add term` + **live result**. Current has `Fixed / Formula (linear combination of other rules)` radios + a plain Amount input — no term editor. | ✅ `T-R38` + `T-R41` (formula preview endpoint) |
| 17 | **Cycle + non-positive-result guard copy** inline. Current absent. | ✅ `T-R41` |
| 18 | **NEXT DUE + CADENCE** side-by-side at the bottom. Current renders Cadence + Start separately at the top; no Next-due picker. | ✅ `T-R38` |

## Create account — `/accounts/new` (mock `overlay-2c-create-account.png`) — host `T-R65` ✅

| # | Delta | Status |
|---|---|---|
| 19 | **Shell** (slide-over, Esc chip, Rising Dough chrome). Current renders bare partial on direct URL. | 🐛 **B-01** |
| 20 | **NAME · CURRENCY · TYPE** in grid; CURRENCY is a filterable combobox (immutable, stated). Current renders native select with placeholder "Type to filter ISO code…" ✓ via `_slideover.html`, but direct-URL view is unstyled. | ✅ `T-R65` (shipped within overlay) |
| 21 | **Large toggle switch for "This is a liability"**. Current renders a plain checkbox. | ✅ `T-R65` (shipped) |
| 22 | **Credit limit field** rendered only when toggle is on (`aria-hidden` + disabled otherwise per ADR-0030 §6). Current always-hidden credit_limit input (not visible in bare partial). | ✅ `T-R65` |
| 23 | **"Create account ↩" primary button** at bottom right. Current renders bare `Create account`. | ✅ `T-R65` |

## Create category — `/categories/new` (mock `overlay-2d-create-category.png`) — host `T-R66` ✅

| # | Delta | Status |
|---|---|---|
| 24 | **Shell + Esc chip**. Current renders bare partial on direct URL. | 🐛 **B-01** |
| 25 | **Direction segmented ↓ Expense / ↑ Income**. Current renders two radio buttons inline. | ✅ `T-R66` (shipped — segmented macro) |
| 26 | **Colour row = `Use direction colour` chip + 10 coloured swatches** (circles). Current renders 10 `Pick #hex` radio buttons with no colour preview. | ✅ `T-R66` (shipped — bare partial loses the swatch styling) |
| 27 | **Live preview card** at the bottom (`PREVIEW · [pill] · [direction badge]`). Current renders `Preview name ↓ expense` as plain text. | ✅ `T-R66` |
| 28 | **"Create category ↩" primary button**. Current bare `Create category`. | ✅ `T-R66` |
