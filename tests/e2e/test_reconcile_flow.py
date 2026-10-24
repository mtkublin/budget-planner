"""E2E: reconcile an account, confirm adjustment transaction created."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import strip_id_prefix

pytestmark = pytest.mark.e2e


def test_reconcile_creates_adjustment_transaction(
    live_server: tuple[str, Path],
    page: Page,
) -> None:
    base_url, _db_path = live_server

    # Seed account with opening 100.00; add an expense of 40.00 → derived 60.00.
    assert page.request.post(
        f"{base_url}/accounts",
        form={"name": "Checking", "currency": "PLN", "opening_balance": "100.00"},
    ).ok
    assert page.request.post(
        f"{base_url}/categories",
        form={"name": "Food", "direction": "expense"},
    ).ok

    page.goto(f"{base_url}/accounts")
    account_id = strip_id_prefix(
        page.locator("article[id^='account-']").first.get_attribute("id"),
        "account-",
    )

    page.goto(f"{base_url}/categories")
    food_row = page.locator("tr[id^='category-']", has_text="Food").first
    category_id = strip_id_prefix(food_row.get_attribute("id"), "category-")

    assert page.request.post(
        f"{base_url}/transactions",
        form={
            "operation_date": "2026-01-15",
            "category_id": category_id,
            "account_id": account_id,
            "amount": "40.00",
            "description": "snack",
        },
    ).ok

    # Reconcile: user asserts actual 70.00 → delta +10.00 adjustment.
    reconcile_resp = page.request.post(
        f"{base_url}/accounts/{account_id}/reconcile",
        form={"actual_balance": "70.00"},
    )
    assert reconcile_resp.ok, reconcile_resp.text()

    # Account card now shows 70.00.
    page.goto(f"{base_url}/accounts")
    checking_card = page.locator(f"#account-{account_id}")
    expect(checking_card).to_contain_text("70.00")

    # Transactions page should contain a 10.00 adjustment row (direction = adjustment).
    page.goto(f"{base_url}/transactions")
    expect(page.get_by_text("10.00").first).to_be_visible()
    expect(page.get_by_text("auto-reconciliation").first).to_be_visible()
