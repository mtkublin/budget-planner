# 08 · Bugs

Spotted while auditing. All seven are current-code defects, not design deltas. File each as its own ticket (ideally one PR per fix).

## <a id="b-01"></a>B-01 · Direct URL navigation to overlay routes renders bare partial

**Severity**: HIGH — breaks share links / refresh / open-in-new-tab for every reskinned overlay. Also surfaces as "T-R65 / T-R66 / T-R39 shipped but direct URL still looks like v1" during QA.

**Routes affected**:
- `GET /accounts/new`
- `GET /categories/new`
- `GET /transactions/new`
- `GET /recurring/new`
- `GET /accounts/{id}/reconcile`

**Reproduction**:
```sh
curl -s http://127.0.0.1:8000/accounts/new | head -5
# <div class="slide-over-root"
#      role="dialog"
#      aria-modal="true"
# ...
```

Response is a raw `partials/_slideover.html` fragment — no `<!DOCTYPE html>`, no `<head>`, no stylesheet imports. Browser direct-navigation renders the markup with user-agent defaults.

**Root cause**: router handlers return `partials/_slideover.html` directly (see `src/budget_planner/web/routers/accounts.py:120-132` for the pattern). The template is a fragment with no shell inheritance. It is designed to be swapped into `#modal-root` via HTMX from the host route, where the host already has `base.html` loaded.

**Fix hint**: branch on `HX-Request` header. When present, return the fragment as today. When absent, either (a) render the host route (`/accounts`, `/categories`, …) with an auto-opened overlay via a server-rendered `data-open-overlay` attribute, or (b) 302 to the host route carrying an `?overlay=new` query param that the host route handler reads and renders accordingly. Pattern already partially established via `hx-target="#modal-root"` on the trigger links.

**Why it slipped through**: audits that always launched the overlay from the host page (clicking `+ New account`) never hit the direct-URL path. The frontend-visual-audit skill in this repo hits the URL directly, which is how the bug surfaces.

---

## <a id="b-02"></a>B-02 · Mobile FAB overlays table rows on `/accounts`

**Severity**: MEDIUM.

Current FAB sits mid-viewport on `/accounts` at 375 px and covers the `fundusz konserwatyny (mBank)` row. Container likely uses `position: absolute` relative to a non-scrolling ancestor rather than `position: fixed; bottom: env(safe-area-inset-bottom, 0)`.

**Fix hint**: `.rd-fab { position: fixed; right: 1rem; bottom: calc(1rem + env(safe-area-inset-bottom, 0)); }` or similar. Also check `z-index` so it stays above the (future) bottom tab bar — or remove the FAB on mobile outright per `T-R58`.

**Note**: `T-R58` already schedules FAB removal in Phase 7, but the position bug is live today and masks row content.

---

## <a id="b-03"></a>B-03 · Mobile nav labels float mid-content on `/accounts` and `/plan?tab=budget`

**Severity**: HIGH.

At 375 px, the Rising Dough bottom tab bar (`Today · Ledger · + · Plan · Accounts`) renders in document flow halfway down the page instead of fixed to the viewport bottom. Nav labels overlap table rows. See `/tmp/fe-audit/mobile__accounts.png` and `/tmp/fe-audit/mobile__plan-budget.png`.

**Fix hint**: likely a missing `@media (max-width: 640px)` block in `rising-dough.css` for `.rd-rail__footer` or `.rd-nav`. Should become `position: fixed; left: 0; right: 0; bottom: 0; z-index: 20;` on narrow screens, with content gaining `padding-bottom` equal to the bar height.

---

## <a id="b-04"></a>B-04 · Mobile `/accounts` net worth hero overlaps ASSETS column

**Severity**: MEDIUM.

Hero `52,748.21` and the right-side `ASSETS 56,603.21` column live in the same flex row with no `flex-wrap`. At 375 px they overlap and both become unreadable.

**Fix hint**: wrap the Assets/Liabilities meta into a `display: grid` / `flex-wrap: wrap` block that stacks under the hero at narrow widths.

---

## <a id="b-05"></a>B-05 · Mobile `/accounts` credit-card LIABILITY pill clips off right edge

**Severity**: MEDIUM.

Pill is horizontally positioned past viewport width on the `karta kredytowa (mBank)` row at 375 px. Likely inline-flex with no wrap on the account-row header.

**Fix hint**: allow the pill cluster to wrap under the account name on narrow widths (`flex-wrap: wrap` on the row header, pill becomes block on `max-width: 640px`).

---

## <a id="b-06"></a>B-06 · `/plan?tab=budget` mobile tab strip truncates "Forecast"

**Severity**: LOW–MEDIUM.

Four Plan tabs (`Budget · Year · Forecast · Analytics`) overflow the 375 px viewport. Fourth tab bleeds mid-word with no fade/scroll indicator.

**Fix hint**: `.plan-tabs { overflow-x: auto; scroll-snap-type: x mandatory; }` + each tab `scroll-snap-align: start`. Add `mask-image: linear-gradient(to right, #000 85%, transparent)` for the fade. `T-R55` covers Settings tab-bar scroll but not Plan — add a bullet or widen `T-R55` scope.

---

## <a id="b-07"></a>B-07 · `/` still serves legacy "Overview" dashboard

**Severity**: MEDIUM.

Hitting `/` renders `templates/home/overview.html` with `<title>Overview · Budget Planner</title>`. `T-R06` plans a 302 redirect from `/` to `/today`, and `T-R05` plans the product rename. Both are still ◻. The current `/` page also includes Upcoming widgetry (with `+ Planned`, `+ Recurring`, Promote/Skip/Override actions) that *should* live on `/today` instead.

**Also**: `grep "Budget Planner" src/budget_planner/web/templates` currently returns live hits (at minimum the `/` page title derives from the base template fallback), which would cause `T-R05` acceptance (`grep "Budget Planner" src/budget_planner/web/templates returns zero live hits`) to fail. Confirm before marking `T-R05` done.

**Fix hint**: land `T-R05` + `T-R06` as a bundle. Delete `templates/home/overview.html` or point `GET /` to a 302 `RedirectResponse("/today")`.
