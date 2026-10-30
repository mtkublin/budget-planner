# 05 · Accounts

## `/accounts` — desktop (mock `desktop-1j-accounts.png`)

| # | Element | Status |
|---|---|---|
| 1 | Shell + eyebrow `ACCOUNTS · 10` + title `Net worth` | ✅ |
| 2 | `+ New account` button in top right (opens overlay via HTMX) | ✅ |
| 3 | Hero `52,748.21 PLN` + `ASSETS 56,603.21` + `LIABILITIES 3,855.00` | ✅ |
| 4 | Explanatory copy `All balances in base currency PLN. No FX conversions needed today.` | ✅ |
| 5 | Columns `ACCOUNT · TREND · CHECKED · TXNS · BALANCE · Reconcile · ⋮` | ✅ |
| 6 | Rows with name + type stacked (`IKE (mBank) · investment`) | ✅ |
| 7 | **Sparklines in TREND column** (T-R68) | ✅ renders — IKE / IKZE / lokata 6,5% show single-value flat (expected for low-txn accounts) |
| 8 | **CHECKED column shows relative `today / 14 Oct / 14 days ago / 3 Oct`** with coloured chip (green `today`, amber `14 days ago` warning) | ❌ MISSING — current renders absolute `01 Apr` / `01 Jul` / `01 Sep` in neutral chips |
| 9 | **Sort order: by balance, assets first, liability last** | ⚠️ PARTIAL — current sorts alphabetically |
| 10 | **Credit-card row inline bar** `Limit 20,000 · Available 16,145 · Used 19%` under the row | ❌ MISSING — current shows the `CREDIT CARD · LIABILITY` pill but no utilisation bar |
| 11 | Credit-card balance in red (`−3,855.00 PLN`) | ✅ |
| 12 | `⋮` kebab per row opens popover with `Edit · Snapshot · Delete` (T-R67 ✅) | ✅ verified via probe |
| 13 | **Snapshot action should move INTO Reconcile slide-over** (per `missing-from-plan.md §5.5`) and drop from the row ⋯ | ⚠️ PARTIAL — Snapshot still in kebab; Reconcile missing the `Also save snapshot` checkbox (**F-03**) |
| 14 | Footer: `"Checked" shows when the balance was last compared with the bank. Snapshots live inside the reconcile panel instead of a collapsed list per card.` | ✅ copy matches |
| 15 | FAB visible | 🐛 L-05 |

## Reconcile slide-over (opened via Reconcile button on each row — mock `overlay-1k-reconcile.png`)

Opened via HTMX swap into `#modal-root`. Renders Rising Dough chrome ✓ (improvement over first audit where direct URL was still bare — see **B-03** for the direct-URL case).

| # | Element | Status |
|---|---|---|
| 16 | Slide-over shell + eyebrow `RECONCILE` + title (e.g. `IKE (mBank)`) + `Esc` chip | ✅ |
| 17 | **Three-step chip row** `① Open your bank · ② Enter its balance · ③ Review` | ✅ (verified via probe) |
| 18 | Explainer `Compare this account with your bank...` | ✅ |
| 19 | **Side-by-side columns** `RISING DOUGH SAYS X` vs `YOUR BANK SAYS Y` | ✅ (both labels present per probe) |
| 20 | Yellow **Difference callout** | ✅ (`difference_callout: true`) |
| 21 | **`Record as` category selector** (default `±ADJUST Reconciliation (system)`, any category allowed) | ❌ MISSING — see **F-03** |
| 22 | **`Also save a balance snapshot` checkbox** | ❌ MISSING — see **F-03** |
| 23 | **`PREVIOUS CHECKS` list** (sourced from snapshots + prior reconciles) | ✅ renders (`01 Apr / 01 May / 01 Jun / 01 Jul / 01 Aug`) |
| 24 | **Primary button states signed amount** `Record −28.90 ↩` | not verifiable — bank input selector didn't match in probe (`bank_input_present: false`). Could be present with a different name attribute. |
| 25 | `Cancel` secondary button | not verified |

## Kebab ⋯ menu actions on each row (T-R67 ✅)

| # | Action | Behaviour | Status |
|---|---|---|---|
| 26 | `Edit` | `hx-get /accounts/{id}/edit → #modal-root` | ✅ opens overlay via HTMX |
| 27 | `Snapshot` | `hx-post /accounts/{id}/snapshot swap=none` | fires silently; no feedback. **Missing toast** (`T-R61` toast macro exists in `/dev/components`, no proof it's wired here). |
| 28 | `Delete` | `hx-post /accounts/{id}/delete target=#account-{id} swap=outerHTML` | ⚠️ PARTIAL — no `hx-confirm` observed. Account delete is destructive — needs confirm prompt or undo toast. Not probed. |
