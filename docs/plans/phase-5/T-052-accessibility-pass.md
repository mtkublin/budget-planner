# T-052 — Accessibility Pass

> Phase 5 — Polish. Status: pending.

## Purpose

Lift the app to WCAG 2.1 AA on the main flows. Semantic landmarks, keyboard navigation, visible focus, labelled inputs, announced HTMX swaps, 4.5:1 contrast, no keyboard traps. Verified by an automated axe-core (or `pa11y`) run in CI on the eight primary routes with zero WCAG-A violations and manual keyboard pass notes captured in an audit report.

## Inputs / prerequisites

- Upstream tasks: Phase 3 routers (`T-030..T-039`) and T-051 (flash + form error ARIA shape).
- Global rule (binding): `rules/web/testing.md` section "Accessibility" — automated accessibility checks, keyboard navigation, reduced-motion, contrast.
- Global rule (adjacent): `rules/web/coding-style.md` — "Semantic HTML First"; `rules/web/design-quality.md` — no generic template look.
- ADRs:
  - [`ADR-0002`](../../adr/0002-web-stack-fastapi-htmx-jinja.md) — HTMX swaps are the interactivity substrate; swapped regions must announce themselves.
  - [`ADR-0015`](../../adr/0015-forecast-deterministic-live-htmx.md) — the forecast fragment swaps on `forecast-stale` events; live region needed.
  - [`ADR-0019`](../../adr/0019-soft-delete-and-audit-log.md) — delete-undelete UX must be reachable via keyboard; destructive actions need `aria-describedby` warnings.

## Deliverables

- Audit report: `docs/plans/phase-5/a11y-audit.md` — one row per route × check, before/after. Written by this task (the file is created fresh).
- Template changes (list, not an exhaustive diff):
  - `src/budget_planner/web/templates/base.html` — add semantic landmarks (`<header>`, `<nav aria-label="Primary">`, `<main id="main">`, `<footer>`), skip link, `<html lang="en">`, `<meta name="theme-color">`, and the two flash live regions established in T-051.
  - `src/budget_planner/web/templates/partials/_form.html` (shared form shell) — every `<input>` / `<select>` / `<textarea>` paired with a `<label for="…">`; required fields get `aria-required="true"`; errors wired via `aria-describedby` + `aria-invalid`.
  - Modal partials (`partials/modal_*.html` for the edit/promote/reconcile modals) — focus-trap wiring: `role="dialog" aria-modal="true" aria-labelledby="…" aria-describedby="…"`, Escape-key close, focus restoration back to the invoking element.
  - Table partials (`partials/*_table.html`) — `<caption class="sr-only">` for every data table, `<th scope="col">`, sort buttons as `<button aria-sort="…">`.
  - Chart partials (forecast + analytics) — Plotly `<div>` wrapped in `<figure>` with `<figcaption>`; off-screen `<table class="sr-only">` summarising the series (long description).
  - `src/budget_planner/web/static/css/a11y.css` — focus-visible styles, `.sr-only`, `prefers-reduced-motion` block. May be inlined into `tokens.css` by T-053; keep as a dedicated file here for easier review.
- CI wiring:
  - `tests/e2e/test_a11y.py` — Playwright + `axe-core` (via `axe-playwright-python` or injected via CDN script in page) running against each of the eight primary routes. Fail on any WCAG-A violation; warn on AA.
  - Alternative tool allowed: `pa11y` run from the `justfile`. **Decision: axe-core via Playwright**, because Playwright is already in the dev dependencies (T-001).
  - `justfile`: new recipe `just a11y` running the axe suite. Added to `just ci`.

## Step-by-step

Numbered checks. Each check is a hard requirement — not satisfied means the task is not done. Record pass/fail in `a11y-audit.md`.

1. **Semantic landmarks.** `base.html` structure:

   ```html
   <!doctype html>
   <html lang="en">
     <head>…</head>
     <body>
       <a class="skip-link" href="#main">Skip to content</a>
       <header>
         <nav aria-label="Primary">…</nav>
       </header>
       <main id="main" tabindex="-1">
         <div id="flash-region" role="status" aria-live="polite"></div>
         <div id="flash-region-assertive" role="alert" aria-live="assertive"></div>
         {% block content %}{% endblock %}
       </main>
       <footer>…</footer>
     </body>
   </html>
   ```

   One `<h1>` per page. No orphan `<div>` stacks around content that should be `<section>` or `<article>`.

