# T-053 — Visual Polish

> Phase 5 — Polish. Status: pending.

## Purpose

Give the app a point of view. Today it reads as "default Tailwind + a few cards" — exactly what `rules/web/design-quality.md` bans. This task introduces a design-token layer (palette, type, spacing, radius, elevation) as CSS custom properties on top of Tailwind CDN, then applies the tokens to the nav, dashboard cards, forecast chart surround, and forms. The surfaces must demonstrate at least four of the "required qualities" in the global design-quality rule. The direction is pre-picked below.

## Design direction

**Picked: editorial / Swiss (International Typographic Style).**

Rationale (one line, as asked): the data is numeric and dense (money, dates, categories) — Swiss typography and generous negative space let the numbers lead; "bento" would compete with the data. Human may override by swapping tokens; the structure is direction-agnostic.

Direction cues enforced by this task:

- Strong type contrast between tabular numerals and sentence copy; one display face, one text face, one mono for numbers.
- Grid-aligned left rail nav; sentence-case; small-caps for section eyebrows.
- Flat surfaces with hairline borders instead of heavy shadows; two levels of elevation only.
- Accent is a single ink colour, not a decorative gradient.
- Dense table typography paired with generous page gutters.

Rejected directions and why:

- **Bento**: fights the dense tables; good for landing pages, not budget operation views.
- **Dark luxury**: default dark mode is a template smell; defer to a toggle after v1.
- **Neo-brutalism**: visually loud; hostile to money numbers.

## Inputs / prerequisites

- Upstream tasks: Phase 3 routers (`T-030..T-039`), T-051 (flash kinds set), T-052 (focus-ring colour contract).
- Binding standard: `rules/web/design-quality.md` — anti-template policy, 4-of-10 required qualities per surface.
- Adjacent standards: `rules/web/coding-style.md` (CSS custom properties, animation-only properties), `rules/web/performance.md` (CWV budgets, no layout thrash).
- ADRs:
  - [`ADR-0002`](../../adr/0002-web-stack-fastapi-htmx-jinja.md) — Tailwind via CDN; no build step. Tokens live in a CSS file layered on top.

## Deliverables

New / updated files:

- `src/budget_planner/web/static/css/tokens.css` — the token layer. CSS custom properties scoped to `:root`. Grouped into palette, typography, spacing, radius, elevation, motion.
- `src/budget_planner/web/static/css/components.css` — small set of component-scoped utility classes that compose the tokens. Keeps per-template inline overrides minimal.
- `src/budget_planner/web/templates/base.html` — load order: Tailwind CDN, then `tokens.css`, then `components.css`, then `a11y.css` (T-052). Preload the primary font.
- Updated templates (listed by file, concrete polish diffs below):
  - `base.html` — top shell: logo mark, left rail nav, main container with asymmetric gutters.
  - `partials/nav.html` — Swiss-rail layout.
  - `pages/home.html` — dashboard composition.
  - `pages/forecast.html` — chart surround.
  - `partials/_form.html` — form rhythm.
- `src/budget_planner/web/templates/partials/eyebrow.html` — tiny snippet for the small-caps section eyebrow pattern.

Not deliverables (explicitly):

- No Tailwind config file (we are on CDN). Everything is `tokens.css` + utility class overrides.
- No icon set beyond what is already in the repo. If none exists, inline a short set of hand-drawn SVGs under `web/static/icons/`; icons are not the point of this task.

## Step-by-step

### 1. Author `tokens.css`

Scoped to `:root`. All values are examples; the committing agent should tune. **oklch** for colour (modern, perceptually uniform; `rules/web/coding-style.md` recommends it). `clamp()` for fluid typography. `rem` for spacing.

