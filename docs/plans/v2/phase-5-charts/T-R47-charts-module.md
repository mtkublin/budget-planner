# T-R47 — `charts.py` module

- **Phase**: 5 — Charts
- **Sequential**: blocks T-R48, T-R49, T-R50.
- **Depends on**: Phase 2 primitives.
- **References**: ADR-0054 §1, §2.

## Context

Replace Plotly with a tiny pure-Python module that returns SVG geometry (points, path `d` strings, axis labels, gridlines, tooltip anchors). Jinja consumes the geometry; the browser renders inline SVG. Keeps the "server is source of truth" principle and removes 2 MB of JS from the critical path.

## Deliverables

- `src/budget_planner/web/charts.py` with three functions, all pure:

  ```python
  @dataclass(frozen=True)
  class LineAreaChart:
      path_d: str
      area_d: str
      annotations: tuple[Annotation, ...]
      x_labels: tuple[str, ...]
      y_labels: tuple[str, ...]
      gridlines: tuple[Gridline, ...]
      viewbox: str

  def line_area(points: Sequence[Point], outliers: Sequence[Annotation] = ()) -> LineAreaChart: ...

  @dataclass(frozen=True)
  class GroupedBarsChart:
      groups: tuple[BarGroup, ...]
      x_labels: tuple[str, ...]
      y_labels: tuple[str, ...]
      viewbox: str

  def grouped_bars(groups: Sequence[BarGroupInput], max_bars_per_group: int = 2) -> GroupedBarsChart: ...

  @dataclass(frozen=True)
  class HorizontalBarsChart:
      bars: tuple[HBar, ...]
      viewbox: str

  def horizontal_bars(items: Sequence[HBarInput]) -> HorizontalBarsChart: ...
  ```

- Supporting dataclasses in the same module: `Point`, `Annotation`, `Gridline`, `BarGroup`, `BarGroupInput`, `HBar`, `HBarInput`.
- `_nice_axis(min, max, target_ticks=5)` helper that returns `(min_rounded, max_rounded, step)` using the standard "1 · 2 · 5 × 10^k" nice-number algorithm.
- Unit tests at ≥ 95 % coverage under `tests/unit/web/test_charts.py`: representative inputs for each shape, degenerate cases (empty, single point, flat line, negative values).

## Acceptance criteria

- All three functions return frozen dataclasses; mutation attempts raise.
- `_nice_axis(0, 1234, target_ticks=5)` returns `(0, 1500, 300)` or an equivalent nice step.
- `line_area` with an empty input returns an empty `path_d` and valid `viewbox` without raising.
- `pytest tests/unit/web/test_charts.py --cov=src/budget_planner/web/charts` ≥ 95 %.

## Validation hook

```sh
pytest tests/unit/web/test_charts.py --cov=src/budget_planner/web/charts.py --cov-fail-under=95
```

## Risks & gotchas

- SVG `viewBox` + path `d` must stay numeric strings (no scientific notation) so the browser renders consistently. Format with `{:.3f}`.
- Gridlines render as separate `<line>` elements so CSS can style them; do not merge into the main path.
- Annotation positioning uses the `_nice_axis` output as the anchor — recomputing in the template would drift.
- Tooltip anchor points are precomputed centroids; the template reads them from `data-anchor-x` / `data-anchor-y`.

## Handoff notes

- T-R48 (Forecast chart template) consumes `LineAreaChart`; T-R49 (Analytics) consumes the other two.
- Future `sparkline(points)` for the Accounts trend column reuses the same `_nice_axis` helper plus a narrow-aspect `line_area` variant — do not reinvent.
