# 시나리오 선택 잠금과 실제 집행금액 불변조건을 검증하는 테스트
import pytest

from app.domain.enums import ExecutionType
from app.domain.execution import Execution, ExecutionAllocation
from app.domain.simulation import ScenarioSelection


def test_selection_rejects_scenario_from_another_simulation() -> None:
    selection = ScenarioSelection(simulation_id=10, scenario_id=100)

    with pytest.raises(ValueError, match="같은 시뮬레이션"):
        selection.validate_scenario(scenario_simulation_id=11)


def test_selection_cannot_change_after_execution_lock() -> None:
    selection = ScenarioSelection(simulation_id=10, scenario_id=100)
    selection.lock()

    with pytest.raises(ValueError, match="집행 등록 후"):
        selection.change_scenario(scenario_id=101)


def test_execution_amount_and_unused_amount_equal_loan_amount() -> None:
    execution = Execution(
        simulation_id=10,
        selection_id=20,
        execution_type=ExecutionType.CUSTOM,
        total_amount=800,
        unused_amount=200,
    )

    execution.validate_amounts(loan_amount=1_000)

    execution.unused_amount = 100
    with pytest.raises(ValueError, match="대출금액"):
        execution.validate_amounts(loan_amount=1_000)


def test_execution_allocation_accepts_free_name_without_category() -> None:
    allocation = ExecutionAllocation(
        name="저녁 시간대 광고",
        category=None,
        amount=800_000,
    )

    assert allocation.name == "저녁 시간대 광고"
    assert allocation.category is None


def test_execution_type_uses_confirmed_api_modes() -> None:
    assert {member.name for member in ExecutionType} == {
        "SAME_AS_A",
        "SAME_AS_B",
        "SAME_AS_C",
        "MIXED",
        "CUSTOM",
    }
