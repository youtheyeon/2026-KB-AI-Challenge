# 같은 프로세스 AI 어댑터의 입력 변환과 예외 경계를 검증하는 테스트
from decimal import Decimal

import pytest

from app.domain.enums import RepaymentType
from app.services.simulation_engine import (
    InProcessSimulationEngine,
    SimulationEngineRequest,
    SimulationGenerationError,
)


def simulation_request() -> SimulationEngineRequest:
    return SimulationEngineRequest(
        findings=({"bottleneck_type": "high_cost_ratio"},),
        business_history=(
            {
                "round": 1,
                "findings": [{"bottleneck_type": "high_cost_ratio"}],
                "pos_data": {"monthly_revenue": 8_100_000},
                "selected_allocation": {"equipment_interior": 0.6},
            },
        ),
        loan_amount=15_000_000,
        annual_interest_rate=Decimal("0.045"),
        term_months=36,
        grace_months=3,
        repayment_type=RepaymentType.EQUAL_PAYMENT,
        baseline_monthly_revenue=7_500_000,
        average_daily_customers=90,
    )


def test_engine_translates_request_to_ai_payload() -> None:
    captured = {}

    def fake_runner(findings, loan, pos_data, *, business_history):
        captured.update(
            findings=findings,
            loan=loan,
            pos_data=pos_data,
            business_history=business_history,
        )
        return {"scenario_results": []}

    engine = InProcessSimulationEngine(loader=lambda: fake_runner)

    assert engine.run(simulation_request()) == {"scenario_results": []}
    assert captured == {
        "findings": [{"bottleneck_type": "high_cost_ratio"}],
        "loan": {
            "amount": 15_000_000,
            "annual_interest_rate": 0.045,
            "term_months": 36,
            "grace_months": 3,
            "repayment_type": "equal_payment",
        },
        "pos_data": {
            "monthly_revenue": 7_500_000,
            "avg_daily_customers": 90,
        },
        "business_history": [
            {
                "round": 1,
                "findings": [{"bottleneck_type": "high_cost_ratio"}],
                "pos_data": {"monthly_revenue": 8_100_000},
                "selected_allocation": {"equipment_interior": 0.6},
            }
        ],
    }


def test_engine_wraps_runtime_error_without_exposing_original_message() -> None:
    def failing_runner(*_):
        raise RuntimeError("secret-bearing upstream message")

    engine = InProcessSimulationEngine(loader=lambda: failing_runner)

    with pytest.raises(
        SimulationGenerationError,
        match="시뮬레이션 결과 생성에 실패했습니다",
    ) as caught:
        engine.run(simulation_request())

    assert "secret-bearing" not in str(caught.value)


def test_engine_rejects_invalid_result_shape() -> None:
    engine = InProcessSimulationEngine(loader=lambda: lambda *_, **__: {"unexpected": []})

    with pytest.raises(SimulationGenerationError, match="유효하지 않은 결과"):
        engine.run(simulation_request())
