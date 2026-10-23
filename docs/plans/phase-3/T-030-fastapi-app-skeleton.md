# T-030 — FastAPI App Skeleton

> Phase 3 — Web Layer. Status: pending.

## Purpose

Stand up the FastAPI application that every router in Phase 3 plugs into: app factory, Jinja2 environment with shared template helpers, HTMX / Tailwind / Plotly loaded from CDNs in a `base.html` layout, a shared `partials/` directory, request-scoped SQLite connection dependency, and the `127.0.0.1`-bound uvicorn entrypoint. No business logic — this task owns the plumbing that T-031..T-039 extend.

## Inputs / prerequisites

- Upstream tasks:
  - [`../phase-0/T-004-config-module.md`](../phase-0/T-004-config-module.md) — provides `Settings` (`host`, `port`, `base_currency`, `display_timezone`, `database_url`).
  - [`../phase-1/T-010-migration-framework.md`](../phase-1/T-010-migration-framework.md) — `get_connection(settings)` is reused as a FastAPI dependency.
  - Phase 2 service modules exist, pure, and testable; this skeleton does not call them but is wired to accept them.
- ADRs:
  - [`../../adr/0002-web-stack-fastapi-htmx-jinja.md`](../../adr/0002-web-stack-fastapi-htmx-jinja.md) — stack choice.
  - [`../../adr/0005-single-user-no-auth-user-id-scaffold.md`](../../adr/0005-single-user-no-auth-user-id-scaffold.md) — bind to `127.0.0.1`, `user_id = 1`.
  - [`../../adr/0007-timezone-handling.md`](../../adr/0007-timezone-handling.md) — UTC in DB, `Europe/Warsaw` in UI.
  - [`../../adr/0021-functional-style-no-oop.md`](../../adr/0021-functional-style-no-oop.md) — routers are plain functions decorated with `@router.get/post`; no router subclasses.
- Service functions: none directly. Dependency injection surface only.

## Deliverables

- Router module path: `src/budget_planner/web/app.py` (app factory `create_app(settings) -> FastAPI`).
- Supporting modules:
  - `src/budget_planner/web/deps.py` — FastAPI dependencies: `get_db()` (yields a connection), `get_settings()`.
  - `src/budget_planner/web/templating.py` — `build_jinja_env(settings)` and the shared filters/globals registered on it.
  - `src/budget_planner/web/htmx.py` — small helpers (`is_htmx(request) -> bool`, `trigger(response, *events) -> None`).
- Jinja templates:
  - `src/budget_planner/web/templates/base.html` — full-page shell: `<head>`, Tailwind CDN, HTMX CDN, Plotly CDN, named blocks (`title`, `head_extra`, `nav`, `main`, `scripts`).
  - `src/budget_planner/web/templates/partials/_flash.html` — toast-strip fragment, swapped out-of-band on mutations.
  - `src/budget_planner/web/templates/partials/_money.html` — `{{ amount|money(ccy) }}` wrapper used by every list surface.
  - `src/budget_planner/web/templates/partials/_direction_badge.html` — pill rendering for a `Direction`.
  - `src/budget_planner/web/templates/partials/_pagination.html` — HTMX-driven prev/next controls (used by txn + planned + analytics tables).
  - `src/budget_planner/web/templates/partials/_form_errors.html` — inline validation error block.
  - `src/budget_planner/web/templates/_dev_index.html` — a minimal landing page returned by `GET /` until T-039 replaces it (so Phase 3 agents working in parallel never land on a 404).
- Static assets: `src/budget_planner/web/static/app.css` — a thin layer of CSS custom properties (color + spacing + type scale tokens) that Tailwind utilities compose with. Served under `/static`.
- Tests: `tests/integration/web/test_app.py` using FastAPI `TestClient`.

## Endpoints

Only two endpoints land in T-030. The rest are added by their respective routers.

| Method | Path | Request shape | Response shape | Service call(s) | HTMX attrs on trigger |
|--------|------|---------------|----------------|-----------------|------------------------|
| GET | `/healthz` | — | `application/json` `{"status":"ok","version":<pkg version>}` | — | none (no HTMX) |
| GET | `/` | — | `text/html` (base shell + `_dev_index.html`). T-039 replaces this with the real dashboard. | — | none |

