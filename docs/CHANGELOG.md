# Changelog

## 2026-10-23
- T-001: scaffolded `uv`-managed Python 3.12 project (`pyproject.toml`, `uv.lock`, `.python-version`), source + test + migrations directory skeleton, placeholder `README.md`, and empty `.env.example`.
- T-002: added `justfile` recipe surface (install, dev, lint, format, typecheck, test, ci, migrate, seed, db-reset, install-hooks) and `.github/workflows/ci.yml` single-matrix-row pipeline running `just ci` with coverage artefact upload.
- T-003: wired pre-commit stack (`.pre-commit-config.yaml`), tool configs in `pyproject.toml` (`ruff`, `mypy --strict`, `pytest` + 90% coverage gate, `sqlfluff`, `djlint`, `bandit`), `detect-secrets` baseline, smoke test, and tolerant djlint call in `just lint` for the empty templates dir in Phase 0.
