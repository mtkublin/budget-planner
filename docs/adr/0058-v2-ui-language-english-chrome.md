# ADR-0058 — v2: UI language — English chrome, user data as-typed

- **Status**: Accepted
- **Date**: 2026-10-28
- **Amends**: ADR-0051 (v2 information architecture).
- **Related**: handoff `docs/application_redesign_handoff/docs/07-open-items.md`.

## Context

Mockups show English chrome (nav, buttons, section headers, empty-state copy) alongside Polish category names (user data). The operator is single-user, Polish-native, English-fluent.

Options considered:

1. English chrome + user data in whatever language typed. No i18n layer.
2. Introduce an i18n stack (`babel`, `fluent`, or `gettext` wrapper) for future multi-language.

## Decision

**Option 1.** v2 commits to:

- English chrome: nav labels, headers (e.g. "Everything that happened"), buttons ("+ Add", "Promote"), form labels, empty-state copy, validation messages.
- User data as-typed: category names, account names, transaction descriptions, notes.
- Template strings are literal English in Jinja templates. No `_()`/`gettext` wrapper, no catalogue extraction.

## Rationale

- Single operator; i18n is premature abstraction (YAGNI).
- Mockups are already in English; translating chrome retroactively against the handoff is wasted motion.
- Future multi-user milestone can re-open the question; this ADR is explicitly reversible by introducing an i18n stack behind the macros without template rewrites.

## Consequences

- No new dependency (`babel`, `jinja2.ext.i18n`).
- Phase 3 screen rebuilds (T-R25..T-R39, T-R65..T-R70) use English literals matching the handoff.
- Category pills, account chips, and transaction descriptions render user-input verbatim and never translate.
- Error messages surfaced to the user remain English regardless of locale headers.

## Reversibility note

If multi-language chrome becomes a requirement later, the migration path is:

1. Wrap literal strings with `{{ _("…") }}`.
2. Add Babel to deps, configure `pybabel` extraction against `src/budget_planner/web/templates/`.
3. Ship default `en` catalogue; translators maintain additional catalogues.

The macro layer (ADR-0053) is the natural chokepoint — strings inside macros become the first extraction target.
