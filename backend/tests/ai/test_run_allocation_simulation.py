# 저장된 진단 findings로 A·B·C 배분안을 생성하는 AI 코어 테스트
import llm_explainer
import pytest
import run_simulation


def stored_finding() -> dict:
    return {
        "bottleneck_type": "high_cost_ratio",
        "title": "원가율 상승",
        "detail": "원가율이 비교 기준보다 높습니다.",
        "comparison_chip": "원가율 비교",
        "evidence_source": "업계 가정치 (실증 데이터 없음)",
        "methodology": "저장 진단 근거",
        "severity": "심각",
        "confidence_badge": "보통",
        "suggested_category": "equipment_interior",
    }


def test_run_allocation_simulation_uses_supplied_findings(monkeypatch) -> None:
    monkeypatch.setattr(
        run_simulation,
        "generate_scenario_explanation",
        lambda **_: {
            "allocation_rationale": "저장된 병목을 사용한 배분 근거",
            "scb_growth_outlook": "정성적 성장 가능성",
        },
    )
    findings = [stored_finding()]

    result = run_simulation.run_allocation_simulation(
        findings,
        {
            "amount": 15_000_000,
            "annual_interest_rate": 0.045,
            "term_months": 36,
            "grace_months": 0,
            "repayment_type": "equal_payment",
        },
        {"monthly_revenue": 7_500_000, "avg_daily_customers": 90},
    )

    assert [item["scenario_id"] for item in result["scenario_results"]] == ["A", "B", "C"]
    assert result["bottleneck_diagnosis"] == findings
    assert all(
        item["allocation_rationale"] == "저장된 병목을 사용한 배분 근거"
        for item in result["scenario_results"]
    )


def test_llm_explainer_raises_runtime_error_when_api_key_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(llm_explainer, "ANTHROPIC_API_KEY", None)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm_explainer.generate_scenario_explanation(
            scenario_id="A",
            scenario_label="병목 집중형",
            allocation={"marketing_online": 0.85},
            diagnosis=[stored_finding()],
            scb_outlook=[],
        )


def test_run_allocation_simulation_applies_completed_business_history(monkeypatch) -> None:
    captured_warnings = []

    def fake_explanation(**kwargs):
        captured_warnings.append(kwargs["tradeoff_warnings"])
        return {
            "allocation_rationale": "이력 반영 배분 근거",
            "scb_growth_outlook": "정성적 성장 가능성",
        }

    monkeypatch.setattr(run_simulation, "generate_scenario_explanation", fake_explanation)
    history = [
        {
            "round": 1,
            "findings": [{"bottleneck_type": "time_of_day_weakness"}],
            "pos_data": {"monthly_revenue": 7_500_000},
            "selected_allocation": {"equipment_interior": 0.60},
        },
        {
            "round": 2,
            "findings": [{"bottleneck_type": "high_cost_ratio"}],
            "pos_data": {"monthly_revenue": 8_000_000},
            "selected_allocation": {"equipment_interior": 0.60},
        },
        {
            "round": 3,
            "findings": [{"bottleneck_type": "high_cost_ratio"}],
            "pos_data": {"monthly_revenue": 8_200_000},
            "selected_allocation": {"equipment_interior": 0.60},
        },
    ]
    current_finding = stored_finding() | {
        "bottleneck_type": "time_of_day_weakness",
        "suggested_category": "marketing_online",
    }

    result = run_simulation.run_allocation_simulation(
        [current_finding],
        {
            "amount": 15_000_000,
            "annual_interest_rate": 0.045,
            "term_months": 36,
            "grace_months": 0,
            "repayment_type": "equal_payment",
        },
        {"monthly_revenue": 7_500_000, "avg_daily_customers": 90},
        business_history=history,
    )

    scenarios = {item["scenario_id"]: item for item in result["scenario_results"]}
    assert scenarios["A"]["allocation"]["equipment_interior"] >= 0.15
    assert scenarios["B"]["allocation"]["equipment_interior"] >= 0.15
    assert captured_warnings[0] == [
        {
            "category": "equipment_interior",
            "resulting_bottleneck": "high_cost_ratio",
            "occurred_after_round": 1,
        }
    ]
