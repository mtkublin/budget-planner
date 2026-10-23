# T-051 — Error Handling & Flash Messages

> Phase 5 — Polish. Status: pending.

## Purpose

Make failures legible. Today a validation error bubbles up as an untyped FastAPI 422 and a server error as a stack trace page. After this task, every router raises or returns one of a small set of named exceptions; a single exception-handler module turns each into either (a) an inline HTMX partial that swaps into the form, or (b) a full-page error template. Flash messages exist and work with and without JavaScript. All server errors log a correlation id and the request context; the user sees a safe message.

## Inputs / prerequisites

- Upstream tasks: Phase 3 routers (`T-030..T-039`) must exist — this task patches handler patterns across all of them.
- ADRs:
  - [`ADR-0002`](../../adr/0002-web-stack-fastapi-htmx-jinja.md) — HTMX fragment swaps are the interactivity substrate.
  - [`ADR-0015`](../../adr/0015-forecast-deterministic-live-htmx.md) — defines `HX-Trigger: forecast-stale`; our flash trigger follows the same header pattern.
  - [`ADR-0019`](../../adr/0019-soft-delete-and-audit-log.md) — soft delete UX; delete failures must distinguish "already deleted" vs "not found" and surface the correct 404/409.
- Global rule: `rules/web/testing.md` (Accessibility priority) — flash region must be announced by assistive tech.
- Services already raise domain exceptions (phase 2 contract — assumed from code, not from docs). If no shared exception types exist yet, this task introduces them in `src/budget_planner/domain/errors.py`.

## Deliverables

New files:

- `src/budget_planner/web/errors.py` — exception handler module. Registers FastAPI exception handlers for the mapped exception set.
- `src/budget_planner/domain/errors.py` — if not already present. Domain exceptions:
  - `ValidationError(fields: dict[str, str])` — field-level messages.
  - `NotFoundError(entity: str, entity_id: int)` — soft-deleted or missing.
  - `ConflictError(message: str)` — unique-constraint, same-currency transit violation, cannot-delete-system-category, etc.
  - `ServiceError(message: str)` — generic 500-class; non-user-safe details go to logs.
- `src/budget_planner/web/templates/partials/flash.html` — single flash message partial. Supports `kind ∈ {info, success, warning, error}`. Rendered standalone (HTMX `hx-swap-oob="true"` target) or embedded in a full page.
- `src/budget_planner/web/templates/partials/form_errors.html` — field-level error block used inside form partials. Receives a `errors: dict[str, str]` context.
- `src/budget_planner/web/templates/errors/404.html` — full-page 404.
- `src/budget_planner/web/templates/errors/500.html` — full-page 500 with safe copy + a correlation id.
- `src/budget_planner/web/templates/errors/_shell.html` — shared partial for the two error pages (keeps base layout DRY).

Updated files (sketch, not an exhaustive diff):

- `src/budget_planner/web/app.py` — register handlers from `errors.py`; add middleware that attaches a per-request `request_id` (uuid4 hex) to `request.state` for logging + 500 pages.
- `src/budget_planner/web/routers/*.py` — stop catching exceptions ad-hoc; raise the four domain exceptions. All HTMX form POST handlers return the form partial with `form_errors.html` populated on `ValidationError` (HTTP 422) instead of redirecting.
- `src/budget_planner/web/templates/base.html` — reserve a top-of-main `#flash-region` with `role="status" aria-live="polite"` for normal flashes and a `#flash-region-assertive` with `aria-live="assertive"` for errors. Both are swap targets for `hx-swap-oob` partials.
- `src/budget_planner/web/static/js/flash.js` — ~15 LOC vanilla-JS listener for `HX-Trigger: flash` events. Reads the trigger payload and injects a flash partial into the live region. Behind a `type="module"` script tag. Degrades: without JS, the handler also appends the flash partial into the main response, so flashes always show up.

Audit report:

