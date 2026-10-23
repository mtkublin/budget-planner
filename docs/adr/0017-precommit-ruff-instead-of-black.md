# ADR-0017: Pre-commit Stack & Using Ruff Instead of Black

- **Status**: Accepted
- **Date**: 2026-10-23

## Context

The initial requirements call for `black` for formatting (and equivalents in other languages). `ruff` now provides a `black`-compatible formatter plus linting, import-sorting, and more, in a single Rust-backed tool.

## Decision

Pre-commit hook stack:

- `ruff` — lint + import sort (replaces `flake8`, `isort`, parts of `pyupgrade`).
- `ruff-format` — formatter (output byte-for-byte compatible with `black`).
- `mypy --strict` — type checker.
- `pytest` (fast subset) — test guard against obvious regressions on commit.
- `sqlfluff` — SQL formatter + linter for migration and query files.
- `djlint` — Jinja template linter.
- `bandit` — Python security scanner.
- `detect-secrets` — prevent accidental secret commits.
- Standard `pre-commit-hooks` stdlib: trailing whitespace, EOF newline, large-file check, yaml/toml validate.

CI (`just ci`) also runs the full `pytest` suite with a 90% coverage gate.

## Consequences

- Fewer tools to configure; `ruff` replaces several.
- Faster hook execution.
- Still produces `black`-equivalent formatting, honouring the spirit of the requirement.

## Alternatives Considered

- **Keep `black` separately alongside `ruff`**: redundant since `ruff-format` is `black`-compatible.
- **`pyright` instead of `mypy`**: faster, but Microsoft-run; `mypy` has broader plugin ecosystem.
- **No pre-commit, CI-only checks**: slower feedback loop.
