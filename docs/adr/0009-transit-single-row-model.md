# ADR-0009: Transit as a Single Row

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

Transits between the user's own accounts are modelled as a **single transaction row** with both `account_id` (source) and `dest_account_id` (destination) populated. Normal transactions have `dest_account_id = NULL`.

A seeded `Transit` category exists with `direction = 'transit'`. Transits must use that category (or any other category with `direction = 'transit'` if the user adds more).

Transits are excluded from income/expense statistics (filter by `direction != 'transit'`).

## Consequences

- Unified transaction log view is trivial (one table).
- No orphan risk from paired entries getting out of sync.
- Balance derivation reads one row and applies both legs.
- Cross-currency transits blocked at the service layer (ADR-0006).

## Alternatives Considered

- **Paired rows linked by `transit_id`**: double-entry bookkeeping purity; needs transactional insert, cascade delete, join for display. Overkill.
- **Separate `transits` table**: DRY violation; analytics view needs UNION.
