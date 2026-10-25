# T-072 — README + CHANGELOG

> Phase 6 — UX redesign. Status: pending.

## Purpose

Close Phase 6 by updating `README.md` with the new 4-tab navigation, the keyboard shortcut map, a migration note for legacy URLs, and a pointer to ADR-0023. Append a dated line to `docs/CHANGELOG.md` on landing day. No binary screenshots are committed; the README describes the capture command for a future screenshot without checking in the image.

## Inputs / prerequisites

- Upstream tasks: T-071 (a11y re-audit landed; all new surfaces stable).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md).
- Adjacent standards: project's existing README style; `rules/common/git-workflow.md` for conventional-commits message.

## Deliverables

Updated files:

- `README.md`:
  - Replace the top-level navigation description with the new 4-tab IA.
  - Add a "Navigation" subsection:
    - Overview, Ledger, Accounts, Budget — one line each, describe the job.
    - Settings is a drawer, not a tab; opens with ⚙ or `g s`.
  - Add a "Keyboard shortcuts" subsection — the full map (see below).
  - Add a "Migration" subsection:
    - "Legacy URLs `/transactions`, `/planned`, `/recurring`, `/categories`, `/analytics` return `302` redirects to their new homes; bookmarks continue to work."
    - Link to ADR-0023 and to `docs/plans/v1/phase-6/README.md`.
  - Replace or add the "Design" subsection pointing at `static/css/tokens.css` + ADR-0023.
  - Describe (don't commit) the screenshot capture command, e.g.
    ```sh
    npx playwright screenshot --viewport-size=1440,900 http://127.0.0.1:8000/ docs/images/overview.png
    ```
    with a note that the image is intentionally not checked in.
- `docs/CHANGELOG.md` — append under today's date:
  ```markdown
  ## 2026-XX-XX
  - Phase 6 UX redesign: 4-tab IA (Overview / Ledger / Accounts / Budget) + Settings drawer + command palette + quick-add FAB. Legacy URLs redirect. See ADR-0023 and `docs/plans/v1/phase-6/`.
  ```
- `docs/plans/v1/tasks.md` — mark T-061…T-072 as ✅ once each lands; T-072's own line marked ✅ on commit.

Not deliverables:

- No binary assets. The README describes screenshot capture; it does not add images.
- No new scope. If a reviewer wants more docs (e.g. a longer migration guide), split into a follow-up task.

## Step-by-step

1. **Draft the Navigation subsection.**
   ```markdown
   ## Navigation
   The app has four primary destinations, listed in the left rail:
   - **Overview** (`/`) — fortune, this-month budget-left, upcoming planned payments.
   - **Ledger** (`/ledger`) — all money events: Actual · Planned · Recurring, switched by a segmented control.
   - **Accounts** (`/accounts`) — balances, sparklines, reconcile.
   - **Budget** (`/budget`) — monthly summary, rules editor, breakdown charts.
   Settings is a slide-over drawer (⚙ icon or `g s`): Categories · FX · Preferences.
   ```
2. **Draft the Keyboard shortcuts subsection.**
   ```markdown
   ## Keyboard shortcuts
   | Keys | Action |
   |---|---|
   | `g o` / `g l` / `g a` / `g b` | Go to Overview / Ledger / Accounts / Budget |
   | `g s` | Open Settings drawer |
   | `n` | Quick-add (context-aware: actual / planned / recurring) |
   | `/` | Focus the current page's search / filter input |
   | `[` / `]` | Cycle Ledger segmented control |
   | `⌘K` / `Ctrl K` | Open command palette |
   | `?` | Open shortcut cheatsheet |
   | `Esc` | Close topmost overlay |
   ```
3. **Draft the Migration subsection.**
   ```markdown
   ## Migration from the pre-v1 nav
   The old 9-tab navigation has been consolidated. Legacy URLs continue to work:
   | Old URL | New home |
   |---|---|
   | `/transactions` | `/ledger?view=actual` |
   | `/planned` | `/ledger?view=planned` |
   | `/recurring` | `/ledger?view=recurring` |
   | `/categories` | Settings drawer → Categories |
   | `/analytics` | `/budget#breakdown` |
   | `/budget/manage` | `/budget#rules` |
   All above return `302` redirects for one release; HTMX fragment aliases preserved. See [ADR-0023](docs/adr/0023-ux-redesign-information-architecture.md) and [`docs/plans/v1/phase-6/`](docs/plans/v1/phase-6/README.md).
   ```
4. **Append the CHANGELOG line.** One bullet under today's date. Keep it short — details live in the ADR + phase-6 README.
5. **Preview on GitHub.** Push a draft branch, open the README on github.com, confirm tables render and the ADR link resolves. If a table doesn't render, it's probably a column-count issue — fix locally.
6. **Flip phase status.** In `docs/plans/v1/tasks.md`, prefix the T-072 line with ✅ at commit time.

## Validation / acceptance

- `README.md` contains the three new subsections (Navigation, Keyboard shortcuts, Migration) with the content above (wording may be tightened; structure stable).
- `README.md` links to `docs/adr/0023-ux-redesign-information-architecture.md` and `docs/plans/v1/phase-6/README.md`.
- `docs/CHANGELOG.md` has an entry dated the landing day summarising Phase 6.
- `README.md` renders cleanly on github.com (manual check): no broken tables, no broken links.
- `grep -nE '/transactions|/planned|/recurring|/categories|/analytics' README.md` returns matches only inside the migration table.
- No binary files added under `docs/images/` by this commit.

## Risks & gotchas

- **Screenshot drift.** Describing a capture command without committing the image means the README references no local file. If a future task adds screenshots, add the image path and update the README together.
- **CHANGELOG date.** Use the actual landing day (not when the stub was drafted). Commit date can differ from the date in the file — pin to commit day.
- **Markdown table GitHub quirks.** Pipe characters inside cells (e.g. ``/ledger?view=actual``) must be inside backticks; GitHub renders them fine inside code spans.
- **Link rot in the ADR.** Make sure ADR-0023 exists and is linked from `docs/adr/README.md` before this task lands (T-060 handled it; verify).
- **Scope creep into a "what's new" blog.** This task is doc-only, not marketing. One README section per topic, one CHANGELOG line, done.

## Handoff notes

- End-of-phase handoff: v1 Phase 6 complete. Any future UX work on top of this starts with a new ADR.
- Commit shape: `docs(T-072): README nav + shortcuts + migration + CHANGELOG for Phase 6`.
