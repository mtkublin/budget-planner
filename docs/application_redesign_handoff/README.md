# Rising Dough — redesign handoff

Redesign of the former "Budget Planner" (desktop + mobile). Based on `design-brief/README.md` and the visual audit.

## Contents
| Path | What |
|---|---|
| `mockups/Rising Dough Redesign.dc.html` | All screens on one pannable canvas. Open in a browser with `support.js` beside it. Each screen has an id (1a–1t, 2a–2e) used throughout these docs. |
| `mockups/screenshots/*.png` | One PNG per screen, named by id and topic. |
| `docs/01-visual-direction.md` | Palette (OKLCH), type, elevation, motion, contrast. |
| `docs/02-information-architecture.md` | Navigation, what merged where, and why. |
| `docs/03-screen-specs.md` | Per-screen behaviour, data, states. |
| `docs/04-components.md` | Component inventory with variants. |
| `docs/05-interactions.md` | Promote, add, override, reconcile, formula flows; keyboard; accessibility. |
| `docs/06-implementation-notes.md` | Mapping to FastAPI + Jinja + HTMX + Tailwind, suggested tooling changes. |
| `docs/07-open-items.md` | Illustrative data, deferred work, decisions still needed. |
| `tokens.css` | Design tokens as CSS variables (Tailwind v4 `@theme` ready). |

## Screen index
| Id | Screen | Screenshot |
|---|---|---|
| 1a / 1b / 1c | Visual direction, components, IA | `system-*` |
| 1d | Today (replaces Overview) | `desktop-1d-today` |
| 1e | Ledger · Actual | `desktop-1e-ledger-actual` |
| 2a | Ledger · Planned | `desktop-2a-ledger-planned` |
| 1f | Ledger · Recurring | `desktop-1f-ledger-recurring` |
| 1g | Plan · Budget | `desktop-1g-plan-budget` |
| 1h | Plan · Year | `desktop-1h-plan-year` |
| 1i | Plan · Forecast | `desktop-1i-plan-forecast` |
| 2b | Plan · Analytics | `desktop-2b-plan-analytics` |
| 1j | Accounts | `desktop-1j-accounts` |
| 1n | Settings · Categories | `desktop-1n-settings-categories` |
| 1k | Reconcile slide-over | `overlay-1k-reconcile` |
| 1l / 2e | Add entry (formula / fixed) | `overlay-1l-…`, `overlay-2e-…` |
| 2c / 2d | Create account / category | `overlay-2c-…`, `overlay-2d-…` |
| 1m | Command palette (deferred) | `overlay-1m-command-palette` |
| 1o–1t | Mobile: Today, Ledger, Plan Budget, Forecast, Accounts, Add sheet | `mobile-*` |

## Naming
The product is now **Rising Dough**. Wordmark is plain Newsreader text; no "local-first" tagline anywhere in the UI.
