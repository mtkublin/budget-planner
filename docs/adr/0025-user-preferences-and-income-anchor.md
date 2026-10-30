# ADR-0025 — User Preferences Table and Income Anchor Category

**Status**: accepted (2026-10-25)

**Context**

The budget planner has no per-user settings store today. App-wide
configuration lives in `src/budget_planner/config.py` via
`pydantic-settings` and is driven by environment variables (ADR-0004 for
the package manager / env story is adjacent, but the direct precedent is
`T-004`). This is correct for *deployment* knobs — database URL, bind
host, FX API URL — but wrong for *user* preferences that need to flip
without editing a `.env` file.

The trigger for this ADR is the **"Left daily spend"** metric
([F4.6](../requirements.md#24-monthly-budget)): the user must pick which
INCOME-direction category represents their anchor paycheck so the metric
knows which planned-income date to divide the remaining budget over
(F4.7). That is a per-user preference by definition. We also expect more
preferences to accrete over v1's remaining phases (default landing view,
locale, chart defaults, soon-to-be-remembered filter scopes).

Three shapes were on the table:

1. A **boolean column on `categories`** (`is_income_anchor`) — rejected.
   This is the exact anti-pattern [ADR-0010](0010-account-model-free-text-type.md)
   warned against: a single-purpose, behaviour-affecting flag glued onto
   a descriptive domain table. It also makes a UI concern leak into the
   domain layer and does not generalise to the next preference we add.
2. An **env var in `config.py`** (`income_anchor_category_id`) — rejected.
   Terrible UX: the user would edit `.env` and restart the server to
   change their anchor. For a web app this is strictly worse than the
   existing "manage" page affordance.
3. A **generic `user_preferences(user_id, key, value)` table** — accepted.
   One migration pays for every future preference. Keyed access, soft
   lifecycle (settings are overwritten, not versioned), no audit entry
   (settings are not domain mutations in the ADR-0022 sense).

**Decision**

1. **New table `user_preferences`.** Schema:

   ```sql
   CREATE TABLE user_preferences (
     id          INTEGER PRIMARY KEY,
     user_id     INTEGER NOT NULL REFERENCES users(id),
     key         TEXT    NOT NULL,
     value       TEXT    NOT NULL,
     created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
     updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
     UNIQUE(user_id, key)
   );
   ```

   No `deleted_at` column: a preference is either present or absent;
   there is no business value in a tombstone row. Clearing a preference
   deletes the row. No `audit_log` entry: preferences are UI state, not
   domain mutations — [ADR-0022](0022-repository-layer-soft-delete-audit-discipline.md)
   scope is domain data and is unaffected.

2. **First key: `income_anchor_category_id`.** The stored `value` is the
   stringified `categories.id` of the user's chosen INCOME-direction
   anchor category. Reads **validate liveness and direction** at service
   boundary: if the referenced category is soft-deleted or has had its
   direction changed (currently immutable per ADR-0008, but defence in
   depth), the preference is treated as *unset* at read time and the
   downstream metric falls back to its end-of-month denominator. The
   stale row stays — users may rebind the same key later; the service
   layer, not the repository, enforces semantic validity.

3. **Scope keyed on `users.id = 1` in v1.** [ADR-0005](0005-single-user-no-auth-user-id-scaffold.md)
   established the single-user scaffolding; this table extends it in the
   same shape (`user_id` FK, singleton row in v1). Future multi-user reuses
   the table verbatim.

4. **No new domain direction, enum, or arithmetic.** The anchor is a
   lookup key only; the three services it touches
   (`services.budget.month_summary`, `services.planned.list_planned`,
   and a new `services.preferences`) share this ADR but their internal
   contracts are unchanged by it. `derive_balance`, `signed_legs`,
   `resolve_budget`, `expand(...)` all stay as-is.

5. **Repository shape.** `src/budget_planner/repositories/preferences.py`
   exposes three pure functions:
   - `get(conn, user_id, key) -> UserPreference | None`
   - `upsert(conn, user_id, key, value) -> UserPreference`
   - `delete(conn, user_id, key) -> None`

   These do **not** use the `_shared.mutate(...)` helper — that helper
   writes an `audit_log` row inside the same transaction and the point of
   this ADR is that preferences skip audit. The functions still run
   inside an explicit `BEGIN`/`COMMIT` to keep the "repository owns the
   transaction" invariant from [ADR-0022](0022-repository-layer-soft-delete-audit-discipline.md).

**Consequences**

Pros:

- One migration unlocks every future per-user preference without
  re-opening a design discussion. Default view, locale, remembered
  filter scopes, chart defaults — all fit the same shape.
- Keeps `config.py` tightly scoped to deployment knobs (ADR-0004 story
  stays coherent).
- Does not perturb any ADR between 0003 and 0024. In particular,
  ADR-0010, ADR-0019, and ADR-0022 are untouched.

Cons / costs:

- One extra table + one new migration + one new service module. Low cost
  for v1 and amortises across every future preference.
- A rare class of bug: a key stored as a stringified `categories.id`
  that points to a deleted row. Covered by the service-layer liveness +
  direction check (point 2 above). An integration test asserts the
  fallback path.

Explicit non-goals:

- **No typed value column.** Preferences are stringly-typed in storage;
  the service layer casts (`int`, `bool`, `date`) at the boundary. A
  typed `value_json` was considered and rejected as premature; strings
  are enough for every v1 preference.
- **No audit log entries for preferences.** See point 1 and the ADR-0022
  scope note.
- **No multi-user support in v1.** The `user_id` column is scaffolding
  for a future multi-user milestone (not v2 or v3); v1 writes `user_id = 1` everywhere.

**Alternatives Considered**

- *Boolean column on `categories`.* See context. Single-purpose,
  behaviour-leaking, does not generalise.
- *Env var in `config.py`.* See context. Worst UX of the three.
- *Typed `value_json` BLOB.* Premature; v1 keys are all scalar strings
  or stringified ids. Revisit if a preference ever needs structured
  storage (none planned for v1).

**References**

- Related: ADR-0005 (single-user scaffold), ADR-0010 (free-text type —
  anti-pattern this ADR avoids), ADR-0019 (soft-delete + audit scope),
  ADR-0022 (repository discipline — this ADR carves out a *settings*
  exception), ADR-0024 (orthogonal classification pattern — same
  "don't glue behaviour flags onto descriptive tables" principle).
- Requirements: [F4.6](../requirements.md#24-monthly-budget),
  [F4.7](../requirements.md#24-monthly-budget).
- Task breakdown: [Phase 9 — Left Daily Spend](../plans/v1/phase-9/README.md).
