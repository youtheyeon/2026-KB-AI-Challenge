# 기존 AI 결과 추적 함수를 호출하는 같은 프로세스 어댑터 테스트
from decimal import Decimal

import pytest

from app.domain.enums import RepaymentType
from app.services.outcome_engine import (
    FinancialProjectionRequest,
    InProcessOutcomeEngine,
    OutcomeCalculationError,
    OutcomeEngineRequest,
)


def comparison_result() -> dict:
    return {
        "resolved_bottlenecks": [],
        "persisted_bottlenecks": [],
        "new_bottlenecks": [],
        "not_comparable_bottlenecks": [],
        "post_execution_findings": [],
        "post_execution_financial_result": {},
        "breakeven_status": {"status": "비교 불가", "reason": "근거 없음"},
        "next_round_pos_data_snapshot": {"monthly_revenue": 8_100_000},
    }


def engine_request() -> OutcomeEngineRequest:
    return OutcomeEngineRequest(
        allocation={"custom_1": 0.9},
        loan_amount=15_000_000,
        monthly_revenue=8_100_000,
        annual_interest_rate=Decimal("0.045"),
        term_months=36,
        grace_months=0,
        repayment_type=RepaymentType.EQUAL_PAYMENT,
        pre_findings=({"bottleneck_type": "high_cost_ratio"},),
        post_pos_data={"monthly_revenue": 8_100_000},
        comparable_bottleneck_types=frozenset({"high_cost_ratio"}),
        break_even_additional_revenue_target=500_000,
    )


def test_engine_passes_actual_execution_and_loan_conditions() -> None:
    captured = {}

    def fake_compare(**kwargs):
        captured.update(kwargs)
        return comparison_result()

    engine = InProcessOutcomeEngine(
        compare_loader=lambda: fake_compare,
        mock_loader=lambda: lambda **kwargs: {"monthly_revenue": kwargs["monthly_revenue"]},
        benchmark_loader=lambda: lambda: ({"11_14": 0.3}, 326),
        financial_loader=lambda: lambda **kwargs: {},
    )

    assert engine.compare(engine_request()) == comparison_result()
    assert captured["selected_allocation"] == {"custom_1": 0.9}
    assert captured["loan_term_months"] == 36
    assert captured["annual_interest_rate"] == 0.045
    assert captured["comparable_bottleneck_types"] == {"high_cost_ratio"}
    assert captured["time_benchmark_sample_size"] == 326


def test_engine_projects_financials_with_observed_revenue() -> None:
    captured = {}

    def fake_financial(**kwargs):
        captured.update(kwargs)
        return {"monthly_loan_payment": 446_205}

    engine = InProcessOutcomeEngine(
        compare_loader=lambda: lambda **kwargs: comparison_result(),
        mock_loader=lambda: lambda **kwargs: {},
        benchmark_loader=lambda: lambda: ({}, 0),
        financial_loader=lambda: fake_financial,
    )
    request = FinancialProjectionRequest(
        allocation={"inventory": 0.8},
        loan_amount=12_000_000,
        monthly_revenue=9_200_000,
        annual_interest_rate=Decimal("0.037"),
        term_months=48,
        grace_months=6,
        repayment_type=RepaymentType.EQUAL_PRINCIPAL,
    )

    assert engine.project_financial(request) == {"monthly_loan_payment": 446_205}
    assert captured == {
        "allocation": {"inventory": 0.8},
        "loan_amount": 12_000_000,
        "baseline_monthly_revenue": 9_200_000,
        "annual_interest_rate": 0.037,
        "loan_term_months": 48,
        "grace_months": 6,
        "repayment_type": "equal_principal",
    }


def test_engine_generates_normal_mock_for_requested_revenue() -> None:
    captured = {}

    def fake_mock(**kwargs):
        captured.update(kwargs)
        return {"monthly_revenue": kwargs["monthly_revenue"]}

    engine = InProcessOutcomeEngine(
        compare_loader=lambda: lambda **kwargs: comparison_result(),
        mock_loader=lambda: fake_mock,
        benchmark_loader=lambda: lambda: ({}, 0),
        financial_loader=lambda: lambda **kwargs: {},
    )

    assert engine.generate_mock(7_500_000) == {"monthly_revenue": 7_500_000}
    assert captured == {"scenario": "normal", "monthly_revenue": 7_500_000}


def test_engine_rejects_incomplete_comparison_shape() -> None:
    engine = InProcessOutcomeEngine(
        compare_loader=lambda: lambda **kwargs: {"resolved_bottlenecks": []},
        mock_loader=lambda: lambda **kwargs: {},
        benchmark_loader=lambda: lambda: ({}, 0),
        financial_loader=lambda: lambda **kwargs: {},
    )

    with pytest.raises(OutcomeCalculationError, match="결과 검증 계산에 실패했습니다"):
        engine.compare(engine_request())


def test_engine_hides_upstream_exception_message() -> None:
    def failing_compare(**kwargs):
        raise RuntimeError("secret-bearing upstream message")

    engine = InProcessOutcomeEngine(
        compare_loader=lambda: failing_compare,
        mock_loader=lambda: lambda **kwargs: {},
        benchmark_loader=lambda: lambda: ({}, 0),
        financial_loader=lambda: lambda **kwargs: {},
    )

    with pytest.raises(OutcomeCalculationError) as caught:
        engine.compare(engine_request())

    assert "secret-bearing" not in str(caught.value)
