# T-R73 — Pace-tag rule confirmation

- **Phase**: 0 — Decisions
- **Sequential**: yes; blocks T-R14 (pace_tag macro) and T-R25 (Today).
- **Depends on**: none.
- **References**: handoff §07 "Today pace tag reads 'On track' as in the current app although spend is 71% of plan; confirm the pace rule."

## Context

The handoff flags a mocked state where the Today hero reads "On track" while 71 % of the planned budget has been spent, which looks tight. Three plausible rules:

1. **Expected-progress vs. actual-progress** on the anchor window: `on_track` iff `spent / budgeted <= elapsed_days / total_days + 0.1`, `tight` iff ≤ +0.25, `overdue` iff any overdue items exist.
2. **Days-remaining vs. remaining-amount** at the current burn rate: `on_track` iff `left_per_day >= target_per_day * 0.9`.
3. **Current v1 rule, unchanged**: whatever `services.budget.month_summary` returns today.

The handoff mock shows "On track" at 71 % spend on day 14 of 24 — rule 1 would mark it "tight" (expected 58 %, actual 71 %), rule 2 depends on the specific amounts.

## Deliverables

- ADR amendment to ADR-0041 (budget period anchor window) or ADR-0051 pinning the formula.
- Document the thresholds and the overdue-override behaviour.
- Reference the formula in the `pace_tag` macro's docstring (T-R14).

## Acceptance criteria

- ADR Accepted.
- Formula implementable in `services.budget.month_summary` as a pure function returning `Literal["on_track", "tight", "overdue"]`.
- The handoff's "On track at 71 % spend on day 14 of 24" scenario is either explicitly accepted (rule chosen matches) or acknowledged as illustrative-only in the ADR.

## Risks & gotchas

- Threshold values are opinionated; make them tokens so a future ADR can tune without changing the macro.
- Overdue must always win over spending ratio — handoff explicitly says overdue items never render muted.

## Handoff notes

- The chosen formula feeds `pace_tag` macro acceptance tests (T-R14) and the Today hero `pace_tag` render (T-R25).
