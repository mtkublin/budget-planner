# ADR-0007: Timezone Handling

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

- `created_at`, `updated_at`, `deleted_at`, and all audit timestamps are **UTC** `TIMESTAMP` columns.
- Transaction `operation_date` is a **`DATE`** column (no time component). A spend on 2026-10-20 is tz-less in meaning.
- The display timezone is set in app config (default `Europe/Warsaw`) and used only when rendering UTC timestamps for users.

## Consequences

- No DST drift.
- No tz hell on travel or deploy to a different region.
- Operation dates remain the user's intent (the date they consider the money spent), not a UTC-normalised shift.

## Alternatives Considered

- **Naive local time** everywhere: breaks on travel or deploy.
- **Per-transaction tz**: overkill; `operation_date` as `DATE` already sidesteps the issue.
