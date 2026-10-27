# ADR-0029: SQLite Connection Threading — `check_same_thread=False`, Per-Request Connection

- **Status**: Accepted
- **Date**: 2026-10-27
- **Related**: ADR-0003 (SQLite in v1), ADR-0022 (repository layer)

## Context

`src/budget_planner/db/connection.py` opened SQLite with the stdlib default `check_same_thread=True`. The web layer wires DB access as follows:

1. `src/budget_planner/web/deps.py:get_db` is a **synchronous generator dependency** that calls `get_connection(settings)` and `yield`s a connection, closing it in `finally`.
2. Route handlers (`routers/budget.py:index`, etc.) are `def` (synchronous).

FastAPI/Starlette dispatches sync dependencies and sync endpoints through anyio's `run_in_threadpool`. Two separate hops are made per request: one for the dependency, one for the endpoint. Anyio's worker pool is non-deterministic — the dependency may resolve on worker A, the endpoint may run on worker B. SQLite's default thread-check then raises:

```
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread.
The object was created in thread id X and this is thread id Y.
```

Observed on `/budget` under concurrent load (`xargs -P 20`): ~83% of requests failed with 500. Under purely serial load the bug is masked because anyio tends to reuse the one idle worker, so dependency and endpoint land on the same thread.

The thread check exists in stdlib `sqlite3` because a single `sqlite3.Connection` object is **not safe to use concurrently** from multiple threads (the handle has internal mutable state and the C API is single-threaded per handle). SQLite itself, since 3.3.1, is compiled thread-safe (`SQLITE_THREADSAFE=1` serialized mode by default). The stdlib check is a conservative guard, not a SQLite limitation.

Our pattern is already safe: every request opens its own connection via `get_db` and closes it in `finally`. Connections are never shared across requests. The only reason the check fires is that *within a single request* the connection crosses one worker-thread boundary (dependency → endpoint).

## Decision

Open SQLite connections with `check_same_thread=False` in `budget_planner.db.connection.get_connection`.

Keep the per-request connection lifecycle unchanged: `get_db` opens, request handles, `finally` closes. No pooling, no module-level shared handle, no attempt to share one connection across requests or threads.

## Consequences

- `/budget` (and every other route) stops 500-ing under concurrency.
- No API or schema change. One-line change in `db/connection.py`.
- We take on the burden the stdlib check was warning about: **a connection must not be used from two threads at the same time**. Our architecture already guarantees this because:
  - Connections are request-scoped (not module/app-state globals).
  - A single sync request runs on exactly one worker thread at a time; the dependency hop finishes before the endpoint hop starts. The thread may differ between hops, but there is no overlap.
  - Repositories receive the connection as a parameter and do not spawn threads.
- A new invariant for future code: never pass a `sqlite3.Connection` into a background thread, task group, or `asyncio.to_thread` call that could run concurrently with the request handler. If background work is needed, open a dedicated connection in that worker.

## Alternatives Considered

- **Make `get_db` and endpoints `async`, open connection inside the endpoint.** Larger refactor, loses the dependency injection seam used by tests to override settings/DB, and SQLite is still blocking I/O so `async def` buys nothing on the DB path.
- **Connection pool keyed by thread id (`threading.local`).** Hides connection lifecycle, complicates close/shutdown, and provides no benefit over per-request connections at this scale.
- **Pin the anyio threadpool to a single worker.** Serializes all requests through one thread, destroying concurrency.
- **Switch to `aiosqlite`.** Adds a dependency and an async surface for every repository call site. Not justified in v1 for a local-first single-user app.

## Follow-ups

- Add a regression test that exercises `/budget` (or a cheap route) with concurrent clients and asserts no 500s.
