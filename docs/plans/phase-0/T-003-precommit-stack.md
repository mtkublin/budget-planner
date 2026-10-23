# T-003 — Pre-commit Stack

> Phase 0 — Repository Bootstrap. Status: pending.

## Purpose

Wire the full write-time quality gate: `ruff` (lint + import sort), `ruff-format`, `mypy --strict`, a fast `pytest` subset, `sqlfluff`, `djlint`, `bandit`, `detect-secrets`, and the standard pre-commit stdlib hooks. Land the paired `[tool.*]` configuration blocks in `pyproject.toml` so each tool behaves identically on dev machines and in CI. From this point forward, every commit is linted, typed, and smoke-tested before it reaches `main`.

## Inputs / prerequisites

- Upstream tasks:
  - [T-001 — Repository scaffolding](T-001-repository-scaffolding.md) — `pyproject.toml` exists; `src/`, `tests/`, `migrations/` scaffolded.
  - [T-002 — Justfile + CI](T-002-justfile-and-ci.md) — `just install-hooks` recipe exists.
- ADRs that constrain the choices:
  - [`ADR-0017` — Pre-commit stack & using Ruff instead of Black](../../adr/0017-precommit-ruff-instead-of-black.md)
  - [`ADR-0018` — CI: single matrix row](../../adr/0018-ci-single-matrix-row.md) (CI runs the same tools)
  - [`ADR-0021` — Functional style, no gratuitous OOP](../../adr/0021-functional-style-no-oop.md) (constrains mypy settings — strict is mandatory)
- Required local tools:
  - `uv >= 0.4` (invokes every hook via `uv run`).
  - `pre-commit >= 3.8` (dev dep from T-001).

> Note on tasks.md: the T-003 line in `docs/tasks.md` cites ADR-0020 (import deferred). That ADR is about export-vs-import scope, not pre-commit tooling. The correct references are ADR-0017 (and secondarily ADR-0018). Use the ones listed above.

## Deliverables

- `.pre-commit-config.yaml` at repo root — the hook definitions.
- `.secrets.baseline` at repo root — baseline for `detect-secrets`.
- `pyproject.toml` additions:
  - `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`
  - `[tool.mypy]`
  - `[tool.pytest.ini_options]`
  - `[tool.coverage.run]`, `[tool.coverage.report]`
  - `[tool.sqlfluff.core]`, `[tool.sqlfluff.rules]`
  - `[tool.djlint]`
  - `[tool.bandit]`
- No source code changes under `src/`.

## Step-by-step

1. Append the following tool-config blocks to `pyproject.toml` (preserve the existing `[project]`, `[dependency-groups]`, `[build-system]`, `[tool.hatch.*]`, `[tool.uv]` blocks from T-001):

   ```toml
   # ---------------------------------------------------------------------------
   # ruff — lint + format + import sort
   # ---------------------------------------------------------------------------
   [tool.ruff]
   line-length = 100
   target-version = "py312"
   src = ["src", "tests"]
   extend-exclude = ["migrations/*.sql"]

   [tool.ruff.lint]
   # Enabled rule groups (see https://docs.astral.sh/ruff/rules/).
   select = [
     "E", "F", "W",         # pycodestyle + pyflakes
     "I",                   # isort
     "B",                   # bugbear
     "UP",                  # pyupgrade
     "SIM",                 # simplify
     "RET",                 # return
     "PTH",                 # use pathlib
     "N",                   # pep8-naming
     "ANN",                 # type annotations required
     "ASYNC",
     "S",                   # bandit-lite (complements standalone bandit)
     "C4",                  # comprehensions
     "DTZ",                 # datetime timezone
     "TID",                 # tidy imports
     "ARG",                 # unused arg
     "ERA",                 # eradicate commented-out code
     "PL",                  # pylint subset
     "RUF",                 # ruff-specific
   ]
   ignore = [
     "ANN401",              # dynamic Any allowed in explicit kwargs forwarding
     "PLR0913",             # function arg count — services take many deps
     "S101",                # assert is fine in tests (per-file-ignores reinforces)
   ]

   [tool.ruff.lint.per-file-ignores]
   "tests/**/*.py" = ["S101", "PLR2004", "ANN"]
   "src/budget_planner/db/migrate.py" = ["S608"]  # dynamic SQL permitted here

   [tool.ruff.lint.isort]
   known-first-party = ["budget_planner"]
   combine-as-imports = true

   [tool.ruff.format]
   quote-style = "double"
   indent-style = "space"
   line-ending = "lf"
   skip-magic-trailing-comma = false

   # ---------------------------------------------------------------------------
   # mypy — strict
   # ---------------------------------------------------------------------------
   [tool.mypy]
   python_version = "3.12"
   strict = true
   warn_unreachable = true
   warn_no_return = true
   disallow_any_generics = true
   check_untyped_defs = true
   no_implicit_optional = true
   explicit_package_bases = true
   mypy_path = ["src"]
   packages = ["budget_planner", "tests"]
   plugins = ["pydantic.mypy"]

   [[tool.mypy.overrides]]
   module = ["plotly.*", "sqlfluff.*", "djlint.*", "pandas.*", "pyarrow.*"]
   ignore_missing_imports = true

   [tool.pydantic-mypy]
   init_forbid_extra = true
   init_typed = true
   warn_required_dynamic_aliases = true

   # ---------------------------------------------------------------------------
   # pytest + coverage
   # ---------------------------------------------------------------------------
   [tool.pytest.ini_options]
   minversion = "8.0"
   testpaths = ["tests"]
   addopts = [
     "-ra",
     "--strict-config",
     "--strict-markers",
     "--cov=src/budget_planner",
     "--cov-report=term-missing",
     "--cov-report=xml",
     "--cov-report=html",
     "--cov-fail-under=90",
   ]
   markers = [
     "unit: fast unit tests (default)",
     "integration: database or HTTP-backed tests",
     "e2e: full-stack smoke tests",
   ]
   asyncio_mode = "auto"
   filterwarnings = [
     "error",
     "ignore::DeprecationWarning:plotly.*",
   ]

   [tool.coverage.run]
   branch = true
   source = ["src/budget_planner"]
   omit = ["src/budget_planner/__main__.py"]

   [tool.coverage.report]
   skip_covered = false
   show_missing = true
   exclude_lines = [
     "pragma: no cover",
     "raise NotImplementedError",
     "if TYPE_CHECKING:",
     "if __name__ == .__main__.:",
   ]

   # ---------------------------------------------------------------------------
   # sqlfluff — SQL lint + format
   # ---------------------------------------------------------------------------
   [tool.sqlfluff.core]
   dialect = "sqlite"
   templater = "raw"
   max_line_length = 100
   exclude_rules = ["L034"]  # select-ordering is noisy for migrations

   [tool.sqlfluff.rules]
   capitalisation.keywords = "upper"
   capitalisation.identifiers = "lower"
   capitalisation.functions = "upper"
   capitalisation.literals = "upper"

   # ---------------------------------------------------------------------------
   # djlint — Jinja template lint
   # ---------------------------------------------------------------------------
   [tool.djlint]
   profile = "jinja"
   max_line_length = 120
   indent = 2
   format_css = true
   format_js = false

   # ---------------------------------------------------------------------------
   # bandit — security scan
   # ---------------------------------------------------------------------------
   [tool.bandit]
   exclude_dirs = ["tests", ".venv", "migrations"]
   skips = ["B101"]  # assert in tests (also skipped by per-file-ignore in ruff)
   ```

