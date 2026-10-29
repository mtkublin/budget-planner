# 01 · Bugs — BLOCKING & FUNCTIONAL

Each bug has: ID · severity · reproduction · evidence · suggested fix. All reproductions assume `uvicorn ... --reload --port 8000` running.

---

## <a id="b-01"></a>B-01 · Plan · Budget override feature 100% dead (404)

**Severity**: 🐛 BLOCKING. Primary user action on Plan · Budget unreachable.

**Reproduction**:
```sh
for id in 4 5 6 7 8 9 10 11 12 13 14 15 17 18 21 26; do
  printf '%s %s\n' "/budget/overrides/new?category_id=$id" \
    "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/budget/overrides/new?category_id=$id)"
done
# → every line prints 404
```

Open `/plan?tab=budget`, click any row ⋯ → full-page nav to `/budget/overrides/new?category_id=17` → `{"detail":"Not Found"}`.

**Evidence**: `/tmp/fe-audit/probes2.json` → `actions_links_404_scan./plan?tab=budget` lists all 16 override hrefs returning 404.

**Root cause**: Route handler for `GET /budget/overrides/new` is registered at `src/budget_planner/web/routers/budget.py:165` as `/budget/rules/{category_id}/overrides/new` (path parameter, not query string). The template renders links as `/budget/overrides/new?category_id=X`. URL shape mismatch.

**Fix hint**: either (a) update the row template to generate `/budget/rules/{category_id}/overrides/new`, or (b) add a compatibility route `GET /budget/overrides/new` reading `category_id` from query string. Prefer (a) — one line template change in `src/budget_planner/web/templates/plan/_budget_table.html` (or wherever the kebab is rendered).

---

## <a id="b-02"></a>B-02 · Plan · Year heatmap cells not clickable

**Severity**: 🐛 BLOCKING. Keystone interaction of the Year screen never fires.

**Reproduction**:
1. `GET /plan?tab=year`
2. Count `<td>` cells inside tbody: 246.
3. Count buttons/links/role=button inside those cells: 0.
4. Clicking a cell = no popover, no navigation, no HTMX swap.

**Evidence**: `/tmp/fe-audit/probes2.json` → `year_cell_click` → `cell_td_count: 246, clickable_cells_count: 0`.

**Mock requires**: click a cell → popover with `amount` input + `One-off · {month YYYY} / Every year · {month}` toggle + `Reset to default` + `Save ↩`.

**Fix hint**: `src/budget_planner/web/templates/plan/_year_grid.html` currently renders cells as plain `<td>` text. Change to `<td><button hx-get="/budget/rules/{category_id}/overrides/new?month={m}&year={y}" hx-target="#modal-root">{value}</button>` (and ensure the server-side rule exists — may share the fix path with B-01).

---

## <a id="b-03"></a>B-03 · Direct URL navigation to overlay routes still returns bare partial

**Severity**: 🐛 BLOCKING for shareable links and reload-safe UX. Already filed in previous audit — not fixed.

**Routes affected**:
- `GET /accounts/new` → bare slide-over fragment, no `<html><head>`
- `GET /categories/new` → bare fragment
- `GET /transactions/new` → bare fragment
- `GET /recurring/new` → bare fragment
- `GET /accounts/{id}/reconcile` → bare fragment
- `GET /planned/{id}/edit` → bare fragment (not verified this pass; same pattern)
- `GET /recurring/{id}/edit` → bare fragment (same)

**Reproduction**:
```sh
curl -s http://127.0.0.1:8000/accounts/new | head -3
# <div class="slide-over-root"
#      role="dialog"
#      aria-modal="true"
```

**Fix hint**: branch on `HX-Request` header in each `/.../new` handler. When absent → render host route with overlay auto-opened, or 302 to host route with `?open=...` query param that the host template reads.

---

## <a id="f-01"></a>F-01 · Keyboard shortcut `g a` broken

**Severity**: 🐛 FUNCTIONAL.

**Reproduction**: open `/today`, press `g` then `a` within 500 ms. Stays on `/today`.

**Comparison**: `g l` → `/ledger` ✓, `g o` → `/today` ✓ (sameness), `g p` → `/plan` ✓, `g s` → `/settings` ✓. Only `g a` fails.

**Evidence**: `/tmp/fe-audit/probes.json` → `keyboard_g_a` → `accounts_reached: false, url_after: /today`.