- Mapping table included in this file (see "Step-by-step") — no separate deliverable file beyond the module + partials.

## Step-by-step

1. **Define the exception → status → surface mapping.** Encode it as a dict in `errors.py` and keep this table as the canonical reference:

   | Exception | HTTP status | HTMX request? | Non-HTMX request |
   |-----------|-------------|---------------|------------------|
   | `ValidationError` | 422 | Return form partial with `form_errors.html` populated. Set `HX-Retarget: #form-root` and `HX-Reswap: outerHTML`. **No** redirect. | Re-render the full form page with errors inline (same template, embedded, not swapped). |
   | `NotFoundError` | 404 | Return `partials/flash.html` with `kind=error` as OOB swap into `#flash-region-assertive`; empty 200-shaped body so HTMX does not clobber the target. | Full-page `errors/404.html`. |
   | `ConflictError` | 409 | Same as `NotFoundError` but `kind=warning`. | Re-render the originating form page with the message in `form_errors.html` under the `_form` key. |
   | `ServiceError` / unhandled `Exception` | 500 | Log full traceback with correlation id; return a stripped `partials/flash.html` with `kind=error` + "Something went wrong. Reference: {request_id}". | Full-page `errors/500.html` with the same reference id visible to the user. |
   | `starlette.exceptions.HTTPException` with `.status_code == 405` | 405 | Flash + leave page as-is. | Full-page 405 renders the 404 template with a tweaked copy. Not worth its own template. |

2. **Implement `errors.py`.** Pure functions bound to FastAPI's `app.exception_handler` on registration. One handler per domain exception. Each handler inspects `request.headers.get("HX-Request") == "true"` to pick the HTMX branch. No business logic in handlers — only mapping and template rendering.

3. **Introduce request id middleware.** `src/budget_planner/web/middleware/request_id.py`. Generates `uuid4().hex[:12]`, assigns to `request.state.request_id`, and adds the id as the `X-Request-Id` response header. Used by both logs and the 500 template.

4. **Logging.** Use the stdlib `logging` module. Configure a JSON formatter (or a key=value formatter) in `web/app.py` on startup. 500-class handlers call `logger.exception("unhandled", extra={"request_id": rid, "path": request.url.path, "method": request.method})`. Never log request bodies — may contain amounts and descriptions.