2. Create `.pre-commit-config.yaml` at repo root:

   ```yaml
   # Pre-commit hook stack. Pinned revs; bump via `pre-commit autoupdate` quarterly.
   default_language_version:
     python: python3.12

   repos:
     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v4.6.0
       hooks:
         - id: trailing-whitespace
         - id: end-of-file-fixer
         - id: check-yaml
         - id: check-toml
         - id: check-added-large-files
           args: [--maxkb=500]
         - id: check-merge-conflict
         - id: mixed-line-ending
           args: [--fix=lf]

     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.6.9
       hooks:
         - id: ruff
           args: [--fix]
         - id: ruff-format

     - repo: https://github.com/pre-commit/mirrors-mypy
       rev: v1.11.2
       hooks:
         - id: mypy
           additional_dependencies:
             - pydantic>=2.9
             - pydantic-settings>=2.6
             - types-python-dateutil>=2.9
             - pandas-stubs>=2.2
           args: [--config-file=pyproject.toml]
           pass_filenames: false
           files: ^(src|tests)/

     - repo: https://github.com/sqlfluff/sqlfluff
       rev: 3.1.1
       hooks:
         - id: sqlfluff-lint
           files: \.sql$
         - id: sqlfluff-fix
           files: \.sql$

     - repo: https://github.com/djlint/djLint
       rev: v1.35.2
       hooks:
         - id: djlint-jinja
           files: \.html$

     - repo: https://github.com/PyCQA/bandit
       rev: 1.7.10
       hooks:
         - id: bandit
           args: [--configfile=pyproject.toml, --recursive, src]
           pass_filenames: false

     - repo: https://github.com/Yelp/detect-secrets
       rev: v1.5.0
       hooks:
         - id: detect-secrets
           args: [--baseline, .secrets.baseline]

     - repo: local
       hooks:
         - id: pytest-fast
           name: pytest (fast subset)
           entry: uv run pytest -q -m "not integration and not e2e" --no-cov
           language: system
           pass_filenames: false
           stages: [pre-commit]
   ```

   Rationale:
   - `pytest-fast` is a `local` hook invoked via `uv run`; it bypasses coverage to stay snappy and skips integration/e2e markers. The full suite runs in `just test` / CI.
   - `mypy` uses `pass_filenames: false` so it always type-checks the package rather than drive-by edits. `additional_dependencies` must include every runtime dep whose stubs mypy loads at hook time.
   - `detect-secrets` requires a baseline — generated in step 3.

3. Generate the detect-secrets baseline:

   ```sh
   uv run detect-secrets scan --exclude-files 'uv\.lock|htmlcov/|\.secrets\.baseline' > .secrets.baseline
   ```

