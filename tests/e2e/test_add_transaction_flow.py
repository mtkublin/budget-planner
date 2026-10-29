"""E2E: create account → add transaction → see balance update."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import strip_id_prefix

pytestmark = pytest.mark.e2e


def test_add_transaction_updates_account_balance(
    live_server: tuple[str, Path],
    page: Page,
) -> None:
    base_url, _db_path = live_server

    # 1. Create a Checking account with opening_balance 100.00 PLN.
    create_resp = page.request.post(
        f"{base_url}/accounts",
        form={
            "name": "Checking",
            "currency": "PLN",
            "opening_balance": "100.00",
        },
    )
    assert create_resp.ok, create_resp.text()

    # 2. Create an expense category "Groceries".
    cat_resp = page.request.post(
        f"{base_url}/categories",
        form={"name": "Groceries", "direction": "expense"},
    )
    assert cat_resp.ok, cat_resp.text()

    # 3. Discover the created ids by scraping the accounts/categories pages.
    page.goto(f"{base_url}/accounts")
    expect(page.locator("text=Checking")).to_be_visible()
    # Opening balance renders as "100.00 zł".
    expect(page.get_by_text("100.00").first).to_be_visible()

    # Find the account_id by inspecting the row wrapper.
    account_el = page.locator("tr[id^='account-']").first
    account_id = strip_id_prefix(account_el.get_attribute("id"), "account-")

    # Find the category id by posting a form POST that reads back the row.
    page.goto(f"{base_url}/categories")
    groceries_row = page.locator("[id^='category-']", has_text="Groceries").first
    category_id = strip_id_prefix(groceries_row.get_attribute("id"), "category-")

    # 4. Post a 20.00 expense transaction.
    txn_resp = page.request.post(
        f"{base_url}/transactions",
        form={
            "operation_date": "2026-01-15",
            "category_id": category_id,
            "account_id": account_id,
            "amount": "20.00",
            "description": "milk",
        },
    )
    assert txn_resp.ok, txn_resp.text()

    # 5. Confirm balance on /accounts flipped to 80.00.
    page.goto(f"{base_url}/accounts")
    checking_card = page.locator(f"#account-{account_id}")
    expect(checking_card).to_contain_text("Checking")
    expect(checking_card).to_contain_text("80.00")
