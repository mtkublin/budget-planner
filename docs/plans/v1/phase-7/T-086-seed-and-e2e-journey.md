# T-086 — Seed Demo Credit-Card Account + E2E Journey

> Phase 7 — Liability Accounts. Status: pending.

## Purpose

Make the new feature visible on a freshly seeded dev DB (`just seed`), and lock in the end-to-end user flow with a Playwright journey. This is the final task of the phase; it is the public-facing proof that T-081..T-085 compose cleanly.

## Inputs / prerequisites

- Upstream tasks: T-084 (UI complete). T-085 (soft-warning preview) landing is strongly preferred but not strictly required — the e2e asserts the account-card side only.
- Binding standards:
  - [`ADR-0024`](../../../adr/0024-liability-accounts-and-credit-limit.md).
  - Phase 4 e2e precedent: `tests/e2e/test_add_transaction_flow.py`, `tests/e2e/conftest.py` (per-test subprocess + migrated SQLite + Playwright chromium).
  - `justfile` recipe `seed` wraps `python -m budget_planner.db.seed`.
- Adjacent precedent:
  - `src/budget_planner/db/seed.py` — current seed insert for the two system categories; add a demo liability account next to the existing demo seed path (if any; otherwise add one).

## Deliverables

Modified files:

- `src/budget_planner/db/seed.py` — insert one liability demo account under the default user. Idempotent via `name` uniqueness per user.

New files:

- `tests/e2e/test_credit_card_journey.py`.

### Seed changes

Append to the existing seed flow:

```python
# Demo credit-card account for Phase 7 (ADR-0024). Idempotent on re-seed.
existing = accounts_repo.find_by_name(conn, "Visa (PLN)")
if existing is None:
    accounts_repo.create(
        conn,
        NewAccount(
            name="Visa (PLN)",
            currency="PLN",
            opening_balance=0,
            type="credit_card",
            is_liability=True,
            credit_limit_minor=1_000_000,  # 10,000.00 PLN
        ),
    )
```

- Use `accounts_repo.find_by_name` (the existing live-filter helper) to keep the seed idempotent.
- `type = "credit_card"` is the descriptive label (ADR-0010 free text); the behavioural flag is `is_liability = True`.
- Opening balance `0` means no pre-existing debt. Users can edit the account to reflect a real statement balance.

Guard the seed call with an existence check so `just seed` on an already-seeded DB stays a no-op.

### E2E journey

`tests/e2e/test_credit_card_journey.py`:

```python
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_credit_card_full_journey(page: Page, base_url: str) -> None:
    # 1. Open /accounts and verify the Visa (PLN) card is seeded with Limit 10,000.00.
    page.goto(f"{base_url}/accounts")
    visa = page.locator('[id^="account-"]').filter(has_text="Visa (PLN)")
    expect(visa).to_be_visible()
    expect(visa.locator(".credit-strip")).to_contain_text("10,000.00")
    expect(visa.locator(".credit-strip")).to_contain_text("0%")

    # 2. Dashboard shows Assets / Liabilities / Net worth with Liabilities = 0.00.
    page.goto(f"{base_url}/")
    expect(page.locator(".fortune-split")).to_contain_text("Liabilities")
    expect(page.locator(".fortune-split")).to_contain_text("0.00")

    # 3. Add a 500.00 expense on the Visa account via /transactions/new.
    page.goto(f"{base_url}/transactions/new")
    page.select_option('select[name="account_id"]', label="Visa (PLN)")
    page.select_option('select[name="category_id"]', label="Groceries")  # or any seeded expense category
    page.fill('input[name="amount"]', "500.00")
    page.fill('input[name="description"]', "e2e credit-card expense")
    page.click('button[type="submit"]')

    # 4. Visa card now shows Available 9,500.00 and 5% used.
    page.goto(f"{base_url}/accounts")
    visa = page.locator('[id^="account-"]').filter(has_text="Visa (PLN)")
    expect(visa.locator(".credit-strip")).to_contain_text("9,500.00")
    expect(visa.locator(".credit-strip")).to_contain_text("5%")

    # 5. Dashboard shows Liabilities = 500.00 and a reduced Net worth.
    page.goto(f"{base_url}/")
    expect(page.locator(".fortune-split")).to_contain_text("500.00")

    # 6. Over-limit scenario: add an 11,000.00 expense.
    page.goto(f"{base_url}/transactions/new")
    page.select_option('select[name="account_id"]', label="Visa (PLN)")
    page.select_option('select[name="category_id"]', label="Groceries")
    page.fill('input[name="amount"]', "11000.00")
    page.fill('input[name="description"]', "e2e overshoot")
    page.click('button[type="submit"]')  # submits successfully (soft enforcement)

    # 7. Over-limit badge is now visible on the Visa card.
    page.goto(f"{base_url}/accounts")
    visa = page.locator('[id^="account-"]').filter(has_text="Visa (PLN)")
    expect(visa.locator(".badge--warning")).to_contain_text("Over limit by")

    # 8. Transit payoff: move 11,500.00 from a bank account to the Visa (restores to zero).
    #    Precondition: the seeded demo includes at least one asset account; if not,
    #    create a bank account via /accounts first.
    page.goto(f"{base_url}/transactions/new")
    page.select_option('select[name="account_id"]', label="Bank (PLN)")
    page.select_option('select[name="dest_account_id"]', label="Visa (PLN)")
    page.select_option('select[name="category_id"]', label="Transit")
    page.fill('input[name="amount"]', "11500.00")
    page.fill('input[name="description"]', "e2e payoff")
    page.click('button[type="submit"]')

    # 9. Visa card returns to 0 balance, 0% used, no over-limit badge.
    page.goto(f"{base_url}/accounts")
    visa = page.locator('[id^="account-"]').filter(has_text="Visa (PLN)")
    expect(visa.locator(".credit-strip")).to_contain_text("0%")
    expect(visa.locator(".badge--warning")).to_have_count(0)
```

