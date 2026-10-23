# ADR-0004: Package Manager — uv

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

Use `uv` for dependency and virtual-environment management. Lockfile committed. Python version pinned via `.python-version` (`3.12`).

## Consequences

- Fast resolver (Rust-backed), 10-100x pip.
- One tool handles venv, lockfile, and Python version pin.
- `uv sync` reproducible across machines and CI.
- `pyproject.toml` native, no `requirements.txt` sprawl.

## Alternatives Considered

- **Poetry**: mature, widely known; slower; non-standard lockfile format.
- **pip-tools**: minimal; more ceremony around venv management.
- **PDM**: capable but smaller mindshare than uv in 2026.
