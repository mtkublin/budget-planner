# ADR-0018: CI — Single Matrix Row (Python 3.12 + Ubuntu)

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

GitHub Actions runs a single matrix row: `ubuntu-latest` + Python 3.12. Pipeline runs `just ci`, which executes lint, typecheck, test with coverage, and a build check.

## Consequences

- Fast feedback, minimal CI minutes.
- No cross-version drift to debug for a personal application that is not a library.
- Can expand to `macos-latest` or additional Python versions if the project is open-sourced later.

## Alternatives Considered

- **Matrix (3.11, 3.12, 3.13) × (ubuntu, macos, windows)**: 9 jobs, 9× minutes, no v1 gain.
- **Add macOS only**: 2× cost, modest insurance for dev-machine parity; defer.
