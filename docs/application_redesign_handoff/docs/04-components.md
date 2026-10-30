# 04 · Components (screen 1b)

| Component | Spec |
|---|---|
| **Amount** | Plex Mono, tabular. Sign: − for expense, + for income, none for transit. Currency suffix muted 0.72em. Income green, negative balances expense red. ƒ chip when formula-derived. Foreign amounts show base-currency equivalent and rate: "≈ 412.10 PLN · 1 EUR = 4.2936 (28 Oct)". |
| **Category pill** | Uppercase 10.5px/600, round, tinted from category hue. |
| **Direction badge** | Glyph + label: ↓ Expense, ↑ Income, ⇄ Transit, ± Adjust. 4px radius. |
| **Pace tag** | ● On track (green), ▲ Tight (amber), ! N overdue (solid red, white text). |
| **Overdue chip / row** | Solid red chip "N days late"; row tinted expense-soft. |
| **Buttons** | Primary (accent fill), default (hairline), ghost (text), small variant. Shortcut hint as `kbd` inside. |
| **Segmented control** | Tabs and switches; active = ink fill. |
| **Filter row** | Chips: date range, category, account, direction, search with `/` hint. |
| **Table row** | Grid row, hairline divider, inline actions right-aligned; actions visible on focus and hover, always visible on touch. |
| **Overlays** | Slide-over (reconcile), modal (add, create), popover (cell edit, row menu), palette. Topmost handles Esc. |
| **Form controls** | Text, amount (decimal point preserved while typing), date, account/category combobox, toggle, term row (sign · source · % · value). |
| **Heatmap cell** | 34px tall, colour by value, tier marker per 03 · Year. |
| **Progress bar** | 6–10px, hairline track; segmented variant for spent / committed / left (committed uses diagonal hatch). |
| **Add** | Top-bar button (desktop), centre tab (mobile). Replaces the floating action button. |
