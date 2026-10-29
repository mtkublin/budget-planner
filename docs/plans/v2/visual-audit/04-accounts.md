# 04 · Accounts

## `/accounts` — desktop (mock `desktop-1j-accounts.png`)

Closest-to-mock of all current screens. Net worth hero, Assets/Liabilities split, trend sparkline column, last-checked column, txns count, balance, Reconcile button, and ⋯ menu are all present.

| # | Delta | Status |
|---|---|---|
| 1 | **Last-checked column renders relative "today / 14 Oct / 14 days ago / 3 Oct"** with coloured chip (green `today`, amber `14 days ago` warning). Current shows absolute `01 Apr` / `01 Jul` dates in a neutral chip. | ✅ `T-R42` (last-checked endpoint) + `T-R34` (display) |
| 2 | **Sort order: by balance, assets first, liabilities last.** Current sorts alphabetically. | 📎 `T-R34` / service helper (weak — `missing-from-plan.md §5.8`) |
| 3 | **Credit-card row shows inline `Limit 20,000 · Available 16,145 · Used 19%` bar** below the row. Current renders the LIABILITY pill but no utilisation bar. | 📎 `T-R34` (weak — `missing-from-plan.md §5.7`) |
| 4 | **Snapshot action removed from the row** (merged into Reconcile slide-over as "Previous checks" + "Also save a snapshot" checkbox). Current ⋯ menu still exposes Snapshot per `T-R67`. | 📎 `T-R34` + `T-R39` (weak — `missing-from-plan.md §5.5`) |
| 5 | **Sparklines render for every account**, including investment accounts. Current sparklines render for accounts with transactions; IKE / IKZE / lokata 6,5% show just a flat line (potentially correct — flat balances — but worth confirming vs mock which also shows minimal shapes). | ✅ `T-R68` (sparkline helper + Accounts trend column) |
| 6 | **Explanatory footnote** at the bottom explaining Checked semantics + where snapshots live. Current renders a shorter copy ("Checked" shows when the balance was last compared with the bank. Snapshots live inside the reconcile panel instead of a collapsed list per card.) ✓ roughly matches. | ✅ shipped |
| 7 | **Transit-heavy balance** (`osobiste` 83 txns) renders a complex sparkline shape ✓. | ✅ shipped |
| 8 | **"+ New account" button in top header, Rising Dough primary style** ✓. | ✅ `T-R65` |

## `/accounts` — mobile (mock `mobile-1s-accounts.png`)

Current `mobile__accounts.png` has serious layout bugs; see also [08-bugs.md](08-bugs.md).

| # | Delta | Status |
|---|---|---|
| 9 | **Bottom tab bar** (Today · Ledger · `+` · Plan · Accounts). Current renders tab labels floating mid-page over row content. | 🐛 **B-03** + ✅ `T-R51` |
| 10 | **Hero + Assets/Liabilities stacked**, not side-by-side. Current overlaps 52,748.21 with the Assets number. | 🐛 **B-04** + ✅ `T-R51` |
| 11 | **Credit-card LIABILITY pill wraps on its own line**. Current clips off right edge. | 🐛 **B-05** + ✅ `T-R51` |
| 12 | **FAB removed on mobile** in favour of centre `+` in the tab bar. Current FAB overlaps row content mid-screen. | 🐛 **B-02** + ✅ `T-R51` + `T-R58` |
| 13 | **Row shape**: account name wraps intact ✓; trend sparkline present ✓; relative checked chip; txn count hidden on narrow (per handoff `03` §Accounts "mobile 1s" shows txn count dropped). | ✅ `T-R51` + `T-R34` |
