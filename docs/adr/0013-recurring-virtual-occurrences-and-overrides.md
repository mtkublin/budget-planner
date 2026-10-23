# ADR-0013: Recurring Rules — Virtual Occurrences with Sparse Overrides

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

Recurring rules are the source of truth. Occurrences are **not materialised** into the planned-transactions table; they are generated virtually when queried.

### `recurring_rules`

Fields relevant for occurrence generation:
- `cadence`: `monthly` | `quarterly` | `yearly`.
- `start_date`, `end_date` (nullable).
- `day_of_month`, `month_of_year` (nullable; used by cadence).
- `default_amount`, `default_description`, `category_id`, `account_id`, `dest_account_id`.
- `active`.

### `recurring_rule_overrides`

Sparse exception table keyed by `(rule_id, occurrence_date)`:
- `state`: `skipped` | `overridden`.
- `amount_override`, `description_override`, `date_override` (nullable).

### Generation algorithm (pure function)

```
occurrences(rule, range_start, range_end):
    1. Compute the canonical schedule from cadence + start/end.
    2. Clip to [range_start, range_end].
    3. Yield each canonical occurrence_date carrying rule defaults.

apply_overrides(occurrences, overrides):
    4. For each override:
         - state=skipped       → drop the occurrence
         - state=overridden    → replace amount/description/date with the override fields
    5. Return the final list.
```

### Multi-occurrence skip

"Skip July 2026 AND September 2026" = two rows in `recurring_rule_overrides`, both with `state = 'skipped'`. The UI exposes a calendar of upcoming occurrences with per-row toggle; bulk-skip is a trivial multi-insert.

## Consequences

- Rule edits propagate instantly to all future (and historical, unpromoted) occurrences without backfill.
- No cron / scheduler needed.
- Overrides table stays small (sparse).
- Virtual occurrences are a view-only concept; promotion to actual works by inserting a new `planned_transactions` row (one-off) or going directly to `transactions` from the virtual occurrence via the promotion flow (ADR-0012).

## Alternatives Considered

- **Materialise N months ahead on rule create + rolling job**: arbitrary cutoff; scheduler; drift risk.
- **Materialise on first view (cache)**: optimisation; skip until proven needed.
- **Single `active`/`skipped` boolean per occurrence**: cannot express per-occurrence amount overrides.
