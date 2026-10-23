# ADR-0010: Account Model — Free-Text Type

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

Account schema:
- `name` — required, unique per user.
- `type` — optional free-text label (e.g. `"bank"`, `"cash"`, `"brokerage"`). No logic branches on type; used only for UI grouping and filtering.
- `currency` — ISO 4217, immutable after creation.
- `opening_balance` — integer minor units.

## Consequences

- No type-specific business logic to maintain.
- Users can add new types without schema changes.
- UI can group accounts by type for better navigation.

## Alternatives Considered

- **Enum type (cash/checking/savings/credit/investment)**: rigid; blocks user flexibility; migration pain to add new types.
- **No `type` field**: simpler but weakens UI grouping.
