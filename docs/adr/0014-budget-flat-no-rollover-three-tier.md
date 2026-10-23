# ADR-0014: Budget Model — Flat Categories, No Rollover, Three-Tier Resolution

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

- **Flat categories**: no hierarchy. (Hierarchy can be added later via `parent_category_id` without breaking changes.)
- **No rollover**: each month's unspent budget is forfeited (money stays in the account; the *budget* view resets).
- **Per-category only**: total monthly budget is derived (`SUM(category_budget)`), not independently configurable.

### Three-tier resolution

```
get_budget(category, year, month) =
    one_off(category, year, month)         ??    # applied once
    recurring(category, month)             ??    # applied every year for this month
    default(category)                            # applied all months
```

### Tables

- `budget_defaults(category_id UNIQUE, amount)`.
- `budget_recurring_overrides(category_id, month 1-12, amount, UNIQUE(category_id, month))`.
- `budget_one_off_overrides(category_id, year, month, amount, UNIQUE(category_id, year, month))`.

## Consequences

- Resolution is a pure null-coalesce — trivially testable.
- Three small tables, each with a single clear purpose.
- Users can model: "my gym fee goes up every January" (recurring) and "I had an extra big heating bill in February 2026 only" (one-off).

## Alternatives Considered

- **Hierarchical categories**: UX cost (tree nav, rollup math, parent-vs-leaf budgets); no clear v1 need.
- **Rollover**: muddles "did I meet budget this month?" view.
- **Total cap + per-cat**: conflicting constraints; dropped.
- **Single `budget_overrides` table with nullable year**: fewer tables, muddier semantics.
