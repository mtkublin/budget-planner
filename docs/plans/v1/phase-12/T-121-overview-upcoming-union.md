# T-121 [P] Overview Upcoming unions planned + recurring; group `+ Planned` + `+ Recurring`

> Depends on: T-119. Parallel-safe with T-122, T-123, T-124.

## Scope

Overview-only template + light hydrator work; no service work (T-119 landed `services.upcoming.list_upcoming`).

### `web/routers/home.py`

- Upcoming fragment hits `services.upcoming.list_upcoming(conn, today=…, window_days=…)`.
- A hydrator converts each `UpcomingItem` into the shape the template already consumes, extending it with `kind`, `planned_id`, `rule_id`, `override_present`.
- `today` is sourced from `datetime.now(ZoneInfo(settings.display_timezone)).date()` per ADR-0007.

### `templates/home/_upcoming_list.html`

- Row partial branches on `item.kind`:
  - `"planned"` → existing promote-planned affordance (`hx-get="/planned/{{ planned_id }}/promote"` modal flow).
  - `"recurring"` → new buttons: **Promote** (`hx-get="/recurring/{{ rule_id }}/promote"`), **Skip** (`hx-post="/recurring/{{ rule_id }}/skip-next" hx-confirm="Skip the next occurrence?"`), **Override** (`hx-get="/recurring/{{ rule_id }}/overrides/new?occurrence_date={{ effective_date }}"`). Edit of the rule is intentionally **not** surfaced from Overview; users edit the rule from Ledger Recurring.
- `is_overdue` chip rendering unchanged for planned rows; recurring rows never render overdue (promotion is manual but the row is anchored at `next_due`, not an operation date).

### `templates/home/_upcoming_panel.html`

- Current markup has two sibling `<button>`s under `.panel__header`. Wrap them inside a dedicated flex cluster:
  ```html
  <div class="panel__add-group">
    <button ...>+ Planned</button>
    <button ...>+ Recurring</button>
  </div>
  ```
- Stylesheet: add `.panel__add-group { display: flex; gap: var(--space-2); }` (or whatever the existing design-system token is).

### Tests

- `tests/integration/web/test_home.py`:
  - Overview Upcoming contains a `[data-kind="recurring"]` row when an active rule's `next_due` falls in the window.
  - A persisted planned row with past date still renders as overdue + italic.
  - Clicking `+ Recurring` opens the slide-over wired to `/recurring/new`.
  - `+ Planned` + `+ Recurring` buttons both live inside `.panel__add-group` (DOM assertion).
- `tests/integration/web/test_fab.py` — unchanged; Overview FAB still opens the actual-txn create form (ADR-0026).

### `frontend-visual-audit`

- `/` at 1440 / 1024 / 375 with a seeded recurring rule whose `next_due` falls in the current window. Confirm the two add buttons group together on the smallest viewport.

## Acceptance

- Overview Upcoming shows planned + recurring together, correctly sorted by effective date.
- No duplicate rows when a recurring rule has an override for the next cycle (override merges in; one row).
- `+ Planned` + `+ Recurring` visually paired.
- `just ci` + visual sweep green.

## Non-goals

- Ledger-side changes (T-122).
- Any change to `services.upcoming` (T-119 shipped it).
