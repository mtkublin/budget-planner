# T-R72 — UI language decision

- **Phase**: 0 — Decisions
- **Sequential**: yes; blocks every Phase 3 screen (strings live in templates).
- **Depends on**: none.
- **References**: handoff §07 "Polish labels: mockups are in English with Polish category names; confirm UI language."

## Context

Mockups show English chrome (nav, buttons, headers) with Polish category names (user data). The current v1 app follows the same pattern. The decision is whether to:

1. **Commit to English chrome + user category names in whatever language the user types** — simplest, keeps v1 behaviour, no i18n layer, matches the mockups verbatim.
2. **Introduce an i18n layer** (`babel`, `fluent`, or a lightweight gettext wrapper) — enables multi-language chrome at the cost of a new dependency, string-extraction tooling, and build-time or runtime catalogue loading.

The user is single-operator in v1/v2; the operator is Polish-native and English-fluent per prior session notes.

## Deliverables

- New ADR capturing the decision + reasoning.
- If option 1: ADR amends ADR-0051 to pin "UI language = English; user data = any".
- If option 2: ADR documents the i18n stack choice, the string-extraction workflow, and the catalogue format; `docs/requirements.md` §3 gains a new sub-section.

## Acceptance criteria

- ADR Accepted; chosen option explicit.
- All Phase 3 template rebuilds have a clear rule for literal strings vs. interpolation points.
- If i18n chosen: a Phase 1 task is added (or T-R06 extended) to install the i18n stack.

## Risks & gotchas

- i18n introduced late in a template rebuild is painful — strings extracted retroactively miss edge cases. Decide before Phase 3 or commit to deferring i18n to a future version.
- Mockups are illustrative; design intent is "intentional, opinionated" chrome — option 1 is likely the right call given the single-operator scope.

## Handoff notes

- Default recommendation: option 1 (English chrome, user category names in any language). Record the alternative-rejected reasoning in the ADR so a future multi-user milestone can reopen the question.
