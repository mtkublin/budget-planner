# 05 · Interactions and accessibility

## Promote a recurring or planned item
1. Focus a row in Upcoming (↑ ↓) or Ledger.
2. **↵** or Promote expands the row in place: account, date, amount editable.
3. **↵** confirms; **Esc** cancels. Result: real transaction created, `next_due` advances, row collapses, hero figures update.
4. Batch: **⇧↵** promotes every item due today or overdue (confirmation toast with Undo).
5. **Skip** = one click, writes a skipped override for that date. **Override** opens the same expanded row in override mode.
Toast after any write: "Promoted księgowa · Undo" (soft delete makes undo safe).

## Add a transaction
`n` (or + Add) → choose when (Happened / Planned / Repeats) → pick **category** (direction follows) → amount (Fixed or Formula) → account, date, note → **↵** saves; **⌘↵** saves and keeps the modal open for the next entry. Amount field is focused first on mobile.

## Override a budget cell for one month
Plan · Year: click a cell (or arrow to it and press ↵) → popover → amount → keep **One-off** → ↵. Choose **Every year** to create a recurring-annual override. "Reset to default" removes the override. Same popover from Plan · Budget row ⋯ (adds "New default").

## Reconcile
Accounts → Reconcile → enter bank balance → difference shown → choose category (default Reconciliation) → Record. Creates a signed adjustment transaction (+ optional snapshot). Never edits existing transactions.

## Formula amounts
Add/Remove terms; each term has sign, source rule (searchable), coefficient in percent (stored as basis points). Result updates as you type. Save blocked with inline message on cycles or non-positive results.

## Keyboard
`g o/l/p/a/s` navigate · `[` `]` Ledger tabs · `n` add · `/` focus filter · ↑ ↓ move between rows · ↵ primary action · Esc closes the topmost overlay · `?` cheatsheet · ⌘K palette (deferred).

## Accessibility (WCAG 2.1 AA)
- Contrast figures in 01. No colour-only cues.
- Visible focus ring on every interactive element; logical tab order; row actions reachable by keyboard.
- Popovers and modals trap focus, restore it on close, and use correct roles; live-region announcement on promote/override.
- Tap targets ≥ 44px on mobile (the mockup tab bar and sheet follow this; row action buttons expand on touch).
- `prefers-reduced-motion`: no counting or slide animations.
- Charts have a data table equivalent (the Forecast and Analytics tables) and text annotations.
