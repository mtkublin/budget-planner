# T-R52 — `+ Add` bottom sheet

- **Phase**: 6 — Responsive
- **Sequential**: after T-R51, T-R38.
- **Depends on**: T-R51 (mobile tab bar), T-R38 (Add entry modal).
- **References**: ADR-0055 §3, ADR-0030 (modal dismissal scope).

## Context

Mobile uses a bottom sheet instead of the centred modal. Tap on the centre `+ Add` tab opens three choice tiles (Transaction · Planned · Recurring); choosing one swaps the sheet contents to the respective form. Amount field focused first. Dismiss on 2xx (ADR-0030) and on back-swipe (`popstate`).

## Deliverables

- `templates/_partials/_bottom_sheet.html` wrapper:
  ```html
  <dialog class="sheet" id="add-sheet" aria-labelledby="add-sheet-title">
    <div class="sheet__handle" aria-hidden="true"></div>
    <section class="sheet__body">...</section>
  </dialog>
  ```
- `static/css/components/sheet.css`:
  - `position: fixed; bottom: 0`; width 100 vw; `max-height: 90dvh`.
  - CSS translate for open/close; `prefers-reduced-motion` falls back to opacity-only.
  - `env(safe-area-inset-bottom)` padding.
  - `backdrop-filter: blur(8px)` on `::backdrop`.
- `static/js/sheet.js`:
  - `openSheet(url)` fetches the sheet contents via HTMX into the `sheet__body`.
  - Push `history.pushState({sheet: id})` so `popstate` closes.
  - Focus-trap inside the sheet; Esc closes.
  - Swipe-down past 30 % of sheet height closes.
- `templates/transactions/_add_choices.html`:
  - Three large tap tiles ("Transaction" / "Planned" / "Recurring"), each `hx-get` into `#add-sheet .sheet__body`.
- Dismiss contract (ADR-0030): closes on 2xx form submit only; side-effect HTMX responses (formula preview) do not dismiss.
- Visual-regression baselines at 375 px: tiles state, Fixed form state, Formula form state.

## Acceptance criteria

- Opening the sheet pushes a history entry; browser back closes the sheet without leaving the page.
- Swipe-down past 30 % threshold closes; swipe-down below threshold snaps back.
- Focus-trap confirmed by keyboard-only navigation smoke test (no element outside the sheet reachable).
- Dismiss on 2xx form submit only; formula preview requests leave the sheet open.
- `env(safe-area-inset-bottom)` padding visible on iPhone Simulator; nothing clipped behind the home indicator.

## Validation hook

```sh
pytest tests/e2e/test_add_sheet.py && \
  just test-visual --filter add-sheet
```

## Risks & gotchas

- `<dialog>` + `showModal()` has deeper history-interception quirks on Safari — test on real device or emulator before marking done.
- `100dvh` (dynamic viewport height) matters: `100vh` on iOS Safari includes the URL bar area and clips.
- Swipe handler must only intercept vertical drags; horizontal swipes must still reach any carousel inside the form (none currently, but defensive).

## Handoff notes

- The T-R38 Add entry modal shares its form partials; this task hosts them inside the sheet shell at ≤ 640 px.
- The desktop Add modal (T-R38) and this sheet both call the same POST endpoints; keep the dismiss contract identical.