- Auto-skip when Playwright or chromium is absent (matches the T-042 pattern).
- Reuse the shared `page` + `base_url` fixtures from `tests/e2e/conftest.py`.

## Step-by-step

1. **Seed.** Edit `src/budget_planner/db/seed.py` and add the demo account block after the system categories. Keep the idempotency check.
2. **Verify locally.** `just db-reset && just migrate && just seed && just dev` → `/accounts` shows the Visa card with a 10,000.00 limit.
3. **E2E file.** Author the journey. Reuse the existing fixtures; do not spin up a new subprocess harness.
4. **Playwright chromium.** Confirm `uv run playwright install chromium` has been executed in the environment that runs the test (CI already handles this per T-042's recorded instructions).
5. **Soft-enforcement assertion.** Step 6 of the journey is the load-bearing check — the transaction submit does NOT return a 4xx. If it does, the task has drifted into hard enforcement; roll back the service change.

## Validation / acceptance

- `just db-reset && just migrate && just seed` is a clean sequence; re-running `just seed` is a no-op (no duplicate account error).
- `pytest tests/e2e/test_credit_card_journey.py -q` is green locally with chromium installed; auto-skips otherwise.
- `just ci` is green (Playwright suite included).
- `docs/CHANGELOG.md` appended with the Phase 7 landing paragraph on the day T-086 lands.

## Risks & gotchas

- **Seed category availability.** The journey selects categories like "Groceries" and "Transit". "Transit" is seeded as a system category (ADR-0012); "Groceries" is not. If no expense category exists on a fresh seed, create one via the UI step-by-step in the journey or extend the seed with one demo expense category (prefer the latter — it keeps the e2e deterministic).
- **Bank account availability.** The transit-payoff step requires at least one asset account. If the seed does not already include a demo bank account, add one (`"Bank (PLN)"`, `type="bank"`, `opening_balance=5_000_000`, `is_liability=False`) alongside the Visa demo.
- **Flake avoidance.** Use `expect(...)` from Playwright (auto-retries) instead of raw `assert`. Do not sleep.
- **Currency formatting.** Assertions match the formatted string (`"10,000.00"`, `"9,500.00"`). If the money filter switches thousands separators, update the assertions in one place.
- **CHANGELOG discipline.** The Phase 7 landing entry appends to the top of the current day's block; mirror the Phase 6 / Phase 9 kickoff paragraphs. One paragraph, no bullet list.

## Handoff notes

- Phase 7 exit: all seven tasks closed; `just ci` green; CHANGELOG updated. Flip the `README.md` status badge from "pending" to "landed" and strike-through the task table rows in `docs/plans/v1/phase-7/README.md` as each PR merges.
- Follow-ups parked for a later phase (not Phase 7 scope): FX-aware fortune aggregation (T-032), destination-leg soft warnings on transits, additional liability variants (loans, mortgages, lines of credit, overdraft facilities).
- Commit shape: `feat(T-086): seed credit-card demo + e2e journey (ADR-0024)`.
