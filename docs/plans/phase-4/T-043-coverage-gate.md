# T-043 — Coverage gate

> Phase 4 — Testing. Status: pending.

## Purpose

Make 90% line + branch coverage a hard gate on `just test` and `just ci`. The gate turns the unit/integration/e2e tests from T-040/T-041/T-042 into a non-negotiable floor; a dropped-below-90 run fails the pipeline. This closes the Phase 4 exit criteria in [`docs/implementation_plan.md`](../../implementation_plan.md).

## Inputs / prerequisites

- Upstream code already covered by:
  - T-040 — unit tests under [`tests/unit/`](../../../tests/unit/).
  - T-041 — integration tests under [`tests/integration/`](../../../tests/integration/).
  - T-042 — e2e smoke tests under [`tests/e2e/`](../../../tests/e2e/).
- Existing `justfile` + CI from T-002 (`just ci` already wires `just test` and `just lint`).
- `pyproject.toml` coverage config stub from T-003 (threshold placeholder).
- ADRs: [ADR-0018](../../adr/0018-ci-single-matrix-row.md), [ADR-0019](../../adr/0019-soft-delete-and-audit-log.md), [ADR-0021](../../adr/0021-functional-style-no-oop.md).
- Testing stack already provisioned in T-001: `pytest`, `pytest-cov`.

## Deliverables

- Config diff in `pyproject.toml`:

  ```toml
  [tool.coverage.run]
  source = ["src/budget_planner"]
  branch = true
  parallel = true
  omit = [
    "src/budget_planner/web/templates/*",
    "src/budget_planner/__main__.py",
  ]

  [tool.coverage.report]
  fail_under = 90
  show_missing = true
  skip_covered = false
  precision = 2
  exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "\\.\\.\\.",
  ]

  [tool.coverage.html]
  directory = "build/coverage-html"

  [tool.coverage.xml]
  output = "build/coverage.xml"
  ```

- `justfile` diff (updates to existing recipes, no new ones):

  ```make
  test:
      uv run pytest \
          --cov=src/budget_planner \
          --cov-branch \
          --cov-report=term-missing \
          --cov-report=xml:build/coverage.xml \
          --cov-report=html:build/coverage-html \
          --cov-fail-under=90 \
          tests

  ci: lint typecheck test
  ```

- CI diff in `.github/workflows/ci.yml` (artifact upload already landed in T-002; this step confirms the path):

  ```yaml
  - name: Upload coverage report
    if: always()
    uses: actions/upload-artifact@v4
    with:
      name: coverage-report
      path: |
        build/coverage.xml
        build/coverage-html/
  ```

- No new test files. This task is config + wiring only.

## Scope & test matrix

Not a test-authoring task. The matrix is the **gate rule set**:

| Check | Where | Fails build if |
|-------|-------|----------------|
| Total line coverage ≥ 90% | `pytest --cov-fail-under=90` | Below 90% total |
| Branch coverage enabled | `[tool.coverage.run] branch = true` | Branch mode off |
| Scope restricted | `source = ["src/budget_planner"]` | Scope widened to include tests/templates |
| Omit list intact | `omit = [...]` | Templates/`__main__` re-added by accident |
| CI artifact uploaded | `.github/workflows/ci.yml` | Artifact step missing |

## Fixtures / seed data

None. This task relies entirely on the fixtures introduced by T-040/T-041/T-042.

## Validation / acceptance

Commands:

```sh
just test              # must fail if coverage < 90%
just ci                # must call just test, must fail on gate
uv run pytest --cov=src/budget_planner --cov-branch --cov-fail-under=90 tests
```

Acceptance:

1. Running `just test` with the full suite reports ≥ 90% line + branch coverage. The report shows per-module coverage; no module is excluded except the ones in the `omit` list.
2. Temporarily removing a test file drops coverage below 90% and causes `just test` to **fail** with exit code 2 (coverage threshold not met). Revert.
3. `just ci` fails on the same simulated drop.
4. CI artifact `coverage-report` is produced on both success and failure (`if: always()`).
5. HTML report at `build/coverage-html/index.html` is browsable locally; it is `.gitignore`d.
6. Audit assertions required by [ADR-0019](../../adr/0019-soft-delete-and-audit-log.md) are not relaxed to meet the gate — if coverage drops because of a missed audit path, the fix is a test, not an `omit`.

## Risks & gotchas

- **Don't inflate coverage with trivial tests.** The 90% number is a floor for meaningful tests, not a target gamed with `assert True`. Review in Phase 5 code review.
- **Branch coverage** matters because the functional style (ADR-0021) uses expression-level branching heavily (`x if y else z`, `match`); line-only coverage would under-report missed paths.
- **Don't cover Jinja** — template rendering is validated structurally in T-042. Coverage scope stays on `src/budget_planner` (Python only).
- **Don't `omit` business modules** to make the number — services and repositories must be covered on their own merit.
- **`parallel = true`** is required if `pytest-xdist` is used; without it, coverage data files from each worker overwrite each other. Add `coverage combine` to the test recipe only if xdist is enabled in CI.
- **`--cov-fail-under` on both ends** — the CLI flag and `fail_under` in `pyproject.toml` are both set deliberately. CLI wins when present, but the config value protects IDE runs.
- **SQLite file contention under xdist** — reconfirmed from T-040/T-041 risk list; `tmp_path` fixtures only.
- **E2E flakiness** — if Playwright is adopted in T-042, keep `retries=2` in CI; a flake should not slide into a coverage drop.

## Handoff notes

Phase 5 polish tasks assume:

- The 90% gate is live and failing fast on PRs.
- New code introduced during polish ships with tests sufficient to not drop the number. If polish genuinely cannot be unit-tested (e.g. CSS tweaks), it is covered by the existing e2e flows or an added structural assertion in T-042.
- The `omit` list is **closed**. Expanding it requires an ADR explaining why a module cannot be tested.
- Coverage artifact in CI is the one source of truth; local reports are advisory.
