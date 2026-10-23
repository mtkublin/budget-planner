# Changelog

## 2026-10-23
- T-001: scaffolded `uv`-managed Python 3.12 project (`pyproject.toml`, `uv.lock`, `.python-version`), source + test + migrations directory skeleton, placeholder `README.md`, and empty `.env.example`.
- T-002: added `justfile` recipe surface (install, dev, lint, format, typecheck, test, ci, migrate, seed, db-reset, install-hooks) and `.github/workflows/ci.yml` single-matrix-row pipeline running `just ci` with coverage artefact upload.
