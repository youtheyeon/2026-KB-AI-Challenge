# 관측 가능한 집행 후 지표만 병목 변화로 판정하는 AI 결과 추적 테스트
import bottleneck_detector
import outcome_tracker


def test_unobserved_preexisting_bottleneck_is_not_marked_resolved(monkeypatch) -> None:
    monkeypatch.setattr(
        outcome_tracker,
        "detect_bottlenecks",
        lambda *args, **kwargs: [
            {"bottleneck_type": "high_cost_ratio"},
            {"bottleneck_type": "high_labor_ratio"},
        ],
    )

    result = outcome_tracker.compare_outcomes(
        pre_findings=[
            {"bottleneck_type": "high_cost_ratio"},
            {"bottleneck_type": "low_repeat_rate"},
        ],
        pre_pos_data={},
        post_pos_data={"monthly_revenue": 8_100_000},
        time_benchmark={},
        time_benchmark_sample_size=0,
        selected_allocation={"custom_1": 1.0},
        loan_amount=15_000_000,
        comparable_bottleneck_types={"high_cost_ratio", "high_labor_ratio"},
    )

    assert result["persisted_bottlenecks"] == ["high_cost_ratio"]
    assert result["new_bottlenecks"] == ["high_labor_ratio"]
    assert result["not_comparable_bottlenecks"] == ["low_repeat_rate"]
    assert result["resolved_bottlenecks"] == []


def test_outcome_tracker_passes_stored_loan_conditions(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr(outcome_tracker, "detect_bottlenecks", lambda *args, **kwargs: [])

    def fake_financial(*args, **kwargs):
        captured.update(args=args, kwargs=kwargs)
        return {"remaining_cash_after_payment": 0}

    monkeypatch.setattr(outcome_tracker, "calculate_financial_projection", fake_financial)

    outcome_tracker.compare_outcomes(
        pre_findings=[],
        pre_pos_data={},
        post_pos_data={"monthly_revenue": 8_100_000},
        time_benchmark={},
        time_benchmark_sample_size=0,
        selected_allocation={"inventory": 0.9},
        loan_amount=15_000_000,
        annual_interest_rate=0.037,
        loan_term_months=48,
        grace_months=6,
        repayment_type="equal_principal",
    )

    assert captured["kwargs"] == {
        "allocation": {"inventory": 0.9},
        "loan_amount": 15_000_000,
        "baseline_monthly_revenue": 8_100_000,
        "annual_interest_rate": 0.037,
        "loan_term_months": 48,
        "grace_months": 6,
        "repayment_type": "equal_principal",
    }


def test_detector_does_not_read_unavailable_dimensions() -> None:
    findings = bottleneck_detector.detect_bottlenecks(
        {"monthly_revenue": 8_100_000, "monthly_cogs": 5_100_000},
        time_benchmark={},
        comparable_bottleneck_types={"high_cost_ratio"},
    )

    assert [finding["bottleneck_type"] for finding in findings] == ["high_cost_ratio"]
