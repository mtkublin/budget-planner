"""E2E: add recurring rule → see virtual occurrences → promote a planned one."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import strip_id_prefix

pytestmark = pytest.mark.e2e


def test_recurring_rule_lists_virtual_and_promote_cycle(
    live_server: tuple[str, Path],
    page: Page,
) -> None:
    base_url, _db_path = live_server

    # Seed account + category.
    assert page.request.post(
        f"{base_url}/accounts",
        form={"name": "Checking", "currency": "PLN", "opening_balance": "0.00"},
    ).ok
    assert page.request.post(
        f"{base_url}/categories",
        form={"name": "Rent", "direction": "expense"},
    ).ok

    page.goto(f"{base_url}/accounts")
    account_id = strip_id_prefix(
        page.locator("article[id^='account-']").first.get_attribute("id"),
        "account-",
    )
    page.goto(f"{base_url}/categories")
    rent_row = page.locator("tr[id^='category-']", has_text="Rent").first
    category_id = strip_id_prefix(rent_row.get_attribute("id"), "category-")

    # Create a monthly recurring rule starting 2026-01-15 for 50.00.
    assert page.request.post(
        f"{base_url}/recurring",
        form={
            "cadence": "monthly",
            "start_date": "2026-01-15",
            "category_id": category_id,
            "account_id": account_id,
            "default_amount": "50.00",
            "default_description": "rent",
        },
    ).ok

    # View /planned with a window that captures Jan, Feb, Mar 2026.
    page.goto(f"{base_url}/planned?date_from=2026-01-01&date_to=2026-03-31")
    expect(page.get_by_text("recurring").first).to_be_visible()
    # Three virtual rows, each labelled "recurring".
    recurring_rows = page.locator("tr[id^='planned-v-']")
    expect(recurring_rows).to_have_count(3)

    # Also create a one-off planned so promotion is a real router call.
    planned_resp = page.request.post(
        f"{base_url}/planned",
        form={
            "operation_date": "2026-01-20",
            "category_id": category_id,
            "account_id": account_id,
            "amount": "25.00",
            "description": "one-off",
        },
    )
    assert planned_resp.ok, planned_resp.text()

    # Scrape the persisted row id.
    page.goto(f"{base_url}/planned?date_from=2026-01-01&date_to=2026-03-31")
    persisted_el = page.locator("tr[id^='planned-p-']").first
    planned_id = strip_id_prefix(persisted_el.get_attribute("id"), "planned-p-")

    # Promote with an edited amount.
    promote_resp = page.request.post(
        f"{base_url}/planned/{planned_id}/promote",
        form={
            "operation_date": "2026-01-22",
            "amount": "27.50",
            "description": "promoted one-off",
        },
    )
    assert promote_resp.ok, promote_resp.text()

    # Verify the transaction appears on /transactions with the edited amount.
    page.goto(f"{base_url}/transactions")
    expect(page.get_by_text("27.50").first).to_be_visible()
