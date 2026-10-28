# Phase 6 — Responsive layer

> Mobile shell: bottom tab bar, `+ Add` bottom sheet, narrow numeric table scroll wrappers, year grid becomes category cards at ≤ 640 px.
>
> Three breakpoints: mobile ≤ 640, tablet 641–1099, desktop ≥ 1100 (ADR-0055).

Entry: Phase 3 exit criteria met per screen.

Exit: 375 px viewports render every v2 route without `horizontalScroll`; tap targets ≥ 44 px; new baselines captured.

Tasks: T-R51..T-R56.

- T-R51 mobile tab bar
- T-R52 `+ Add` bottom sheet
- T-R53 narrow numeric table scroll wrappers (fixes `/budget`, `/analytics`, `/forecast` v1 overflow findings)
- T-R54 Year grid → category cards on mobile
- T-R55 Settings mobile layout
- T-R56 mobile VR baseline regeneration

ADR references: 0055, 0030, 0023 (mobile stance superseded).
