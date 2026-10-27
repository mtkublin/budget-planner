# Budget Planner — developer commands.
# Discoverable via `just --list`.

set shell := ["bash", "-cu"]
set dotenv-load := true

# --- environment -----------------------------------------------------------

# Install runtime + dev deps, sync lockfile, install pre-commit hooks + Node dev toolchain.
install:
    uv sync --group dev
    uv run pre-commit install --install-hooks
    npm ci

# Install only the pre-commit hooks (no dependency sync).
install-hooks:
    uv run pre-commit install --install-hooks

# --- dev loop --------------------------------------------------------------

# Run FastAPI with hot reload. Binds 127.0.0.1 per ADR-0005.
dev:
    uv run uvicorn budget_planner.web.app:app \
      --reload --host 127.0.0.1 --port 8000

# Build Tailwind CSS once (purged + minified) → static/tailwind.css. See ADR-0027.
css:
    npm run css

# Rebuild Tailwind on save; run alongside `just dev`.
css-watch:
    npm run css:watch

# Run Playwright visual-regression snapshot suite. Opt-in; not part of `just ci`.
test-visual:
    uv run pytest tests/visual -m visual --override-ini="addopts=-ra --strict-config --strict-markers" --no-cov

# Refresh visual-regression baselines after an intentional design change.
test-visual-update:
    VISUAL_UPDATE=1 uv run pytest tests/visual -m visual --override-ini="addopts=-ra --strict-config --strict-markers" --no-cov

# --- quality gates ---------------------------------------------------------

# Run all linters: ruff, sqlfluff, djlint.
# djlint exits 2 when the target directory is empty (Phase 0 reality); tolerate
# that specific "no files" message so pre-Phase-3 CI stays green. Any real
# lint error still fails because the string check only matches the empty case.
lint:
    uv run ruff check src tests
    uv run sqlfluff lint migrations
    out=$(uv run djlint src/budget_planner/web/templates --check 2>&1); status=$?; if [ $status -ne 0 ] && ! echo "$out" | grep -q "No files to check"; then echo "$out" >&2; exit $status; fi; echo "$out"
    npm run stylelint --silent

# Auto-fix formatting + simple lint issues.
format:
    uv run ruff format src tests
    uv run ruff check src tests --fix
    uv run sqlfluff fix migrations
    out=$(uv run djlint src/budget_planner/web/templates --reformat 2>&1); status=$?; if [ $status -ne 0 ] && ! echo "$out" | grep -q "No files to check"; then echo "$out" >&2; exit $status; fi; echo "$out"

# mypy --strict over the package + tests.
typecheck:
    uv run mypy src tests

# Full pytest suite with coverage. 90% gate wired here and in CI.
test:
    uv run pytest

# Everything CI runs. Keep deterministic — no network except frankfurter mocks.
ci: lint typecheck test

# --- database --------------------------------------------------------------

# Apply all pending SQL migrations. Implemented in Phase 1 (T-010).
migrate:
    uv run python -m budget_planner.db.migrate

# Seed system data (default categories, demo accounts). Implemented in Phase 1 (T-012).
seed:
    uv run python -m budget_planner.db.seed

# Nuke and recreate the dev DB from scratch. Destructive.
db-reset:
    rm -f data/budget.sqlite data/budget.sqlite-wal data/budget.sqlite-shm
    just migrate
    just seed
