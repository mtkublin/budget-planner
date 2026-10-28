# T-R61 — `toast` macro + Undo wiring

- **Phase**: 2 — Primitives
- **Parallel-safe**: yes.
- **Depends on**: T-R10.
- **References**: ADR-0053 (adds row), ADR-0056 §1, handoff §Interactions "Toast after any write: 'Promoted księgowa · Undo'".

## Context

Every write surfaces a toast; destructive writes carry an Undo. Soft-delete (ADR-0019) makes Undo safe for soft-deletable entities. The toast is a shared primitive consumed by every mutation endpoint via `HX-Trigger: {"toast": {...}}`.

## Deliverables

- `src/budget_planner/web/templates/_partials/components/_toast.html`:
  ```jinja
  {% macro toast(variant, message, undo_url=None, undo_label="Undo") %}
    <div class="toast toast--{{ variant }}" role="status" aria-live="polite">
      <span class="toast__msg">{{ message }}</span>
      {% if undo_url %}
        <button class="toast__undo" hx-post="{{ undo_url }}" hx-swap="none">{{ undo_label }}</button>
      {% endif %}
    </div>
  {% endmacro %}
  ```
- `static/css/components/toast.css` — bottom-centre on desktop, bottom-above-tab-bar on mobile; auto-dismiss 4 s via CSS animation + a 4 s `setTimeout` removal.
- `static/js/toast.js`:
  - Listens for `HX-Trigger: {"toast": {...}}` server events.
  - Renders a `_toast.html` fragment into `#toast-root`.
  - Dismiss on Undo click or 4 s timeout.
  - Stack up to 3 toasts; older toasts expire first.
- `base.html` gains `#toast-root` div (if not already present).
- Server-side helper `src/budget_planner/web/htmx.py::add_toast(response, variant, message, undo_url=None)` that mutates the response's `HX-Trigger` header.
- Representative usage on `/dev/components#toast`.
- Unit tests for the server helper + Playwright test for render + dismiss.

## Acceptance criteria

- `services.transactions.create(...)` writes emit a toast with Undo pointing at `/transactions/{id}/delete` (soft-delete).
- Soft-deleted entities can be restored via the Undo button; the second toast confirms restore.
- Three toasts stacked at once render in reverse chronological order; oldest dismisses first.
- `prefers-reduced-motion` disables the slide-in; opacity transition only.
- `role="status"` + `aria-live="polite"` present; screen readers announce without stealing focus.

## Validation hook

```sh
pytest tests/unit/web/test_toast_helper.py tests/e2e/test_toast.py && \
  curl -sS http://localhost:8000/dev/components | grep "toast__msg"
```

## Risks & gotchas

- Do not use `aria-live="assertive"` — toasts are informational, not critical. Assertive interrupts screen-reader flow.
- Undo endpoint is the inverse of the write — must be idempotent against double-click (soft-delete already is).
- Multi-tab Undo: a toast rendered in tab A cannot Undo a write made in tab B. The Undo URL is server-authoritative; it operates on the entity id, so it's correct regardless of which tab fires it.

## Handoff notes

- Every Phase 4 mutation endpoint adds a `response.headers["HX-Trigger"] = ...` call via the shared helper.
- Phase 3 screen tasks that introduce new mutations wire the toast through the helper; do not render toast HTML inline.