**Fix hint**: check `src/budget_planner/web/static/js/shortcuts.js` — likely a missing registration for the `a` key under the `g` chord, or the registered target URL is wrong.

---

## <a id="f-02"></a>F-02 · Today "Promote" row action does full-page navigation

**Severity**: 🐛 FUNCTIONAL. Mock requires inline row expand; current always navigates away.

**Reproduction**: open `/today`, click any `Promote` in Upcoming → `/recurring/21/promote?date=2026-11-01` full page.

**Mock requires**: row expands in place into editable `account | date | amount | Confirm ↩ | Esc`. No modal, no navigation.

**Evidence**: `/tmp/fe-audit/probes2.json` → `today_promote_in_place` → `navigated_away: true, inline_form_appeared: false`.

**Fix hint**: template currently emits `<a href="/recurring/21/promote?date=...">Promote</a>`. Replace with `<button hx-get="/recurring/21/promote/inline" hx-target="closest tr" hx-swap="outerHTML">Promote</button>` and add a `GET /recurring/{id}/promote/inline` fragment handler that returns the editable row.

---

## <a id="f-03"></a>F-03 · Reconcile slide-over missing "Record as" + "Also save a snapshot" controls

**Severity**: 🐛 FUNCTIONAL. Design-complete reconcile UX never ships without these.

**Reproduction**: open `/accounts`, click any `Reconcile` → slide-over opens with eyebrow + title + step chips + "Rising Dough says" + "Previous checks" + "Difference" ✓.

**What's missing**:
- No `Record as` category selector (mock: default `±ADJUST Reconciliation (system)`, any category allowed).
- No `Also save a balance snapshot` checkbox.

**Evidence**: `/tmp/fe-audit/probes2.json` → `reconcile_slideover` → `record_as_label: false, record_as_select: false, snapshot_checkbox: false`.

**Fix hint**: `src/budget_planner/web/templates/partials/accounts/_reconcile_modal.html` — add two form fields and the matching POST handling in `src/budget_planner/web/routers/accounts.py:368` (`reconcile` POST).

---

## <a id="f-04"></a>F-04 · Add entry overlay missing unified Happened/Planned/Repeats + Fixed/Formula + per-day preview

**Severity**: 🐛 FUNCTIONAL. The unified Add entry per handoff is not yet shipped; three separate routes with three different forms exist instead.

**Reproduction**:
- Click `+ Add` on `/today` → opens overlay with the plain `/transactions/new` form (date, amount, category, account, dest-transit, description, Save). No tabs.
- `+ Planned entry` on `/ledger?view=planned` → opens the `/planned/new` form instead.
- `+ Recurring rule` on `/ledger?view=recurring` → opens `/recurring/new` form with its own Fixed/Formula radio + separate layout.

**Mock requires**: single "New entry" overlay with:
1. `Happened / Planned / Repeats` segmented at top.
2. Category combobox (pill + direction badge preview).
3. `Fixed value / Formula ƒ` toggle on Amount row.
4. Large serif amount display with `leaves N / day after this` preview.
5. Formula editor with `+ Add term` + live `result = ...` for the Formula state.
6. `save and add another` footer control.

**Evidence**: `/tmp/fe-audit/enum__desktop__today.json` (buttons=4 inputs=3, no evidence of tab controls); probe `add_entry_overlay` failed to find any of the above controls in the opened overlay.

**Fix hint**: this is actually task **T-R38** which `tasks.md` marks ✅. The reskin shipped the plain form only. Needs: (a) unify the three forms behind one `/add` overlay with a `?when=happened|planned|repeats` initial state, or (b) ship the tab control inside the current `/transactions/new` and have the tabs HTMX-swap the form body.

---

## <a id="f-05"></a>F-05 · Cheatsheet modal renders duplicate "Keyboard shortcuts" section

**Severity**: 🐛 FUNCTIONAL (visual). Press `?` on `/today` → cheatsheet opens but shows two overlapping copies of the "Keyboard shortcuts" heading and tables. The second table displays only `Esc Close`.

**Evidence**: `/tmp/fe-audit/probe__cheatsheet_question_mark.png`.

**Fix hint**: the cheatsheet partial is likely being injected twice. Check if `#modal-root` is rendered more than once in `base.html` or whether `shortcuts.js` registers the open handler on both `?` and `Shift+/` and the browser fires both.