2. **Skip link.** Visible on focus (not `display:none`); jumps to `#main`. `tabindex="-1"` on `<main>` so programmatic focus works.

3. **Label-for on every input.** Audit script: `grep -nE "<input|<select|<textarea" src/budget_planner/web/templates -r` → every match must have a corresponding `<label for="…">`. No placeholder-only labels. For checkbox/radio: wrap in `<label>` or use `for`.

4. **Required + invalid.** Required fields: `required` attribute **and** `aria-required="true"` (belt and braces for older AT). Invalid fields after submit: `aria-invalid="true"` + `aria-describedby="{field}-error"` referencing the error paragraph rendered by `form_errors.html` from T-051.

5. **Focus-visible styles.** `a11y.css`:

   ```css
   :focus-visible {
     outline: 2px solid var(--color-focus-ring);
     outline-offset: 2px;
     border-radius: var(--radius-sm);
   }
   .skip-link {
     position: absolute; left: -9999px;
     background: var(--color-surface);
     color: var(--color-text);
     padding: var(--space-2) var(--space-3);
   }
   .skip-link:focus-visible { left: var(--space-2); top: var(--space-2); }
   ```

   Never remove outlines without replacing them.

6. **Contrast ≥ 4.5:1 for body text, ≥ 3:1 for large text and non-text UI.** Verify every palette pair in T-053's `tokens.css` against a contrast checker. Fail the audit if any text pair is below the threshold. Required pairs: `text` on `surface`, `text-subtle` on `surface`, `accent` on `surface` (for links), `text-on-accent` on `accent` (for primary button).

7. **Keyboard navigation path.** Manual walk, documented in `a11y-audit.md`:
   - From `/`, Tab reaches: skip link → every nav item in order → every interactive element in document order → footer.
   - Shift+Tab reverses cleanly.
   - Enter activates buttons; Space activates buttons but not links.
   - No element reachable only via mouse.

8. **Modal focus trap.** Any dialog-shaped partial (edit transaction, promote planned, reconcile account, add snapshot):
   - Opens with focus on first focusable control inside the dialog.
   - Tab/Shift+Tab cycle inside the dialog; focus does not escape to the page below.
   - Escape closes the dialog and restores focus to the invoking element.
   - Implementation: tiny vanilla-JS helper `src/budget_planner/web/static/js/dialog.js` (~30 LOC). HTMX adds the dialog to the DOM; the helper takes over on `htmx:afterSwap` when `[role="dialog"]` is present.

9. **`aria-live` for HTMX swaps.**
   - Table swap after filter change: swapped `<tbody>` is NOT in a live region (would be noisy); instead, the filter form's `<div class="sr-only" aria-live="polite" id="results-count">N transactions</div>` is updated as part of the swap, so SR users hear "47 transactions" after a filter.
   - Flash region live attributes already set (point 1).
   - Forecast chart swap on `forecast-stale`: a sibling `<p class="sr-only" aria-live="polite">` announces "Forecast updated".

10. **Reduced motion.** `a11y.css`:

    ```css
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
        scroll-behavior: auto !important;
      }
    }
    ```

    Verify Plotly animations: pass `{"transition": {"duration": 0}}` in the layout when `prefers-reduced-motion` is set. Simpler: emit a server-side flag read via `Sec-CH-Prefers-Reduced-Motion` header and strip animation config; fall back to the CSS rule above when the header is absent.

11. **Charts: `<figure>` + sr-only summary.** Each chart partial:

    ```html
    <figure>
      <div id="forecast-chart" data-plotly="…"></div>
      <figcaption>Projected balance over the next {{ horizon }} days.</figcaption>
      <table class="sr-only">
        <caption>Daily balance projection</caption>
        <thead><tr><th scope="col">Date</th><th scope="col">Balance</th></tr></thead>
        <tbody>{% for row in series %}<tr><td>{{ row.date }}</td><td>{{ row.balance }}</td></tr>{% endfor %}</tbody>
      </table>
    </figure>
    ```

12. **Tables.** Every `<table>` has `<caption>` (sr-only is fine), `<th scope="col">` on header cells, `scope="row"` on first column if the row has an identity. Pagination controls are `<button>`s with `aria-label` where their visible text is an icon.

