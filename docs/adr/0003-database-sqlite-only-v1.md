# ADR-0003: Database — SQLite Only in v1, DuckDB Attach Deferred

- **Status**: Accepted
- **Date**: 2026-10-23

## Context

The initial requirements list SQLite and DuckDB as preferred technologies. A dual OLTP + OLAP setup (SQLite primary, DuckDB attached read-only for analytics) was considered.

## Decision

Use SQLite only in v1. Defer DuckDB attach until analytics query performance becomes a bottleneck.

## Consequences

- Single storage engine, single query dialect, simpler mental model.
- Personal-scale data (expected < 100k rows across years) comfortably fits SQLite performance envelope.
- Analytics queries use the same connection; indexed queries are sufficient.
- If analytics view feels slow later, DuckDB can `ATTACH` the SQLite file read-only — no data migration needed.

## Alternatives Considered

- **SQLite + DuckDB from day 1**: premature; adds a second engine and dialect without proven need.
- **DuckDB only**: weaker concurrency story and less battle-tested for mutable workloads.
- **Postgres**: overkill for local-first personal app.
