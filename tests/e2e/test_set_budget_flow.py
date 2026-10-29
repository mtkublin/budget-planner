"""E2E: set a default budget, record spend, see remaining."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import strip_id_prefix

pytestmark = pytest.mark.e2e


def test_set_budget_shows_remaining_after_spend(
    live_server: tuple[str, Path],
    page: Page,
) -> None:
    base_url, _db_path = live_server

    # Seed: one account + Groceries category.
    assert page.request.post(
        f"{base_url}/accounts",
        form={"name": "Checking", "currency": "PLN", "opening_balance": "500.00"},
    ).ok
    assert page.request.post(
        f"{base_url}/categories",
        form={"name": "Groceries", "direction": "expense"},
    ).ok

    # Discover ids by scraping /accounts and /categories.
    page.goto(f"{base_url}/accounts")
    account_id = strip_id_prefix(
        page.locator("tr[id^='account-']").first.get_attribute("id"),
        "account-",
    )
    page.goto(f"{base_url}/categories")
    groceries_row = page.locator("tr[id^='category-']", has_text="Groceries").first
    category_id = strip_id_prefix(groceries_row.get_attribute("id"), "category-")

    # Set a default budget of 500.00 for Groceries.
    assert page.request.post(
        f"{base_url}/budget/defaults/{category_id}",
        form={"amount": "500.00"},
    ).ok

    # Record a 120.00 expense in a known month to query /budget deterministically.
    assert page.request.post(
        f"{base_url}/transactions",
        form={
            "operation_date": "2026-10-15",
            "category_id": category_id,
            "account_id": account_id,
            "amount": "120.00",
            "description": "weekly shop",
        },
    ).ok

    # Visit /budget for the same month. Phase 9 (T-100/T-101) refactored
    # the summary surface: `#budget-summary` is a `<section>` wrapping a
    # `<table class="budget-row-table">`; the id no longer sits on the table.
    page.goto(f"{base_url}/budget?year=2026&month=10")
    groceries_row = page.locator(
        "#budget-summary table.budget-row-table tr",
        has_text="Groceries",
    ).first
    expect(groceries_row).to_contain_text("Groceries")
    # Budgeted
    expect(groceries_row).to_contain_text("500.00")
    # Spent
    expect(groceries_row).to_contain_text("120.00")
    # Remaining
    expect(groceries_row).to_contain_text("380.00")