5. **Flash partial.** `partials/flash.html` renders a single toast-like element with the `kind` driving the token-class (ties into T-053's palette). Uses the shared `role="status"` region for `info`/`success`/`warning`, and the `role="alert" aria-live="assertive"` region for `error`. The partial is dismissible via a `<button type="button" aria-label="Dismiss">` with vanilla-JS click handler in `flash.js`.

6. **HX-Trigger pattern.** Mutating routers that succeed respond with an empty body + `HX-Trigger: flash` and a JSON payload in the trigger header: `{"flash": {"kind": "success", "message": "Transaction added"}}`. `flash.js` listens for `htmx:afterOnLoad` and swaps a server-rendered partial into the OOB region (fetched via a lightweight `GET /_fragments/flash?kind=success&msg=...` endpoint — avoids trusting user strings into HTML in the client). Alternative, simpler route: server returns the flash partial as an OOB swap in the mutation response body itself. **Pick the OOB-in-body route** — fewer round trips, no new fragment endpoint, keeps JS to a tooltip-sized module.

7. **Form error rendering.** `form_errors.html` renders a `<ul role="list" aria-live="polite">` above the form plus per-field `<p id="{field}-error" class="form-error">` elements. The form field uses `aria-describedby="{field}-error"` and `aria-invalid="true"` when the field is in `errors`. Required for a11y pass in T-052.

8. **Router refactor.** For every router under `src/budget_planner/web/routers/`:
   - Remove any `try/except HTTPException`.
   - Raise `ValidationError`, `NotFoundError`, `ConflictError` from service calls or at the router boundary when request shape is wrong.
   - Keep the handler bodies thin: `data = parse(request); result = service.do(data); return render(...)`.
   - On HTMX POSTs that create/update: return the row partial on success; return the form partial with embedded errors on `ValidationError`.

9. **Correlation id in 500 templates.** `errors/500.html` includes `<p class="text-sm text-subtle">Reference: <code>{{ request_id }}</code></p>` so a user can report an id that is grep-able in logs.

10. **Delete UX.** For soft delete routes (ADR-0019): `POST /entity/{id}/delete` on an already-deleted entity returns `NotFoundError` (404). On a protected entity (system category) returns `ConflictError` (409) with a message pointing at the protection reason. Both surface via flash.

11. **Tests.** New tests under `tests/integration/web/test_errors.py`:
    - Each exception → status + body shape for HTMX and non-HTMX branches.
    - Server error path returns 500 with a request id header + log capture includes the same id.
    - Form POST with invalid data returns 422, the response body contains the `form_errors.html` output, no `Location:` redirect header.
    - A11y-touching assertion: response body includes `aria-invalid="true"` on the invalid field and `role="status"` on the flash region.

## Validation / acceptance

- `GET /transactions/0` (nonexistent) returns 404 with `errors/404.html` for a browser request, 404 + flash partial for an HTMX request.
- `POST /transactions` with missing `amount` returns 422; response body is the form partial with the amount field marked invalid; **no** full-page reload for HTMX; browser request re-renders the full form page.
- Deliberately raise `ServiceError` in a stub test endpoint; response is 500, body contains the correlation id, log line with the same id exists.
- `pytest tests/integration/web/test_errors.py` is green with ≥ 95% coverage of `errors.py`.
- Phase 5 exit criterion: "Validation errors rendered inline without full-page reload" is satisfied.
- No router module contains a bare `except Exception` after the refactor.

## Risks & gotchas

- **HTMX swap targets must preserve focus.** When a form partial swaps itself after a `ValidationError`, the previously focused control is lost. Use `hx-swap="outerHTML focus-scroll:true"` on the form, or add a tiny focus restorer in `flash.js` that reads `data-restore-focus` from the swapped partial and refocuses by selector. Document this in the partial.
- **`HX-Retarget` + `HX-Reswap`.** FastAPI returns the response headers only if explicitly set — bind them in the exception handler, not in the router.
- **Flash region OOB swap edge case.** If the response body is empty (success + no table swap), HTMX still processes the `hx-swap-oob` partial if it is included as a sibling top-level element. Verify with the swap docs — do not rely on body-less responses with headers only.
- **No-JS fallback.** `flash.js` is nice to have but not load-bearing. The server must always include the flash partial inline (as an OOB sibling in HTMX responses, or inside the main page for non-HTMX responses). Do **not** gate flashes on client-side JS.
- **Secrets in logs.** `logger.exception` dumps the full traceback. The traceback can include arg reprs. Scrub by using `logger.exception("msg", extra={...})` and never passing user input into the format string. `bandit` + `detect-secrets` in the pre-commit stack remain the net.
- **ADR-0015 forecast errors.** On the forecast page, an FX fetch failure must *not* 500 — ADR-0006 fallback kicks in; a `warning` flash is the correct surface. Verify forecast router raises nothing on fallback.
- **ADR-0019 soft-delete trap.** A `GET /entity/{id}/edit` where the entity is soft-deleted should 404, not render a stale edit form. Repositories already filter `deleted_at IS NULL`; verify the router does not pass `include_deleted=True` by accident.

## Handoff notes

Downstream T-052 depends on the ARIA shape of `flash.html` and `form_errors.html` — do not change the ARIA roles / live-region attributes without updating both tasks. T-053 themes the flash variants via tokens; coordinate the `kind` names (`info|success|warning|error`) so the token names match.

Commit shape: `feat(T-051): centralise error handling and inline validation`.