## Template structure

`base.html` block skeleton (routers only `extends` this file):

```jinja
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}Budget Planner{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tailwindcss@3/dist/tailwind.min.css">
    <link rel="stylesheet" href="{{ url_for('static', path='app.css') }}">
    <script src="https://unpkg.com/htmx.org@2"></script>
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
    {% block head_extra %}{% endblock %}
  </head>
  <body class="min-h-screen bg-[color:var(--surface)] text-[color:var(--ink)]">
    <div id="flash" hx-swap-oob="true"></div>
    {% block nav %}{% endblock %}  {# filled by T-039 #}
    <main id="main" class="mx-auto max-w-screen-xl px-6 py-10">
      {% block main %}{% endblock %}
    </main>
    {% block scripts %}{% endblock %}
  </body>
</html>
```

Shared partials used across every router:

| Partial | Role |
|---------|------|
| `partials/_flash.html` | Target of `hx-swap-oob="true"` on `<div id="flash">`. Rendered by any router after a mutation. |
| `partials/_money.html` | `<span class="tabular-nums ...">` — makes figures line up vertically in tables. |
| `partials/_direction_badge.html` | Pill with semantic color per direction (income / expense / transit / adjustment). |
| `partials/_pagination.html` | `hx-get="{{ path }}?page=…"` + `hx-target` / `hx-swap="outerHTML"` on the table body. |
| `partials/_form_errors.html` | `<ul role="alert">` under a form field; rendered as the entire form fragment on 4xx response. |

Jinja filters registered on `env` (defined in `templating.py`):

| Filter / global | Signature | Behaviour |
|----------------|-----------|-----------|
| `money` | `money(amount_minor, currency)` | Formats positive int minor units into currency-specific decimal string (ADR-0008). |
| `date_fmt` | `date_fmt(d, pattern="%Y-%m-%d")` | ISO by default; same output across routers. |
| `dt_local` | `dt_local(utc_ts)` | Converts UTC `TIMESTAMP` to `settings.display_timezone` for display (ADR-0007). |
| `direction_badge` | `direction_badge(direction)` | Includes `partials/_direction_badge.html`. |
| `base_ccy` global | — | `settings.base_currency` so templates do not import config. |
| `csrf_token` placeholder | — | Returns empty string in v1; keeps the attribute shape stable for a future auth phase. |

## HTMX interactions

T-030 does not swap any domain data. It defines the conventions every later router follows:

- `hx-boost="true"` is **not** used globally — each router opts individual links in.
- Full-page navigation targets `#main` with `hx-swap="innerHTML show:window:top"`. Routers that only re-render a table use `hx-target` scoped to that table and `hx-swap="outerHTML"`.
- Out-of-band flash messages are flushed into `<div id="flash">` from any fragment via `hx-swap-oob="true"`.
- Mutation routes return response headers from the shared `trigger(response, *events)` helper. Agreed event names:
  - `balance-stale` — accounts page + home-dashboard fortune card re-fetch.
  - `forecast-stale` — forecast page re-fetches its chart fragment.
  - `budget-stale` — budget page re-fetches its month summary table.
  - `audit-stale` — reserved for future audit viewer (not consumed in v1).
- `is_htmx(request)` returns `request.headers.get("HX-Request") == "true"`. Routers switch between full-page vs fragment responses on this flag; T-031..T-038 all reuse this helper.

## Validation / acceptance

`TestClient`-level assertions in `tests/integration/web/test_app.py` (BeautifulSoup, not full snapshots):

