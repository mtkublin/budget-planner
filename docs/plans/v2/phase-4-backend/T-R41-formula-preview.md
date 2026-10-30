# T-R41 — `POST /recurring/formula/preview`

- **Phase**: 4 — Backend
- **Parallel-safe**: yes.
- **Depends on**: T-R10.
- **References**: ADR-0047 (formula shape), ADR-0056 §4.

## Context

Add-entry formula builder needs a live preview without persisting. Takes a draft term list; returns the computed value or an inline validation error. Idempotent; no DB write; must handle cycle detection + chained formulas + non-positive results identically to the save path.

## Deliverables

- `src/budget_planner/services/recurring/formula.py` gains:
  ```python
  @dataclass(frozen=True)
  class PreviewOk:
      amount_minor: int

  @dataclass(frozen=True)
  class PreviewError:
      code: Literal["cycle", "non_positive", "invalid_source", "empty"]
      message: str
      offending_term_index: int | None

  PreviewResult = PreviewOk | PreviewError

  def preview(
      conn: Connection,
      when: date,
      draft_rule_id: int | None,
      terms: Sequence[DraftTerm],
  ) -> PreviewResult: ...
  ```
- Router `POST /recurring/formula/preview` accepts a JSON body with the term shape; returns the Jinja fragment (success chip or inline error) + sets `HX-Reswap: innerHTML` on the preview region.
- Reuses existing `_sum_category_in_month`, `_apply_coefficient`, `validate_formula_sources` from ADR-0047 — no re-implementation.
- If `draft_rule_id` is None (new rule): run cycle detection as if the rule were new (empty predecessor set).
- If `draft_rule_id` is set (edit): include the existing rule's references + the draft's references in the cycle graph.
- Unit tests under `tests/unit/services/test_formula_preview.py`: empty terms → `empty`, single valid term → OK, chained formula depth 3 → OK (memoised), self-loop → `cycle`, indirect cycle through a chained formula → `cycle`, non-positive result → `non_positive`, invalid source id → `invalid_source`.
- Integration test under `tests/integration/web/test_formula_preview.py` covers 200 success + 422 error branches + response fragment shape.

## Acceptance criteria

- Coverage ≥ 95 % on the service module (edge-case density).
- Response time ≤ 50 ms for a 3-term chained formula on a seeded dev DB (profile with pytest-benchmark).
- No DB write (verified by audit-log count before/after).
- Error responses carry `code` + `offending_term_index` so the UI can highlight the bad term.

## Validation hook

```sh
pytest tests/unit/services/test_formula_preview.py --cov=src/budget_planner/services/recurring/formula.py --cov-fail-under=95
```

## Risks & gotchas

- Memoisation must be request-scoped; a module-level cache would retain stale sums across requests.
- The preview must honour `recurring_rule_overrides` on `when` (ADR-0046 formula sees non-consumed overrides); otherwise preview and save diverge.
- Cycle detection cost grows with graph size; stay O(V + E) via DFS with a visited set.

## Handoff notes

- T-R38 (Add entry modal) consumes this endpoint via HTMX. The debounce lives on the HTMX trigger.
- `services.recurring.promote_recurring` and `services.budget.committed_in_window` share the same primitives — any change to primitives must re-run their test suites.
