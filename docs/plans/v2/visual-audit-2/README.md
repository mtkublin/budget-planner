# Rising Dough — Visual + Functional Audit v2 (2026-10-29)

> Full-sweep re-audit assuming "all tasks done" per upstream claim. Every deviation from the handoff mockups and every broken interaction is listed below.
> Captured with Playwright at desktop 1440 · tablet 1024 · mobile 375, plus scripted interaction probes (click overlays, kebab menus, cell clicks, form fills, keyboard shortcuts, 404 scan).

Artifacts: `/tmp/fe-audit/` — baseline screenshots, probe screenshots, probe JSON, enumerated-controls JSON per route. DB snapshot preserved at `/tmp/fe-audit/budget-pre-audit.sqlite`.

## File index

| File | Scope |
|---|---|
| [`00-summary.md`](00-summary.md) | Headline totals, broken-feature shortlist, delta shortlist. |
| [`01-bugs-blocking.md`](01-bugs-blocking.md) | Dead endpoints, broken interactions, failing shortcuts. |
| [`02-today.md`](02-today.md) | /today + /dev/components + home. |
| [`03-ledger.md`](03-ledger.md) | Actual · Planned · Recurring · Recently deleted · Bulk toolbar. |
| [`04-plan.md`](04-plan.md) | Budget · Year · Forecast · Analytics. |
| [`05-accounts.md`](05-accounts.md) | Accounts table + ⋮ kebab + Reconcile. |
| [`06-settings-and-overlays.md`](06-settings-and-overlays.md) | Settings tabs + Add entry / Create account / Create category overlays. |
| [`07-mobile.md`](07-mobile.md) | Mobile tab bar, bottom sheets, tap targets, overlap bugs. |

## Audit scope executed

| Pass | Count | Notes |
|---|---|---|
| Baseline screenshots | 15 routes × 3 viewports = **45 shots** | Every GET route, D/T/M. |
| Enumerated controls | **10 routes × desktop** | Lists every button/link/input/form with hx-* attrs. Walks safe-to-fill inputs. Clicks safe-to-click buttons. |
| Scripted interaction probes | **18 desktop + 3 mobile** | Overlay opens, kebab menus, cell click, form fills, keyboard shortcuts, 404 scan on all override hrefs, overlay chrome checks. |
| 404 scan | **26 unique hrefs on /plan?tab=budget** | 16 of them 404 (every override link). |

All 45 baseline requests returned HTTP 200. Zero console errors on baseline sweep. Overflow signals concentrated on mobile; see `07-mobile.md`.

## Legend

| Tag | Meaning |
|---|---|
| 🐛 **BLOCKING** | Hard-broken feature (404, dead click, missing endpoint). |
| 🐛 **FUNCTIONAL** | Interaction fires but wrong outcome (full nav instead of inline, missing control). |
| 🐛 **LAYOUT** | Overlap / clipping / wrong responsive behaviour. |
| ❌ **MISSING** | Design element from mock absent from current render. |
| ⚠️ **PARTIAL** | Element present but doesn't match mock shape (wrong label, order, colour, grouping). |
| ✅ | Matches mock. |
