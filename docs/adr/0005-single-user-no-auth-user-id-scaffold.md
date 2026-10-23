# ADR-0005: Single User, No Auth, user_id Scaffolded

- **Status**: Accepted
- **Date**: 2026-10-23

## Context

v1 runs locally for a single user. Future deployment is possible; adding multi-user support later should not require a schema overhaul.

## Decision

- No authentication in v1.
- The FastAPI server binds to `127.0.0.1` (not `0.0.0.0`) to avoid accidental LAN exposure.
- Every user-owned table has a `user_id` column (nullable, defaults to `1`). A single `users` row seeded with `id=1, name='default'`.
- The `user_id` column is unused by application logic in v1 but reserved for future multi-user queries.

## Consequences

- Zero friction for local use.
- Schema is forward-compatible with multi-user auth without data migrations touching every row.
- A later ADR will cover auth strategy when it is added.

## Alternatives Considered

- **No `user_id` scaffold**: pure YAGNI; costs a schema migration touching every table later.
- **Full auth now**: weeks of work for no v1 value.
