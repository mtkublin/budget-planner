# T-R03 — Self-hosted fonts

- **Phase**: 1 — Foundations
- **Sequential**: after T-R01.
- **Depends on**: T-R01.
- **References**: ADR-0050 §3, ADR-0052 §3, `~/.claude/rules/web/performance.md` §Font loading.

## Context

Three families (Newsreader, Hanken Grotesk, IBM Plex Mono) must be served from `/static/fonts/` as variable `woff2` with a conservative preload strategy. CDN hosting rejected (ADR-0005 local-first + v3 privacy posture).

## Deliverables

- `src/budget_planner/web/static/fonts/`:
  - `newsreader.var.woff2` (weight axis 400..500, latin + latin-ext subset).
  - `hanken-grotesk.var.woff2` (weight axis 400..600).
  - `ibm-plex-mono.var.woff2` (weight axis 400..600).
  - `LICENSE.md` listing each face's upstream license (SIL OFL for all three; verify + commit).
- `src/budget_planner/web/static/css/fonts.css` with three `@font-face` blocks: `font-weight: 400 600`, `font-display: swap`, `font-style: normal`, `font-stretch: 100%`, `unicode-range` for latin + latin-ext.
- Imported from `app.css` **after** `tokens.css` and **before** `@theme`.
- `base.html` `<head>`:
  ```html
  <link rel="preload" href="/static/fonts/newsreader.var.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/static/fonts/hanken-grotesk.var.woff2" as="font" type="font/woff2" crossorigin>
  ```
  No preload for Plex Mono (not above-the-fold on the login/landing route).
- `.gitattributes` entry marking `*.woff2` as binary.
- Phase 1 CI measures total font payload; fails if gzipped > 220 kB.

## Acceptance criteria

- `curl -I http://localhost:8000/static/fonts/newsreader.var.woff2` returns `Content-Type: font/woff2` and `Cache-Control: public, max-age=31536000, immutable` (v3 Caddy adds this; v1 dev server can leave off).
- `@supports (font-variation-settings: normal)` is true in Chrome 125; the hero number renders in Newsreader 500 without a FOUT.
- Browser DevTools "Network" preloads land before HTMX fetches.
- Lighthouse font-load audit on `/today` returns no critical-request warnings.

## Validation hook

```sh
du -b src/budget_planner/web/static/fonts/*.woff2 | awk '{s+=$1} END {print s " bytes"; if (s > 220*1024) exit 1}'
```

## Risks & gotchas

- Variable fonts can be large; subset aggressively (strip CJK, Greek, Cyrillic for the three families). Use `pyftsubset --layout-features='*'` with `--unicodes=U+0000-00FF,U+0100-017F,U+0180-024F` + the eight Polish diacritics.
- `crossorigin` on the preload is **required** even for same-origin fonts or the browser double-downloads.
- `font-display: swap` must apply to all three; without it, the hero FOIT breaks the "feel instant" principle.
- IBM Plex Mono variable at full axis blows past 150 kB; subset latin only.

## Handoff notes

- T-R05 wordmark uses Newsreader 500; T-R11 amount macro uses Plex Mono 500. Both are covered by the preloaded + swap-loaded weights.
- Phase 3 screens use Hanken Grotesk 600 for buttons — swap-loaded; expect brief fallback flash under reduced-motion-aware tests, acceptable.