- `GET /healthz` → `200`, body is JSON with `status == "ok"`.
- `GET /` → `200`, response has `<html lang="en">`, `<script src*="htmx.org">`, `<script src*="plotly">`, and a `<link rel="stylesheet" href*="tailwind">`.
- `GET /static/app.css` → `200`, `content-type` starts with `text/css`.
- Jinja env has `money`, `date_fmt`, `dt_local`, `direction_badge` filters registered; a template that uses each renders without `UndefinedError`.
- `trigger(resp, "balance-stale", "forecast-stale")` sets `HX-Trigger` on `resp` to a JSON object (`{"balance-stale": true, "forecast-stale": true}`) so stacked events survive HTMX parsing.
- `is_htmx(request)` returns `False` without the header, `True` with `HX-Request: true`.
- Uvicorn entrypoint binds to `settings.host` which defaults to `127.0.0.1` — asserted by inspecting the start command in `justfile` and the `uvicorn.Config` used in `__main__.py` (unit test imports and introspects, no actual listen).

A11y basics seeded in `base.html`:

- `<html lang="en">`.
- `<main id="main">` with a visible skip link injected at the top (`<a class="sr-only focus:not-sr-only" href="#main">Skip to content</a>`) for keyboard users.
- `aria-live="polite"` on `<div id="flash">`.

## Risks & gotchas

- **127.0.0.1 only.** The uvicorn command must read `settings.host`; hardcoding `0.0.0.0` would violate `CLAUDE.md` and ADR-0005. Enforce in a unit test that imports the module and asserts the default host string.
- **Jinja autoescape must be on.** `Environment(autoescape=select_autoescape(["html"]))`. Any router rendering user-supplied strings (descriptions) without autoescape introduces XSS; add a smoke test that renders `<script>` in a description and asserts it is HTML-escaped.
- **Tailwind CDN output.** `tailwind.min.css` is sizeable; v1 accepts the cost (ADR-0002). A later ADR will revisit if a build step is justified.
- **HTMX swap identity.** Rows that will be swapped individually must carry a stable `id="txn-{{ txn.id }}"` on the `<tr>` — this is a convention T-031..T-038 must honour. Document the convention in `partials/_pagination.html`'s comments so future contributors do not improvise.
- **`HX-Trigger` JSON vs plain.** Multiple events require JSON form `{"ev1":true,"ev2":true}`. The `trigger()` helper handles this; routers must call it rather than setting the header directly.
- **python-multipart installed.** Form POSTs will 500 otherwise. Already pinned in T-001; a boot-time import check logs a clear message if missing.
- **Request-scoped connection.** `get_db()` yields a connection with `PRAGMA foreign_keys = ON`; close it in `finally`. Tests use a per-test temp SQLite file.
- **Static mount path.** Tests must `app.state.settings = ...` or similar so test rigs can override `database_url` without touching module-level state.

## Anti-template design-quality move

The baseline shell commits to a **two-tone editorial canvas** rather than the stock dashboard look:

- Define CSS custom properties in `app.css`: `--surface` (near-white warm), `--ink` (near-black cool), `--accent` (single oklch accent), `--muted`, `--rule`, `--radius-card`, `--space-section` (`clamp(2rem, 1rem + 4vw, 5rem)`). Everything else — hover, focus-visible rings, badges, dividers — composes against these.
- Pick a **typographic pairing** at this layer so routers inherit it: a serif display family for section titles (`<h1>`, `<h2>` in `base.html`) and a geometric sans for body/numerals; numeric cells use `font-variant-numeric: tabular-nums` via `_money.html`.
- Dividers are hairlines (`1px` with `--rule`), not shadow-stacked cards — a deliberate rejection of the shadcn-grid aesthetic called out in `rules/web/design-quality.md`.
- Focus ring: a 2px outline using `--accent`, drawn on `:focus-visible` only. All routers inherit; T-053 polishes but does not replace.

## Handoff notes

- T-031..T-038 each import `router = APIRouter(prefix="/<name>", tags=["<name>"])` from `src/budget_planner/web/routers/<name>.py` and are registered inside `create_app` via `app.include_router(...)`. The order of inclusion matches the nav order defined by T-039.
- T-039 replaces the body of `_dev_index.html` by extending `base.html` and filling `block nav` + `block main`. The `#main` and `#flash` ids defined here are the swap targets T-039 wires.
- Every mutating router must call `trigger(response, …)` with the agreed event names above; see "HTMX interactions". New event names require a line in this document before use.
- The `get_db` dependency is the single place a connection enters a router. Routers must not open their own connection.
