# 01 · Visual direction (screen 1a)

Editorial / Swiss base from ADR-0023, tightened. Hierarchy comes from type scale and whitespace; colour is reserved for meaning.

## Palette (OKLCH)
See `tokens.css`. Warm neutrals (hue 60–85, chroma ≤ 0.012), one accent (indigo, hue 265), four directional hues with a soft tint each.

| Role | Use |
|---|---|
| Paper / Surface / Sunk | page / cards and inputs / wells, active nav, table-section fills |
| Line | every border (1px hairline) |
| Ink / Mute | primary text / secondary text (5.2:1 on paper) |
| Accent | primary buttons, focus ring, selected row, links |
| Income, Expense, Transit, Adjust | direction badges, signed amounts, pace tags |

**Category pills:** background `oklch(0.94 0.045 H)`, text `oklch(0.4 0.13 H)`, where H is the category override hue or the direction default (expense 28, income 155, transit 230). The direction badge is always shown separately.

## Type
- **Newsreader** (400/500): page titles, section titles, the hero figure, account names. Use `font-feature-settings:'lnum','tnum'` on figures.
- **Hanken Grotesk** (400/500/600): body, labels, buttons. Eyebrows: 11px / 600 / +0.13em / uppercase.
- **IBM Plex Mono** (400/500/600): every amount, date and key hint. `font-variant-numeric: tabular-nums`. Currency code is a muted suffix at 0.72em.
- Scale: hero 96/76 (mobile) · H1 40 · H2 22 · body 14 · small 12–12.5 · eyebrow 11.
Self-host as variable woff2.

## Elevation and shape
Hairlines over shadows. Cards 10px radius, controls 6px, pills round. One shadow only, for overlays: `--shadow-overlay`. Focus ring: 2px accent with 2px paper offset.

## Motion
120–180ms ease-out, state changes only: promoted row collapses and its amount moves into "spent"; hero number counts to its new value; overlays rise 8px and fade. Disable all under `prefers-reduced-motion`.

## Contrast
Body 15:1, muted 5.2:1, pills ≥ 4.8:1. No state is colour-only (direction = colour + glyph + label; overdue = colour + "late" text + "!" glyph).
