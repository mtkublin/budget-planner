# ADR-0043: Recurring Rules — Formula-Derived Amount (Percentage of Other Rules)

- **Status**: Accepted
- **Date**: 2026-10-27
- **Amends**: [ADR-0013](0013-recurring-virtual-occurrences-and-overrides.md), [ADR-0038](0038-recurring-standalone-lifecycle.md). Does not supersede either — the override + promotion lifecycle is unchanged.

## Context

Some real-world recurring payments are not fixed amounts: a monthly income tax is "12% of selected income categories for that month", not a flat `1 234.56 PLN`. The user manually recomputes the amount every promotion today. ADR-0038 made promotion a one-click action — a fixed `default_amount` snapshot is the only knob the promote modal pre-fills.

We want the `default_amount` of a recurring rule to be, optionally, a formula computed from the sums of OTHER recurring rules in the same calendar month, filtered by category.

## Decision

Add an optional `amount_formula` on `recurring_rules` carrying a JSON spec. When present it overrides `default_amount` at **expand time** (budget `committed_in_window`, forecast projection, promote modal pre-fill, Ledger row render). When absent (the default) the rule behaves exactly as before — this is a strictly additive change.

### Formula shape (JSON stored as TEXT)

```json
{
  "coefficient_bps": 1200,
  "source_category_ids": [5, 7]
}
```

- `coefficient_bps` — INTEGER basis points. `1200` = 12.00%. Range `(0, 1_000_000]` (0.0001% to 10 000%). INTEGER so we never persist a float.
- `source_category_ids` — non-empty JSON array of category ids. Direction-agnostic: user picks whichever categories compose the base.

### Computation

```
compute_formula_amount(conn, formula, year, month, exclude_rule_id) -> int:
  rules = all active, non-deleted recurring rules where
          category_id ∈ formula.source_category_ids
          AND amount_formula IS NULL          # cycle prevention — only
                                              # fixed rules are summable
          AND id != exclude_rule_id
  total_minor = 0
  for rule in rules:
      occs = expand(rule, overrides=list_overrides(rule.id),
                    range_start=first_day(year, month),
                    range_end=last_day(year, month))
      total_minor += sum(occ.amount for occ in occs)   # magnitudes only
  decimal = Decimal(total_minor) * Decimal(formula.coefficient_bps) / Decimal(10_000)
  return int(decimal.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
```

- **Magnitude-only sum.** Direction is a presentation concern (ADR-0008); the formula sums positive integer `amount` values regardless of whether the source category is `income` or `expense`. The computed amount then takes on **this rule's** category direction at promotion time.
- **Cycle prevention is structural, not algorithmic.** `amount_formula IS NULL` on sources means the dependency graph is a 2-level tree: formula-rules → fixed-rules. No topological sort required; no runtime recursion limit. Attempting to pick a formula-rule as a source is rejected at the save boundary (422) and defensively filtered at compute time (silently skipped — logged WARNING).
- **Rounding is `ROUND_HALF_UP`** on minor-unit integer boundaries. Deterministic, independent of locale, matches end-user intuition for "percent of".
- **Month is the occurrence's calendar month**, not the rule's `next_due`. For budget and forecast call sites that expand across a range, each occurrence is computed from its own `(year, month)`.
- **Overrides on source rules participate.** If an income source rule has an `amount_override` for the month in question, the override wins — this is already how `expand` works. "This month's tax is 12% of this month's actual income" is the intended semantic.

### Schema change (migration `0008_recurring_amount_formula.sql`)

```sql
ALTER TABLE recurring_rules ADD COLUMN amount_formula TEXT;
-- SQLite rebuild to relax the CHECK: formula rules may legitimately have
-- `default_amount = 0` as the last-snapshotted value when all sources are
-- empty. Fixed rules still require `default_amount <> 0`.
CREATE TABLE recurring_rules_new (
    ...
    default_amount INTEGER NOT NULL,
    amount_formula TEXT,
    CHECK (amount_formula IS NOT NULL OR default_amount <> 0),
    ...
);
```

