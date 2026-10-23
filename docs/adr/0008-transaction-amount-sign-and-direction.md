# ADR-0008: Transaction Amount Sign & Direction

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

- `transactions.amount` stored as **positive integer minor units** for direction ∈ `{income, expense, transit}`.
- Direction derived from `categories.direction` enum (`income | expense | transit | adjustment`).
- **Exception**: direction `adjustment` allows a **signed** amount (positive for inflow, negative for outflow). This encodes the sign of a reconciliation delta without needing two categories.

## Validation rules

- `amount != 0`.
- `direction ∈ {income, expense, transit}` → `amount > 0`.
- `direction == adjustment` → sign is free.

## Balance derivation sign rules

- `income` → `+amount` on `account_id`.
- `expense` → `-amount` on `account_id`.
- `transit` → `-amount` on `account_id`, `+amount` on `dest_account_id`.
- `adjustment` → `+amount` on `account_id` (amount already signed).

## Consequences

- Direction has a single source of truth (the category) for the normal path.
- Reconciliation uses one seeded "Reconciliation" category instead of two (Reconciliation+ / Reconciliation-).
- Balance derivation has a tiny per-direction switch; still a pure function.
- Transits are naturally excluded from income/expense aggregates by filtering direction.

## Alternatives Considered

- **Signed amount always**: flexible; opens door to "positive expense" / "negative income" bugs.
- **Two reconciliation categories**: cleaner model purity; worse UX (user must pick direction manually).
- **Separate `inflows` / `outflows` tables**: DRY violation and join-heavy unified log view.
