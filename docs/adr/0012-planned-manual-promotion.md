# ADR-0012: Planned → Actual Promotion is Manual

- **Status**: Accepted
- **Date**: 2026-10-23

## Decision

A planned transaction becomes an actual transaction only via **manual user action**:

1. User sees the planned entry in the planned log (optionally filtered to "past date, not promoted").
2. User clicks "mark executed" → modal opens with amount, date, description pre-filled from the planned entry.
3. User can edit before confirming (e.g. planned 500, actual 487).
4. On confirm:
   - Insert row into `transactions` with the (possibly edited) values and `promoted_from_planned_id = planned.id`.
   - Update `planned_transactions.promoted_to_txn_id = txn.id`.
   - Write audit entries for both.

Soft-delete of a promoted planned row is still allowed; the actual txn is unaffected.

## Consequences

- Captures real-world drift (planned vs actual) honestly.
- No background scheduler needed in v1.
- Full audit via `promoted_from_planned_id` / `promoted_to_txn_id` links.

## Alternatives Considered

- **Auto-promote at midnight job**: silent errors, scheduler needed, cannot capture planned-vs-actual drift.
- **Hybrid (auto for recurring, manual for one-off)**: inconsistent UX.