- The column is `TEXT` (JSON blob). SQLite's `json1` extension is enabled; service-layer parse/serialize via `json.loads` / `json.dumps` — no schema-level JSON validation. Validation lives in `services.recurring_formula.parse_formula`.
- `default_amount` remains a **snapshot** of the last-computed value for formula rules. Written on `create_rule` / `update_rule` so Ledger / Overview / unsupported-conn surfaces have something sensible to render without hitting the DB. Live callers (`expand`, `promote_recurring`) always recompute.

### Mutation path

- `POST /recurring` and `POST /recurring/{id}` accept new form fields:
  - `amount_source` ∈ `{fixed, formula}` (default `fixed`).
  - `coefficient_percent` — DECIMAL string, converted to bps (× 100, `ROUND_HALF_UP`).
  - `source_category_ids` — repeated form field (checkbox group).
- When `amount_source == formula`:
  - `default_amount` form field is ignored.
  - Service validates `coefficient_percent > 0`, `source_category_ids` non-empty, every source category exists + has `direction ∈ {income, expense}`.
  - Service computes the current `(today.year, today.month)` snapshot and persists it as `default_amount` so the DB has a non-null value.
- When `amount_source == fixed`: existing behaviour. `amount_formula` is cleared.

### Promotion flow (amended ADR-0038)

Inside `promote_recurring`, before the override-merge step:

```
if rule.amount_formula is not None:
    rule_default = compute_formula_amount(
        conn, rule.amount_formula,
        year=rule.next_due.year, month=rule.next_due.month,
        exclude_rule_id=rule.id,
    )
else:
    rule_default = rule.default_amount
```

The rest of the flow (override merge → explicit edits → validate → insert → advance) is unchanged.

### Rendering (Ledger / Overview / Promote modal)

- Ledger recurring row: `effective_amount_minor` becomes `compute_formula_amount(...)` when the rule has a formula, otherwise `rule.default_amount` (existing). A small `fx` chip renders next to the amount with hover-title "12% of Salary + Freelance (2026-11)".
- Promote modal pre-fill: uses the live-computed amount for the rule's `next_due` month.
- Overview Upcoming + Budget `committed_in_window` + Forecast: all route through the new `services.recurring.rt_expand(conn, ...)` wrapper that substitutes computed amounts before `apply_overrides`.

## Consequences

- Formula rules are **not** themselves summable — only fixed rules feed the base. Users who need "tax on (salary + bonus_formula)" must express bonus_formula differently or stage the computation across two rules; this preserves cycle-freedom and keeps the compute path O(n) over source rules.
- `default_amount` on formula rules is a staleness-tolerant snapshot. If the user changes a source rule but never opens the Ledger / Overview page, the snapshot drifts — the next render refreshes it opportunistically (fire-and-forget UPDATE from the hydrator); live promotion is always correct.
- Forecast still projects into the future using today's source-rule state (expected: forecasted salary doesn't change in-horizon). This is the same assumption ADR-0015 made for fixed recurring amounts.
- CHECK relaxation is the only migration-time risk. Existing rows have `default_amount <> 0` so the new CHECK passes trivially; the SQLite rebuild follows the ADR-0038 pattern (migrations/0007).

## Alternatives Considered

- **Store the formula at the override level** (one override = one month's computed amount). Rejected: forces the user to materialise overrides every month, duplicates ADR-0038 override semantics, and the whole feature's point is "set it once".
- **Arbitrary expression DSL** (e.g. `sum(cat:salary) * 0.12 + 50`). Rejected: evaluator surface area, injection risk against the categories dropdown, and the Pareto 90% is covered by the simple `coefficient × sum(categories)` shape.
- **Snapshot-only (no live recompute).** Rejected: the whole feature value is "my tax tracks my actual income this month"; a pure snapshot forces the user to re-save the rule every month, which is strictly worse than today's "edit `default_amount` once".