```css
:root {
  /* Palette — editorial / Swiss */
  --color-surface:         oklch(99% 0 0);
  --color-surface-raised:  oklch(97% 0 0);
  --color-surface-sunken:  oklch(94% 0.004 90);
  --color-hairline:        oklch(88% 0.004 90);
  --color-text:            oklch(18% 0 0);
  --color-text-subtle:     oklch(42% 0 0);
  --color-text-faint:      oklch(60% 0 0);
  --color-accent:          oklch(50% 0.17 258);         /* editorial ink */
  --color-text-on-accent:  oklch(99% 0 0);
  --color-focus-ring:      oklch(60% 0.21 258);

  /* Semantic (ties to flash kinds in T-051) */
  --color-info:            oklch(55% 0.12 240);
  --color-success:         oklch(55% 0.14 155);
  --color-warning:         oklch(68% 0.17 85);
  --color-error:           oklch(55% 0.21 25);

  /* Typography */
  --font-display: "Fraunces", "Source Serif 4", Georgia, serif;
  --font-text:    "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono:    "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

  --text-xs:      clamp(0.75rem, 0.70rem + 0.1vw, 0.8125rem);
  --text-sm:      clamp(0.875rem, 0.82rem + 0.15vw, 0.9375rem);
  --text-base:    clamp(1rem, 0.95rem + 0.2vw, 1.0625rem);
  --text-lg:      clamp(1.125rem, 1.05rem + 0.3vw, 1.25rem);
  --text-xl:      clamp(1.375rem, 1.2rem + 0.6vw, 1.6875rem);
  --text-display: clamp(2rem, 1.4rem + 2vw, 3.25rem);
  --text-hero:    clamp(2.75rem, 1.5rem + 4vw, 5rem);

  --tracking-eyebrow: 0.08em;
  --leading-tight:    1.1;
  --leading-normal:   1.5;

  /* Spacing — modular, 4px base, non-uniform scale */
  --space-0: 0;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;
  --space-7: 3rem;
  --space-8: 4.5rem;
  --space-9: 6.5rem;
  --space-section: clamp(3rem, 2rem + 3vw, 6rem);
  --page-gutter:   clamp(1rem, 1rem + 2vw, 4rem);

  /* Radius */
  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-lg: 8px;
  --radius-pill: 999px;

  /* Elevation — only two levels */
  --elevation-0: none;
  --elevation-1: 0 1px 0 0 var(--color-hairline);                    /* hairline bottom */
  --elevation-2: 0 1px 0 0 var(--color-hairline), 0 8px 24px -16px rgba(0,0,0,0.12);

  /* Motion */
  --duration-fast:   120ms;
  --duration-normal: 220ms;
  --ease-out-expo:   cubic-bezier(0.16, 1, 0.3, 1);
}
```

Load order rule: `tokens.css` **before** any component CSS. Tailwind utilities still available on top, used sparingly.

### 2. Preload the primary font

In `base.html` `<head>`, preload only the `Inter` 400 and 600 WOFF2 files and the `Fraunces` 500 italic for display. All others via `@font-face` with `font-display: swap`. Keep inside the `rules/web/performance.md` budget of two families + the mono.

### 3. Component shell: `components.css`

Tokens drive the surface, not inline styles. Example classes:

```css
.surface      { background: var(--color-surface); color: var(--color-text); }
.surface--raised { background: var(--color-surface-raised); box-shadow: var(--elevation-1); }
.hairline-b   { border-bottom: 1px solid var(--color-hairline); }
.eyebrow      {
  font-family: var(--font-text);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-eyebrow);
  color: var(--color-text-faint);
}
.numeric      { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.btn-primary  {
  background: var(--color-accent);
  color: var(--color-text-on-accent);
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-sm);
  transition: transform var(--duration-fast) var(--ease-out-expo);
}
.btn-primary:hover:not(:disabled) { transform: translateY(-1px); }
.btn-primary:active { transform: translateY(0); }
```

Hover / focus / active states are explicit per `rules/web/design-quality.md` and `rules/web/coding-style.md` (animate `transform` only).

### 4. Apply to nav (`partials/nav.html` + `base.html`)

- Left rail, 220 px fixed, hairline-right separator.
- Section eyebrows ("TRACK", "PLAN", "ANALYZE") with `.eyebrow`.
- Items grouped: TRACK → Transactions, Accounts, Categories. PLAN → Planned, Recurring, Budget. ANALYZE → Forecast, Analytics.
- Current-page item: accent left-border 2 px, `aria-current="page"`.
- Hover: subtle `--color-surface-raised` background change; no shadow.
- Required-qualities checklist for this surface: (1) scale contrast ✓ (2) intentional rhythm ✓ (4) typography pairing ✓ (6) hover/focus states ✓ — four of ten, pass.

### 5. Dashboard cards (`pages/home.html`)

- Three unequal cells, grid-breaking: a wide "This month" card spanning two columns, a narrow "Fortune total" card, and a full-width "Next 7 days" strip under them.
- "Fortune total" uses `--text-display` numerals, mono, tabular-nums; label in eyebrow style; sub-label in `--text-sm` subtle.
- "This month" has a sparkline + budget-remaining bar; the bar uses `--color-accent` fill against `--color-surface-sunken` track; no gradient.
- "Next 7 days" is a horizontal list of pill rows, hairline separators, 7 items; empty slot shows `.text-faint` dash — intentional negative space.
- Required-qualities: (1) hierarchy ✓ (2) rhythm ✓ (3) depth via hairlines + 1 raised surface ✓ (10) data as system (sparkline / bar use tokens) ✓.

### 6. Forecast chart surround (`pages/forecast.html`)

- Chart lives in a `<figure class="surface surface--raised">` wrapper with `--space-6` padding.
- Above the chart: eyebrow "FORECAST", `<h1>` "Projected balance", a horizon-selector `<form>` using `.btn-primary` + segmented buttons (`6M | 1Y | 5Y`).
- Below: `<figcaption class="text-subtle text-sm">` describing the series + the sr-only table (owned by T-052).
- Plotly layout overrides: pass `paper_bgcolor` and `plot_bgcolor` = `var(--color-surface-raised)`, `font.family = Inter`, `font.size = 13`, gridlines in `--color-hairline`, no legend background. Pure config, no CSS reaching into Plotly SVG.
- Required-qualities: (3) depth ✓ (5) color semantic ✓ (6) hover states on the horizon selector ✓ (10) data vis system-integrated ✓.

