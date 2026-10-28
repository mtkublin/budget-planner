# ADR-0046: Recurring Overrides — Soft-Consume on Promotion (Not Delete)

- **Status**: Accepted
- **Date**: 2026-10-28
- **Amends**: [ADR-0038](0038-recurring-standalone-lifecycle.md) §Promotion-flow step 6e; cross-references [ADR-0045](0045-recurring-formula-amount.md) (formula amounts depend on this).

## Context

ADR-0038 established that a `recurring_rule_overrides` row applies to exactly one promotion whose `due_date = occurrence_date`, then **the row is deleted** as part of the promotion transaction. The deletion keeps the overrides table sparse and prevents stale overrides from re-applying to a later occurrence that happens to cycle back to the same date.

ADR-0045 introduced formula-derived recurring amounts: rule A's amount is a percentage of the summed monthly amounts of other recurring rules in selected categories. The formula compute path reuses `services.recurring.expand(source_rule, overrides, month_start, month_end)` to materialise each source rule's monthly occurrences, including any overrides on those occurrences.

Composing the two produces a defect: once source rule B's May occurrence is promoted (its override is consumed and the row deleted), formula compute for A can no longer see the override. If A's May gets promoted **after** B's May, A locks in `B.default_amount × coefficient` instead of the override-adjusted amount B actually paid. If A's May gets promoted **before** B's May, A is correct — but promotion order is a user action, not a system invariant, and the discrepancy is silent.

The user expectation is: once B's May override is written, A's May **always** reflects that override, regardless of promotion order and regardless of whether A is viewed, promoted, or forecast after B's May promotion.

## Decision

**Overrides are soft-consumed on promotion, not deleted.** Add a nullable `promoted_to_txn_id` column to `recurring_rule_overrides` pointing at the `transactions` row that consumed it. The row remains in the table; the override continues to be returned by `services.recurring.expand` and keeps affecting formula compute, forecast backfills, and any historical read that materialises past occurrences.

### Schema change (migration `0009_recurring_override_promoted_fk.sql`)

```sql
ALTER TABLE recurring_rule_overrides
    ADD COLUMN promoted_to_txn_id INTEGER
    REFERENCES transactions (id) DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX ix_recurring_overrides_promoted
    ON recurring_rule_overrides (rule_id, promoted_to_txn_id);
```

- Column is nullable; `NULL` = unconsumed, matches ADR-0038's one-override-per-promotion contract on the write side.
- No `NOT NULL` enforcement at the row level; the service layer owns the "override reaches `promoted_to_txn_id = txn.id` at exactly one point in its lifecycle" invariant (same shape as `planned_transactions.promoted_to_txn_id`).
- Additive migration; no table rebuild; FK pragma toggle unnecessary.

### Repository contract

- `list_overrides(conn, rule_id, *, include_consumed: bool = False)` — default **excludes** consumed overrides so pre-ADR-0046 callers (promote lookup, override UI, skip-and-advance) see the same world they always have.
- `list_overrides_all(conn, rule_id)` — includes consumed overrides. Used by `services.recurring.expand` and formula compute paths that need historical visibility.
- `mark_override_promoted(conn, override_id, txn_id)` — new audit-free helper (service pairs the audit entry with the promotion rule mutation, matching ADR-0038's single-logical-advance pattern).
- `delete_override(conn, rule_id, occurrence_date)` — retained for admin flows and skip-and-advance's ephemeral skip override; **no longer called from `promote_recurring`**.

### Service change (`services.recurring.promote_recurring` step 6e)

```
    e. mark_override_promoted(conn, match.id, txn_id=new_txn.id)
```

Replaces `delete_override`. The matching override row stays, now stamped with the transaction that consumed it. Audit on the rule mutation remains a single `update` entry.

### Formula compute visibility

`services.recurring_formula.compute_formula_amount` loads overrides via `list_overrides_all` (not the default-filtered `list_overrides`). `apply_overrides` is unchanged — it already keys by `occurrence_date`, so a consumed override continues to apply to the exact month it was written for and never leaks to any other date.

### Forward-looking callers (unchanged behaviour)

- `services.upcoming.list_upcoming`, `services.income.next_anchor_date`, `services.budget.committed_in_window`: all operate on windows `>= today`. Consumed overrides are historical (`occurrence_date <= today` by construction, since consumption happens on promotion). They do not match forward windows. These callers continue to use the default-filtered `list_overrides` — unconsumed overrides only.
- `web/routers/recurring._override_on_next_due`: filters by `occurrence_date == rule.next_due`, which is advanced past the consumed override's date. The default `include_consumed=False` makes the filter redundant but defensively correct.

### Historical correctness guarantee

For any past month `M` and any formula rule A:

```
A_amount(M) = coefficient × Σ expand(B, list_overrides_all(B), first(M), last(M)).amount
             over all source rules B
```

This is now stable regardless of when A was promoted vs. when B was promoted. The consumed override row is the single source of truth for "what did B's amount look like in M", survives all promotions, and gets GC'd only when B itself is soft-deleted (follow-up — see Consequences).

## Consequences

- **Table grows unbounded.** One override row per promoted recurring occurrence. At v1 single-user scale this is bounded by `#active_rules × months_lived` — tens to low thousands over a decade. Acceptable; a later cleanup can prune on `recurring_rules.deleted_at IS NOT NULL` cascade.
- **Audit chatter unchanged.** Promotion still emits one logical `update` audit entry on the rule; the override mutation is audit-free (same pattern as `set_next_due` + `set_inactive`).
- **Admin / debugging:** `promoted_to_txn_id` makes the "which txn consumed this override" question a one-column lookup, replacing today's "find a txn with matching `promoted_from_recurring_rule_id + promoted_from_recurring_date`" join. Nice side-effect.
- **FK integrity:** `promoted_to_txn_id` is `DEFERRABLE INITIALLY DEFERRED` to match the project's existing FK style and to permit transaction-insert + override-mark ordering within the single promotion `BEGIN/COMMIT` without constraint ordering fragility.
- **Follow-up — hard delete on rule removal:** when `recurring_rules.deleted_at` is set, orphaned consumed overrides can be hard-deleted or cascade-null'd. Out of scope for ADR-0046; tracked as a later cleanup task.

## Alternatives Considered

- **Freeze A's amount at B's promotion time** (reactive write — on every B promotion, scan every A referencing B's category and rewrite A's `default_amount` snapshot). Rejected: breaks the "formula is live" invariant from ADR-0045, requires reverse-dependency index, and still doesn't help if A hasn't been promoted yet.
- **Store a copy of B's amount on A's transaction at A's promotion time** (lazy materialisation on A's promote). Rejected: works only for the single moment A is promoted; forecast / budget / ledger-row renders between B's May promotion and A's May promotion still see wrong value.
- **Read historical values from `transactions.promoted_from_recurring_*` columns** (bypass overrides entirely post-promotion). Rejected: couples the formula service to transaction storage, breaks the current "expand(rule, overrides, ...)" pure-function surface, and still requires special-case handling for A's May *before* B's May promotes.
