# 06 · Implementation notes

The mockups use inline styles for review only. They are not production code.

## Fit with the stack
Everything fits FastAPI + Jinja + HTMX + Tailwind, no SPA.
- **Server-rendered fragments:** inline promote row, cell edit popover, override row removal, reconcile panel, month/year switches (`hx-get` + `hx-push-url`).
- **Modals / slide-overs:** `hx-get` the form into a native `<dialog>`; dismiss on owning-form success only (ADR-0040).
- **Live previews:** can-I-afford and formula result via debounced `hx-trigger="keyup changed delay:200ms"` to preview endpoints. Server stays source of truth for minor units.
- **Dynamic colour:** heatmap intensity and category hue must be inline `style` or CSS variables from the server; Tailwind cannot generate them from runtime values.
- **Minimal JS:** key handling (existing), popover positioning (CSS anchor / popover API where available), chart tooltips, optional swipe on mobile.

## Suggested tooling changes
1. Tailwind v4 with tokens in CSS (`tokens.css` → `@theme`).
2. Replace Plotly with Jinja-generated SVG charts (smaller, on-brand, accessible); add tiny hover tooltips.
3. Jinja macros for amount, pill, badge, tag, row; a hidden `/dev/components` page renders them all.
4. Self-hosted variable fonts (Newsreader, Hanken Grotesk, IBM Plex Mono).
5. Optional Alpine.js for popover/formula state; alternative is native dialog/popover + existing vanilla layer.
6. Playwright (re-use the audit script) with overflow assertions at 1440 / 1024 / 375, plus axe-core for AA.
7. View Transitions via `hx-swap="... transition:true"` for promote and tab changes.

## Backend additions implied by the design
- "Can I afford" preview: `GET /today/afford?amount=` → per-day figure.
- Formula preview: `POST /recurring/formula/preview` (terms → result or validation error).
- Last-checked per account (latest snapshot or reconcile date).
- Analytics: spend by category for a period with 12-month average; income vs expense by month; top single items.
- Archive/restore for categories (soft delete exists for transactions; confirm for categories/accounts).
- Batch promote for items due.

## Responsive rules
- ≥ 1100px: sidebar + content. < 1100px: sidebar collapses to icons-free top bar. ≤ 640px: bottom tab bar, tables become two-line cards, Year grid becomes category cards.
- Wide numeric tables must live in a scroll wrapper with a sticky first column (fixes the overflow findings on /budget, /analytics, /forecast/view).
