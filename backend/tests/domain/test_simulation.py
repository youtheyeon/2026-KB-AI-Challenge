# 고정 A·B·C 시나리오와 자금 배분 불변조건을 검증하는 테스트
from dataclasses import is_dataclass
from decimal import Decimal

import pytest

from app.db.base import Base
from app.domain.enums import AllocationCategory, RepaymentType, ScenarioCode
from app.domain.simulation import (
    LoanCondition,
    Scenario,
    ScenarioAllocation,
    ScenarioFinancialResult,
    Simulation,
)


def allocation(category: AllocationCategory, ratio: str, amount: int) -> ScenarioAllocation:
    return ScenarioAllocation(category=category, ratio=Decimal(ratio), amount=amount)


def scenario(code: ScenarioCode) -> Scenario:
    return Scenario(
        code=code,
        strategy_type="fixed",
        title=code.value,
        total_amount=1_000,
        allocations=[
            allocation(AllocationCategory.MARKETING_ONLINE, "0.25", 250),
            allocation(AllocationCategory.EQUIPMENT_INTERIOR, "0.25", 250),
            allocation(AllocationCategory.LABOR, "0.25", 250),
            allocation(AllocationCategory.INVENTORY, "0.25", 250),
        ],
    )


def test_loan_and_financial_result_are_value_objects_not_entities() -> None:
    assert is_dataclass(LoanCondition)
    assert is_dataclass(ScenarioFinancialResult)
    assert not issubclass(LoanCondition, Base)
    assert not issubclass(ScenarioFinancialResult, Base)
    assert "loan_condition" in Simulation.__mapper__.composites
    assert "financial_result" in Scenario.__mapper__.composites


def test_simulation_requires_exactly_one_scenario_for_each_code() -> None:
    simulation = Simulation(
        loan_condition=LoanCondition(
            amount=1_000,
            annual_interest_rate=Decimal("0.045"),
            term_months=36,
            grace_months=0,
            repayment_type=RepaymentType.EQUAL_PAYMENT,
        ),
        scenarios=[scenario(ScenarioCode.A), scenario(ScenarioCode.B), scenario(ScenarioCode.C)],
    )

    simulation.validate_scenarios()


def test_simulation_rejects_missing_scenario_code() -> None:
    simulation = Simulation(
        loan_condition=LoanCondition(
            amount=1_000,
            annual_interest_rate=Decimal("0.045"),
            term_months=36,
            grace_months=0,
            repayment_type=RepaymentType.EQUAL_PAYMENT,
        ),
        scenarios=[scenario(ScenarioCode.A), scenario(ScenarioCode.B)],
    )

    with pytest.raises(ValueError, match="A, B, C"):
        simulation.validate_scenarios()


def test_scenario_requires_four_categories_and_exact_totals() -> None:
    valid = scenario(ScenarioCode.A)
    valid.validate_allocations()

    valid.allocations[0].ratio = Decimal("0.04")
    with pytest.raises(ValueError, match="5%"):
        valid.validate_allocations()
