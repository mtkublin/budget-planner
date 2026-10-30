# 02 · Information architecture (screen 1c)

## Navigation
Today · Ledger · Plan · Accounts, with Settings pinned at the bottom. Keys: `g o` Today, `g l` Ledger, `g p` Plan, `g a` Accounts, `g s` Settings. (The old `g b` and `g f` can alias to Plan.)

| Old | New | Reason |
|---|---|---|
| Overview | **Today** | Leads with "left per day" and a can-I-afford check; upcoming items carry inline actions. |
| Ledger + Transactions | **Ledger** | Same list and filters; bulk actions and export appear as a toolbar when rows are selected. |
| Budget + Forecast | **Plan** (tabs: Budget · Year · Forecast · Analytics) | Both answer "how will the period go"; they share the paycheck period header. |
| Accounts | **Accounts** | Stays. Today shows a compact net worth card with a link. |
| Settings drawer | **Settings page** | Categories need room for colour and archive; add/edit stay as modals. |

## Decisions on the brief's open questions (§8)
1. **Surfaces:** five places, one question each (see 1c).
2. **Quick add:** persistent **+ Add** in the top bar, `n` anywhere, ⌘K action. Mobile: centre tab. The floating button is removed (it covered table content).
3. **Planned vs recurring:** still two concepts and two Ledger tabs, but **Upcoming** on Today lists them together with one action set (Promote, Skip, Override).
4. **Paycheck window:** a visible one-liner, "Period 15 Oct → 7 Nov · day 14 of 24", under the hero and in the Plan header with a link to change the anchor.
5. **Settings:** a page with tabs Categories · Currency & FX · Preferences. The income anchor is the first control on Categories.
6. **Yearly grid:** a heatmap with a tier legend and inline edit (see 03 · 1h). Mobile uses per-category cards.
