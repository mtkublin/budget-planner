# T-070 — Redirect Map

> Phase 6 — UX redesign. Status: pending.

## Purpose

Preserve every existing bookmark. The old page URLs (`/transactions`, `/planned`, `/recurring`, `/categories`, `/analytics`) return `302` redirects to their new homes. HTMX fragment URLs (`/transactions/table`, `/planned/table`, `/recurring` list) are already aliased by T-064 — this task adds the page-level redirects, documents the full map, and adds integration tests that nail each one down.

## Inputs / prerequisites

- Upstream tasks: T-064 (ledger lives at `/ledger`), T-066 (`/budget` has the breakdown section), T-067 (settings drawer exists).
- Binding standard: [`ADR-0023`](../../../adr/0023-ux-redesign-information-architecture.md) — old → new URL map.
- Adjacent standards: `rules/web/patterns.md` (URL as state).

## Deliverables

Updated files:

- `src/budget_planner/web/routers/transactions.py`:
  - `GET /transactions` → `RedirectResponse(url="/ledger?view=actual", status_code=302)`.
  - `GET /transactions/table` → `RedirectResponse(url="/ledger/table?view=actual&…", status_code=307)` (307 preserves method and query; owned by T-064 but confirmed here).
- `src/budget_planner/web/routers/planned.py`:
  - `GET /planned` → `302` to `/ledger?view=planned`.
  - `GET /planned/table` → `307` to `/ledger/table?view=planned&…`.
- `src/budget_planner/web/routers/recurring.py`:
  - `GET /recurring` → `302` to `/ledger?view=recurring`.
  - `GET /recurring` (fragment variant) → `307` to `/ledger/table?view=recurring&…`.
- `src/budget_planner/web/routers/categories.py`:
  - `GET /categories` → `302` to `/` with a flash: `Categories moved to Settings → Categories. Open with ⚙ or g s.`
- `src/budget_planner/web/routers/analytics.py`:
  - `GET /analytics` → `302` to `/budget#breakdown`.
  - Fragment analytics routes (`/analytics/spend`, `/analytics/trend`, `/analytics/cashflow`) preserve their current paths — ADR-0023 keeps them for the Budget breakdown fragments; T-066 may call them directly.
- `src/budget_planner/web/routers/budget.py`:
  - `GET /budget/manage` → `302` to `/budget#rules`.

New files:

- `tests/integration/web/test_redirects.py` — covers every alias.

Not deliverables:

- No deletion of old templates. They remain until a Phase 7 cleanup task.
- No `301` upgrades. Keep at `302` for one release; a follow-up task flips to `301` once the IA is stable.

## Step-by-step

1. **Audit current routes.** `grep -nE '@router.get' src/budget_planner/web/routers/` and list every path. Confirm the only page-level survivors moving under this task are: `/transactions`, `/planned`, `/recurring`, `/categories`, `/analytics`, `/budget/manage`.
2. **Add redirects.** Each handler is one line:
   ```python
   @router.get("/transactions")
   def transactions_page() -> RedirectResponse:
       return RedirectResponse(url="/ledger?view=actual", status_code=302)
   ```
   Return `RedirectResponse` directly from the FastAPI handler; do not wrap in `Response`.
3. **Preserve flashes.** For `/categories`, set a flash via the existing flash helper so the user sees a one-time pointer to the drawer.
4. **HTMX fragment aliases.** These are already in T-064. Confirm they still return 307 (not 302) because 307 preserves method + body + query, which matters for POST-via-HTMX. For page-level GET redirects, 302 is fine.
5. **Write the test module.** `tests/integration/web/test_redirects.py` parametrised over the map:
   ```python
   OLD_TO_NEW = [
       ("/transactions", 302, "/ledger?view=actual"),
       ("/planned",      302, "/ledger?view=planned"),
       ("/recurring",    302, "/ledger?view=recurring"),
       ("/categories",   302, "/"),
       ("/analytics",    302, "/budget#breakdown"),
       ("/budget/manage",302, "/budget#rules"),
   ]
   ```
   For fragment aliases, a second parametrised test confirms `/transactions/table?date_from=…` after redirect-follow returns the same bytes as `/ledger/table?view=actual&date_from=…`.
6. **Update docs.** Add the full map to `README.md` under a "Migration" subsection — but that README edit is owned by T-072. Here, only confirm the ADR-0023 map matches reality.

## Validation / acceptance

- `GET /transactions` returns `302` with `Location: /ledger?view=actual`.
- `GET /planned` returns `302` with `Location: /ledger?view=planned`.
- `GET /recurring` returns `302` with `Location: /ledger?view=recurring`.
- `GET /categories` returns `302` with `Location: /` and a flash set.
- `GET /analytics` returns `302` with `Location: /budget#breakdown`.
- `GET /budget/manage` returns `302` with `Location: /budget#rules`.
- `GET /transactions/table?date_from=2026-10-01` returns `307` and, when followed, the body equals `GET /ledger/table?view=actual&date_from=2026-10-01`.
- Same for `/planned/table` → `/ledger/table?view=planned&…` and `/recurring` → `/ledger/table?view=recurring&…`.
- Integration test `test_redirects.py::test_fragment_aliases_return_same_bytes` passes.
- No old URL returns `404`.

## Risks & gotchas

- **Fragment aliases must be 307, not 302.** HTMX relies on method/body preservation; 302 downgrades POST to GET on some clients. Page-level redirects for GET-only are fine at 302.
- **Flash on `/categories`.** Make sure the flash middleware runs before the redirect — set the flash on the request's session, then redirect; the flash renders on the next page load.
- **Hash fragments in redirect targets.** `/analytics` → `/budget#breakdown` works only if the browser respects the hash on redirect. FastAPI will send the `Location: /budget#breakdown` header; most browsers scroll to the hash. If some don't, the Budget page can read `?section=breakdown` as a fallback and scroll via JS — add only if the test fails.
- **Catching repo-wide usage.** `grep -rn '/transactions\|/planned\|/recurring\|/categories\|/analytics' src/` and update any internal `url_for` or template links to point at the new homes. Internal links shouldn't rely on redirects.
- **One-release window.** Keep `302` until the ADR-0023 follow-up task flips to `301`. Don't flip early.

## Handoff notes

- Hand-off to T-072: add the migration note to README referencing this task and ADR-0023.
- The old templates (`transactions/index.html`, etc.) are **not** deleted. A Phase 7 cleanup task removes them once a release has passed with the aliases in place.
- Commit shape: `feat(T-070): legacy URL redirects + fragment aliases + redirect integration tests`.