13. **Destructive actions.** Delete buttons: `<button type="button" aria-describedby="delete-warning">Delete</button>` with an sr-only `<span id="delete-warning">This soft-deletes the record; it can be restored from the audit log.</span>`. Confirmation modal (if present) uses the dialog pattern from check 8.

14. **Automated run.** `tests/e2e/test_a11y.py` iterates over the eight primary routes, logs into none (no auth), injects axe-core, asserts zero WCAG-A violations. Wire into `just ci`. On failure, dump the axe violations JSON to stdout for triage.

15. **Audit report.** `a11y-audit.md` layout:

    ```
    # Phase 5 — Accessibility Audit

    Date: <YYYY-MM-DD>
    Tool: axe-core via Playwright <version>
    Browser: Chromium <version>

    | Route | Semantic | Labels | Focus-visible | Contrast | Keyboard | Live-region | Modal-trap | WCAG-A | Notes |
    |-------|----------|--------|---------------|----------|----------|-------------|------------|--------|-------|
    | /     |          |        |               |          |          |             |            |        |       |
    | /transactions | | | | | | | | | |
    | /accounts | | | | | | | | | |
    | /categories | | | | | | | | | |
    | /planned | | | | | | | | | |
    | /recurring | | | | | | | | | |
    | /budget | | | | | | | | | |
    | /forecast | | | | | | | | | |
    | /analytics | | | | | | | | | |

    ## Manual keyboard walk notes
    …

    ## Open deferrals (if any)
    …
    ```

## Validation / acceptance

- `just a11y` and `tests/e2e/test_a11y.py` run against each of the eight routes with zero WCAG-A axe-core violations.
- Manual keyboard walk recorded in `a11y-audit.md` passes all 15 checks above.
- All form controls in the templates have an associated label; search script in step 3 returns no unlabelled inputs.
- Contrast check table in `a11y-audit.md` lists every text/background pair in `tokens.css` with the measured ratio and a PASS flag.
- Phase 5 exit criterion: "No a11y regressions on main flows" is satisfied.

## Risks & gotchas

- **Tailwind CDN limitation.** No build step for custom config (ADR-0002); custom focus-ring colour and `sr-only` utility must come from `a11y.css` / `tokens.css`, not from a Tailwind plugin.
- **HTMX swap targets must preserve focus** for keyboard users. Verify every `hx-swap` either (a) swaps a region that does not contain the focused element, or (b) uses `hx-swap="outerHTML focus-scroll:true"` with a `[autofocus]` or explicit focus restorer in `dialog.js`. Add a test that tabs to a filter, triggers the swap, and asserts `document.activeElement` is sensible.
- **Flash messages via HX-Trigger → client-side listener.** Design for no-JS fallback (ADR-0002 constraint): the standard flash region must also render server-side when a partial includes the flash in the response body. T-051 owns this; T-052 verifies the ARIA shape remains correct in both paths.
- **Plotly accessibility.** Plotly's SVG is not accessible to screen readers out of the box. The sr-only table summary (check 11) is the fallback. Do not spend time wiring aria roles into Plotly internals.
- **axe-core version drift.** Pin the axe-core version in `pyproject.toml` dev deps or in a Playwright fixture. A silent minor-version bump can turn a new rule from "incomplete" into "violation" and break CI.
- **`<label>` wrapping checkboxes.** Older djlint versions complain about implicit labels; prefer explicit `for`/`id` pairs to keep djlint happy.
- **Keyboard trap check on modals** is often skipped — verify with a Playwright test that presses Tab 20 times inside a dialog and asserts the active element remains inside.
- **Reduced motion vs Plotly.** Plotly ignores `prefers-reduced-motion` globally; must pass transition config explicitly.

## Handoff notes

- Downstream T-053 themes the focus ring and link styles via `tokens.css`. The focus-ring colour variable is defined by T-053 but **used** by T-052's `a11y.css`. Agree on the name (`--color-focus-ring`) up front.
- T-050's README gets a short "Accessibility" subsection pointing at the audit report and the axe-core recipe.
- Commit shape: `feat(T-052): a11y pass — landmarks, labels, focus, live regions, axe-core in CI`.
