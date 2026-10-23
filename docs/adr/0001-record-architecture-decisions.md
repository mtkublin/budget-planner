# ADR-0001: Record Architecture Decisions

- **Status**: Accepted
- **Date**: 2026-10-23

## Context

We need a lightweight way to capture meaningful architecture / product decisions so that future agents and contributors can pick up the project without re-deriving tradeoffs from scratch.

## Decision

Use Architecture Decision Records (ADRs) stored under `docs/adr/`, numbered sequentially, in Markdown. Each ADR has: Status, Date, Context, Decision, Consequences, Alternatives Considered.

An ADR is required when a decision has a meaningful tradeoff or constraints future work. Trivial choices (variable names, filenames) are not ADRs.

## Consequences

- Every meaningful decision is discoverable in one place.
- PRs that change a decision must update or supersede the relevant ADR.
- Agents handed a task can read the related ADR(s) linked from `docs/tasks.md`.

## Alternatives Considered

- No ADRs — rejected; context evaporates on handoffs.
- Confluence/Notion — rejected; local repo must be self-sufficient.
