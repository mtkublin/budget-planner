# ADR-0059 — v2: Pace-tag rule for Today hero + pace_tag macro

- **Status**: Accepted
- **Date**: 2026-10-28
- **Amends**: ADR-0041 (budget period anchor window), ADR-0051 (v2 IA).
- **Related**: handoff `docs/application_redesign_handoff/docs/07-open-items.md`.

## Context

Today hero shows a pace tag — "On track", "Tight", "Overdue" — summarising whether spend is tracking plan for the anchor window. The handoff flagged a mock where "On track" showed at 71% spend on day 14 of 24. Three rules were considered:

1. Expected-progress vs. actual-progress ratio with explicit tolerances.
2. Burn-rate projection (left_per_day vs. target_per_day).
3. Status quo in `services.budget.month_summary`.

## Decision

**Rule 1 (expected vs. actual, with tolerances).** Pure function:

```
pace_tag(spent_minor, budget_minor, elapsed_days, total_days, has_overdue) → Literal["on_track", "tight", "overdue"]
```

Algorithm:

1. If `has_overdue` → `"overdue"`. Overdue always wins.
2. If `budget_minor <= 0` or `total_days <= 0` → `"on_track"` (nothing to pace against).
3. Let `actual = spent_minor / budget_minor`, `expected = elapsed_days / total_days`.
4. If `actual <= expected + 0.10` → `"on_track"`.
5. Else if `actual <= expected + 0.25` → `"tight"`.
6. Else → `"overdue"` (no overdue items but spend is far ahead of pace).

The 71% / day-14-of-24 example (expected = 58.3%, actual = 71%, delta = +12.6pp) resolves to `"tight"` under this rule. The handoff's "On track" rendering is treated as illustrative only; the ADR corrects the formula.

## Rationale

- Pure deterministic function → trivial to unit test and reproduce.
- Thresholds (`+10pp`, `+25pp`) are design tokens exposed via module constants (`PACE_ON_TRACK_HEADROOM = 0.10`, `PACE_TIGHT_HEADROOM = 0.25`) so a future ADR can tune without changing the macro.
- Overdue override preserves handoff rule that overdue items never render muted.
- Burn-rate projection (option 2) was rejected because it over-reacts to spiky weekends and is harder to explain.

## Implementation checkpoints

- `services/budget.py` exports `pace_tag(...)` and `PACE_ON_TRACK_HEADROOM`, `PACE_TIGHT_HEADROOM` constants.
- `tests/services/test_budget_pace_tag.py` covers:
  - `test_on_track_when_actual_matches_expected`
  - `test_tight_when_actual_eleven_pp_over_expected`
  - `test_overdue_when_actual_thirty_pp_over_expected_no_overdue_items`
  - `test_overdue_wins_over_ratio_when_overdue_items_present`
  - `test_handoff_scenario_71_percent_day_14_of_24_resolves_tight`
- `pace_tag` Jinja macro (T-R14) docstring links back to this ADR.

## Consequences

- Pace classification becomes testable and auditable.
- Today hero may render "Tight" in cases where v1 rendered "On track" — intentional, mock illustration superseded.
- Thresholds live in Python (not CSS tokens) because they are logic, not visual.
