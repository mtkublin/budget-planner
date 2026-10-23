# ADR-0016: Task Runner — just

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

Use `just` as the task runner. All developer commands exposed as `just <recipe>`:

- `just install`
- `just dev`
- `just test`
- `just lint`
- `just format`
- `just typecheck`
- `just ci`
- `just db-reset`
- `just migrate`
- `just seed`
- `just install-hooks`

## Consequences

- Cleaner syntax than Make; no tab-sensitivity, no implicit rules.
- Cross-platform (works on macOS, Linux, Windows).
- `just --list` is a self-documenting entry point for new contributors.

## Alternatives Considered

- **Make**: ubiquitous but archaic syntax; recipes grow brittle.
- **poe (poethepoet)**: Python-native via `pyproject.toml`; smaller mindshare.
- **Plain shell scripts in `scripts/`**: no self-documentation, order implicit.
