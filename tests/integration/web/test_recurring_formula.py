"""Integration tests for formula-derived recurring amount (ADR-0041).

Covers:
- Formula sum uses other recurring rules' amounts in the same month.
- Formula amount is recomputed at promote time (not frozen at save).
- Repository persists + hydrates the JSON formula round-trip.
- POST /recurring with amount_source=formula renders a formula row.
- Formula rules filtered out of the sum (cycle guard) at compute time.
- Save-time rejection when a source category contains a formula rule.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient

from budget_planner.domain.enums import Direction
from budget_planner.domain.recurring import AmountFormula
from budget_planner.repositories import (
    recurring as recurring_repo,
)
from budget_planner.services import recurring as recurring_svc, recurring_formula as formula_svc


@pytest.fixture
def income_category_a(make_category: Callable[..., int]) -> int:
    return make_category(name="Salary A", direction=Direction.INCOME)


@pytest.fixture
def income_category_b(make_category: Callable[..., int]) -> int:
    return make_category(name="Salary B", direction=Direction.INCOME)


@pytest.fixture
def expense_category(make_category: Callable[..., int]) -> int:
    return make_category(name="Tax", direction=Direction.EXPENSE)


@pytest.fixture
def account_id(make_account: Callable[..., int]) -> int:
    return make_account(name="Main")


class TestComputeFormulaAmount:
    def test_sums_sources_in_same_month(
        self,
        conn: sqlite3.Connection,
        make_rule: Callable[..., int],
        account_id: int,
        income_category_a: int,
        income_category_b: int,
    ) -> None:
        make_rule(
            account_id=account_id,
            category_id=income_category_a,
            amount=10_000_00,
            start_date=date(2026, 1, 10),
        )
        make_rule(
            account_id=account_id,
            category_id=income_category_b,
            amount=5_000_00,
            start_date=date(2026, 1, 15),
        )
        formula = AmountFormula(
            coefficient_bps=1200,  # 12%
            source_category_ids=(income_category_a, income_category_b),
        )
        amount = formula_svc.compute_formula_amount(conn, formula, 2026, 1, exclude_rule_id=None)
        # 12% of 15 000.00 = 1 800.00 → 180 000 minor
        assert amount == 180_000

    def test_skips_formula_sources(
        self,
        conn: sqlite3.Connection,
        make_rule: Callable[..., int],
        account_id: int,
        income_category_a: int,
    ) -> None:
        # A formula rule in the source category: should be skipped at compute
        # time (ADR-0041 cycle guard). The compute still returns 0 instead of
        # recursing or raising.
        make_rule(
            account_id=account_id,
            category_id=income_category_a,
            amount=1_000_00,
            amount_formula=AmountFormula(
                coefficient_bps=1000,
                source_category_ids=(income_category_a,),
            ),
        )
        formula = AmountFormula(
            coefficient_bps=1200,
            source_category_ids=(income_category_a,),
        )
        amount = formula_svc.compute_formula_amount(conn, formula, 2026, 1, exclude_rule_id=None)
        assert amount == 0


class TestRepositoryRoundTrip:
    def test_formula_json_persists(
        self,
        conn: sqlite3.Connection,
        make_rule: Callable[..., int],
        account_id: int,
        expense_category: int,
    ) -> None:
        formula = AmountFormula(coefficient_bps=1250, source_category_ids=(1, 2, 3))
        rule_id = make_rule(
            account_id=account_id,
            category_id=expense_category,
            amount=0,  # formula rule may snapshot 0 — CHECK relaxed in migration 0008
            amount_formula=formula,
        )
        loaded = recurring_repo.find_rule(conn, rule_id)
        assert loaded is not None
        assert loaded.amount_formula is not None
        assert loaded.amount_formula.coefficient_bps == 1250
        assert loaded.amount_formula.source_category_ids == (1, 2, 3)


class TestPromoteRecurring:
    def test_promote_uses_live_formula_amount(
        self,
        conn: sqlite3.Connection,
        make_rule: Callable[..., int],
        account_id: int,
        income_category_a: int,
        expense_category: int,
    ) -> None:
        make_rule(
            account_id=account_id,
            category_id=income_category_a,
            amount=10_000_00,
            start_date=date(2026, 2, 1),
        )
        # Formula rule next_due is also Feb 2026 → should pick up the above sum.
        tax_id = make_rule(
            account_id=account_id,
            category_id=expense_category,
            amount=1,  # placeholder — CHECK requires non-zero for the snapshot
            start_date=date(2026, 2, 15),
            amount_formula=AmountFormula(
                coefficient_bps=1200,
                source_category_ids=(income_category_a,),
            ),
        )
        edits = recurring_svc.PromotionEdits()
        txn = recurring_svc.promote_recurring(conn, tax_id, edits)
        # 12% of 10 000.00 = 120 000 minor
        assert txn.amount == 120_000
        assert txn.promoted_from_recurring_rule_id == tax_id

    def test_explicit_amount_still_wins_over_formula(
        self,
        conn: sqlite3.Connection,
        make_rule: Callable[..., int],
        account_id: int,
        income_category_a: int,
        expense_category: int,
    ) -> None:
        make_rule(
            account_id=account_id,
            category_id=income_category_a,
            amount=10_000_00,
            start_date=date(2026, 2, 1),
        )
        tax_id = make_rule(
            account_id=account_id,
            category_id=expense_category,
            amount=1,
            start_date=date(2026, 2, 15),
            amount_formula=AmountFormula(
                coefficient_bps=1200,
                source_category_ids=(income_category_a,),
            ),
        )
        edits = recurring_svc.PromotionEdits(amount_minor=500_00)
        txn = recurring_svc.promote_recurring(conn, tax_id, edits)
        assert txn.amount == 500_00


class TestValidateFormulaSources:
    def test_rejects_formula_in_source_category(
        self,
        conn: sqlite3.Connection,
        make_rule: Callable[..., int],
        account_id: int,
        income_category_a: int,
    ) -> None:
        make_rule(
            account_id=account_id,
            category_id=income_category_a,
            amount=1,
            amount_formula=AmountFormula(
                coefficient_bps=1000,
                source_category_ids=(income_category_a,),
            ),
        )
        formula = AmountFormula(
            coefficient_bps=1200,
            source_category_ids=(income_category_a,),
        )
        with pytest.raises(formula_svc.FormulaError):
            formula_svc.validate_formula_sources(conn, formula, exclude_rule_id=None)


class TestFormulaRouter:
    def test_create_formula_rule_round_trips(
        self,
        client: TestClient,
        make_rule: Callable[..., int],
        account_id: int,
        income_category_a: int,
        expense_category: int,
    ) -> None:
        # Baseline fixed income rule so the formula has something to sum.
        make_rule(
            account_id=account_id,
            category_id=income_category_a,
            amount=10_000_00,
            start_date=date(2026, 3, 1),
        )
        response = client.post(
            "/recurring",
            data={
                "cadence": "monthly",
                "start_date": "2026-03-10",
                "category_id": str(expense_category),
                "account_id": str(account_id),
                "default_amount": "",
                "default_description": "Monthly tax",
                "day_of_month": "10",
                "amount_source": "formula",
                "coefficient_percent": "12",
                "source_category_ids": [str(income_category_a)],
            },
        )
        assert response.status_code == 200, response.text
        assert "formula-chip" in response.text or "data-formula-amount" in response.text