### 7. Forms (`partials/_form.html`)

- One column, labels above inputs. Label uses `.eyebrow` style for compactness.
- Input: `--color-surface`, 1 px hairline border, `--radius-sm`, `--space-3` padding. On focus-visible: `--color-focus-ring` outline (owned by T-052; this task provides the token).
- Submit button right-aligned, `.btn-primary`; secondary action is a text-link using `--color-accent` + underline on hover.
- Numeric fields (`amount`) are mono + tabular-nums + right-aligned.
- Error message block (owned by T-051) themed with `--color-error` text and a 2 px left border.
- Required-qualities: (2) rhythm ✓ (4) typography ✓ (6) hover/focus ✓ (5) semantic colour ✓.

### 8. Motion budget

- Only `transform` and `opacity` animated (`rules/web/coding-style.md` and `rules/web/performance.md`).
- Durations capped at `--duration-normal` (220 ms). Nothing longer.
- Reduced-motion handled by T-052's media query — no per-component overrides needed.

### 9. Verify design-quality checklist

For each of the four surfaces above (nav, dashboard, forecast surround, forms) record in the commit message or in a comment on `tokens.css` which four required-qualities the surface satisfies. The rule is "at least four of ten"; log them so a future reviewer can audit.

## Validation / acceptance

- `tokens.css` committed and loaded in `base.html` before any component CSS.
- No hard-coded palette values (hex / rgb / oklch) in any template or component CSS; everything references a `--color-*` variable. Enforce with a `grep` check in CI: `! grep -nE '#[0-9a-fA-F]{3,8}|rgba?\(|oklch\(' src/budget_planner/web/templates src/budget_planner/web/static/css --include='*.html' --include='*.css' --exclude='tokens.css'` returns zero matches.
- Each of the four target surfaces (nav, dashboard, forecast surround, forms) satisfies ≥ 4 of the 10 required qualities in `rules/web/design-quality.md`. The committing agent lists which four, per surface, in the commit body.
- Lighthouse (manual, or Playwright + lighthouse-ci) on `/` and `/forecast` with every CWV metric inside the thresholds in `rules/web/performance.md` (LCP < 2.5s, INP < 200ms, CLS < 0.1, FCP < 1.5s, TBT < 200ms).
- No animations run on layout-bound properties (`width`, `height`, `top`, `left`, `margin`, `padding`, `border`, `font-size`). Grep check: `grep -nE 'transition.*(width|height|top|left|margin|padding|border|font-size)' src/budget_planner/web/static/css` returns zero.
- Contrast ratios (owned by T-052's audit) pass against the final `tokens.css`.
- Phase 5 exit criterion: "UI avoids the generic template look" is satisfied; `tokens.css` is the committed artifact.

## Risks & gotchas

- **Tailwind CDN limitation.** No build step, so Tailwind's `@theme` / config file is unavailable. The token layer must sit *on top* of Tailwind via CSS custom properties referenced from component classes and inline `style="color: var(--color-accent)"` as a last resort. Do not fork Tailwind.
- **Specificity order.** Tailwind utility classes have the same specificity as our component classes; load order wins. `components.css` must load **after** Tailwind's CDN script injects its stylesheet. Confirm with devtools.
- **oklch browser support.** Safari ≥ 15.4, Chrome ≥ 111, Firefox ≥ 113 (all 2023+). Project is local, single user, so fine. If the owner's browser is older, fall back to equivalent sRGB values side-by-side via `color()` function or hex twin.
- **Plotly theming via Python only.** Do not try to style the SVG with CSS; Plotly re-renders and overwrites. Pass layout + template to the figure in the service layer.
- **Font files on disk vs CDN.** Shipping fonts locally keeps the local-first promise; the `127.0.0.1` constraint means CDN font loads are also fine but add a dependency. Prefer self-hosted WOFF2 for the two body fonts; mono can stay system-default.
- **Design-quality rule bans generic look.** Call out specific moves per surface in the commit body — do not hand-wave. The committer must enumerate which four qualities each surface satisfies.
- **Scope creep.** Do not add a theme toggle, dark mode, settings page, animations library, or icon system here. Any of those is a new ADR + its own task.

## Handoff notes

- End-of-phase handoff: v1 release artifact. After T-053 lands, T-050 (README) gets a one-paragraph "Design" subsection pointing at `tokens.css` and this plan.
- Commit shape: `feat(T-053): design tokens + editorial/Swiss surface pass on nav, dashboard, forecast, forms`.
- Future-you: if a dark mode is wanted later, redefine the same `--color-*` vars under a `[data-theme="dark"]` scope. No template changes required.
