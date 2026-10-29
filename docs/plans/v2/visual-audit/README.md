# Rising Dough — v2 Visual Audit (2026-10-29)

> Full-sweep comparison of the running app at `http://127.0.0.1:8000` against the design mockups in `docs/application_redesign_handoff/mockups/screenshots/`.
> Captured with Playwright at **desktop 1440 · tablet 1024 · mobile 375**; artifacts under `/tmp/fe-audit/`.
> Diagnostic signals in `/tmp/fe-audit/summary.json`.

Only four Phase-3 tasks have shipped so far: **T-R39, T-R65, T-R66, T-R67**. Phases 1 / 2 / 4 / 5 / 6 are still open. Many deltas below are therefore *expected* and already captured in `tasks.md` — they are listed here to confirm scope, not to re-plan work. The useful signal is the **UNCOVERED** and **🐛 BUG** rows.

---

## Legend

| Tag | Meaning |
|---|---|
| ✅ `T-R##` | Delta explicitly captured in a task file. |
| 📎 `T-R##` (weak) | Host task exists; sub-item was flagged in `missing-from-plan.md` and still needs absorption. |
| ❓ **UNCOVERED** | No task or missing-from-plan row references this delta. Needs a plan edit. |
| 🐛 **BUG** | Current code regression / defect, not a design delta. File + fix hint attached. |

## File index

| File | Scope |
|---|---|
| [`00-summary.md`](00-summary.md) | Counts, highest-signal findings, shortlist of UNCOVERED items + bugs. |
| [`01-today-and-home.md`](01-today-and-home.md) | `/today` desktop + mobile; `/` legacy Overview that still ships. |
| [`02-ledger.md`](02-ledger.md) | `/ledger?view=actual \| planned \| recurring`. |
| [`03-plan.md`](03-plan.md) | `/plan?tab=budget \| year \| forecast \| analytics`. |
| [`04-accounts.md`](04-accounts.md) | `/accounts` desktop + mobile. |
| [`05-settings.md`](05-settings.md) | `/settings` (Categories / Currency & FX / Preferences tabs). |
| [`06-overlays.md`](06-overlays.md) | Reconcile, Add entry (fixed / formula), Create account, Create category, New recurring. |
| [`07-mobile-and-tablet.md`](07-mobile-and-tablet.md) | Shell-wide responsive findings + overflow table. |
| [`08-bugs.md`](08-bugs.md) | Bugs spotted while auditing (not design deltas). |

---

## Routes screenshotted

17 routes × 3 viewports = 51 screenshots. All returned HTTP 200. Zero console errors across the full sweep.

```text
/                       /today                  /ledger?view=actual
/ledger?view=planned    /ledger?view=recurring  /plan?tab=budget
/plan?tab=year          /plan?tab=forecast      /plan?tab=analytics
/accounts               /settings               /transactions/new
/accounts/new           /categories/new         /recurring/new
/accounts/1/reconcile   /dev/components
```

## Overflow signals (`overflowingElements > 0`)

| Route | tablet | mobile |
|---|:-:|:-:|
| `/today` | 0 | **20** |
| `/ledger?view=actual` | **20** | **20** |
| `/ledger?view=planned` | **5** | **9** |
| `/ledger?view=recurring` | **20** | **20** |
| `/plan?tab=budget` | 0 | **20** |
| `/plan?tab=year` | **7** | **20** |
| `/plan?tab=forecast` | 0 | **7** |
| `/plan?tab=analytics` | 0 | **5** |
| `/accounts` | 0 | **20** |

Desktop is clean at 1440. All responsive breakage is Phase 6 territory (`T-R51..T-R56`), but note the per-screen bugs in [`08-bugs.md`](08-bugs.md) that compound it.