4. Install the hooks and run the full stack:

   ```sh
   just install-hooks        # alias for `uv run pre-commit install --install-hooks`
   uv run pre-commit run --all-files
   ```

   First run downloads hook envs — expect ~1 minute. Fix anything that trips (empty files from T-001 should be clean; `end-of-file-fixer` may touch `.gitkeep` files — commit the fix).

5. Confirm `just ci` composition:

   ```sh
   just ci
   ```

   This now runs the full pipeline (lint, typecheck, test w/ coverage ≥ 90% — currently 0 tests, so this will fail on the gate until Phase 2 tests exist). That is acceptable for Phase 0; CI will remain red for coverage until Phase 4 raises the bar. Phase 0 exit criterion is specifically: `just --list` self-documents and the CI workflow runs the pipeline — not that coverage is already green.

   Interim mitigation (if the agent wants a green bootstrap commit): add a single trivial test under `tests/unit/test_smoke.py`:

   ```python
   def test_package_importable() -> None:
       import budget_planner

       assert budget_planner.__name__ == "budget_planner"
   ```

   Then coverage computes against a near-empty package and passes trivially (0/0 = 100%).

6. Commit (final step after validation passes):

   ```sh
   git add .pre-commit-config.yaml .secrets.baseline pyproject.toml
   git add tests/unit/test_smoke.py   # if added
   git commit -m "feat(T-003): wire pre-commit stack and strict tooling configs"
   ```

## Interfaces / contracts

- Tool configs live in `pyproject.toml` under the `[tool.*]` blocks above. Downstream tasks extend, do not duplicate (do not add `.ruff.toml`, `mypy.ini`, `pytest.ini`, etc.).
- Coverage source path: `src/budget_planner`. All new code must live under that path to count.
- Coverage threshold: 90% (`--cov-fail-under=90`). Raise only via a new ADR.
- mypy strict mode is non-negotiable per ADR-0021.
- Pre-commit entry point for CI parity: `uv run pre-commit run --all-files` (not run in CI directly; CI relies on `just ci`).
- Secrets baseline file: `.secrets.baseline`. Any new false-positive must be audited and re-baselined with `detect-secrets audit`.
- Ruff line length: `100`. Downstream agents should not override.

## Validation / acceptance

Commands that must pass:

- `uv run pre-commit run --all-files` — exit code 0 after any auto-fixes are staged.
- `uv run ruff check src tests` — exit code 0.
- `uv run ruff format --check src tests` — exit code 0.
- `uv run mypy src tests` — exit code 0.
- `uv run sqlfluff lint migrations` — exit code 0 (no SQL yet; sqlfluff tolerates empty inputs).
- `uv run bandit -r src -c pyproject.toml` — exit code 0.
- `uv run detect-secrets scan --baseline .secrets.baseline` — reports no new secrets.
- `uv run pytest -q` — passes (either 0 tests + gated 100% coverage trick, or the smoke test from step 5).

Docs updates (CLAUDE.md handoff checklist):

- Prefix the T-003 line in `docs/tasks.md` with `✅`.
- Append a dated line to `docs/CHANGELOG.md` noting the hook stack + coverage gate.
- Reference ADR-0017 in the commit message. No new ADR required.

## Risks & gotchas

- `pre-commit` creates isolated environments per hook, which do not share your `uv` venv. The `local` `pytest-fast` hook invokes `uv run` to escape that — do not convert it to an upstream repo.
- `mypy` strict + `pydantic.mypy` plugin requires every runtime dep whose types mypy inspects to be present in the hook `additional_dependencies` list. Add new deps to that list when they land, not later.
- `--strict-config` in pytest fails fast on any unknown `addopts` or marker. Keep `markers` in sync when new markers (`e2e`, `integration`) are introduced.
- `filterwarnings = ["error"]` turns deprecation warnings into test failures. If a third-party library emits one, add a targeted ignore like the Plotly line above — do not blanket-silence.
- `detect-secrets` baseline must be regenerated whenever a legitimate secret-like token (fixture, example) lands. Use `uv run detect-secrets audit .secrets.baseline`.
- `djlint-jinja` runs on `.html` files; the templates dir is empty in Phase 0, which is fine — the hook silently no-ops.
- First `pre-commit run --all-files` is slow (hook envs cached in `~/.cache/pre-commit`). Second run should be <5 s.
- `check-added-large-files` cap of 500kB blocks accidental SQLite commits; adjust only if genuinely needed.

## Handoff notes

- T-004 adds the config module; it must pass `ruff`, `mypy --strict`, and `bandit`. Expect annotations on every function and `pydantic-settings` typed fields.
- Phase 1 (T-011) adds `.sql` files under `migrations/`; `sqlfluff` config here already targets `sqlite` dialect so no further changes needed.
- Phase 3 adds Jinja templates; `djlint` config here matches `jinja` profile.
- Phase 4 (T-043) only tightens the coverage gate if needed — the mechanism is already in place via `--cov-fail-under=90`.
- Any ADR-worthy deviation (e.g. bumping line length, loosening strict mypy) must land as a new ADR before being changed here.
