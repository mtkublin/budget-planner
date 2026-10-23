# ADR-0006: Multi-Currency Model

- **Status**: Accepted
- **Date**: 2026-10-23

## Context

The user operates accounts in different currencies and wants a unified fortune / budget / forecast view.

## Decision

- Each `account` has an immutable `currency` (ISO 4217) set at creation.
- Each `transaction` inherits the currency of its `account_id` (no `currency` column on `transactions`).
- A `base_currency` is configured in app config (default `PLN`). All aggregates (fortune, budget, forecast, analytics) are expressed in base currency.
- FX rates fetched from the ECB via `frankfurter.app` on demand, cached in a local `fx_rates(date, from_ccy, to_ccy, rate)` table.
- Conversion uses the **historical rate**: a transaction dated `2026-01-15` converts at the `2026-01-15` rate, not today's.
- Fallback: if the API is unreachable and no rate for the requested date is cached, use the most recent known rate for that pair with a log warning.
- Amounts stored as **positive integer minor units** of the account's currency (e.g. PLN grosz, EUR cents). Signed display derived from `category.direction`.

## Cross-currency transits

- Blocked at the service/validation layer in v1. A transit must reference `account_id` and `dest_account_id` with the same currency.
- Rationale: real-world cross-currency transits involve bank-specific FX spreads that cannot be modelled accurately without extra fields and UX. Deferred to a future ADR.

## Consequences

- Clean separation: accounts own currency, transactions do not.
- Historical reports stay stable; today's FX movements do not retroactively rewrite past aggregates.
- Base currency can be changed with no data migration (recomputed on read).

## Alternatives Considered

- **Single currency**: simpler, rejected because the user maintains multi-currency accounts.
- **`currency` on transaction**: necessary only if accounts hold mixed currencies (rare); over-models the common case.
- **Live rate for all conversions**: wrong signal; historical charts would wiggle on today's FX moves.
- **Manual rate entry**: operationally painful.
