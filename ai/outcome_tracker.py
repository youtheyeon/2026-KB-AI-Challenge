"""
outcome_tracker.py — 집행 전후 비교 및 사업 상태 재평가

스펙 6번([6] 결과 추적, [7] 사업 상태 재평가)에 대응.
track_results_demo.py에서 검증했던 로직을 재사용 가능한 함수로 승격했다.
"""

from bottleneck_detector import detect_bottlenecks
from financial_calculator import calculate_financial_projection


def compare_outcomes(
    pre_findings: list,
    pre_pos_data: dict,
    post_pos_data: dict,
    time_benchmark: dict,
    time_benchmark_sample_size: int,
    selected_allocation: dict,
    loan_amount: int,
    breakeven_additional_revenue_target: float = None,
    comparable_bottleneck_types: set[str] = None,
    annual_interest_rate: float = 0.045,
    loan_term_months: int = 36,
    grace_months: int = 0,
    repayment_type: str = "equal_payment",
) -> dict:
    """
    집행 전(pre) 진단과 집행 후(post) 실제/합성 데이터를 비교해서
    해결된 병목 / 남은 병목 / 신규 병목을 판별하고, 손익분기 기준 대비 결과를 평가한다.

    반환값은 다음 시뮬레이션(run_simulation)의 입력(pos_data)으로 그대로 재사용 가능하다.
    """
    post_findings = detect_bottlenecks(
        post_pos_data,
        time_benchmark,
        time_benchmark_sample_size=time_benchmark_sample_size,
        comparable_bottleneck_types=comparable_bottleneck_types,
    )

    pre_types = {f["bottleneck_type"] for f in pre_findings}
    post_types = {f["bottleneck_type"] for f in post_findings}

    comparable = (
        pre_types | post_types
        if comparable_bottleneck_types is None
        else set(comparable_bottleneck_types)
    )
    resolved = (pre_types & comparable) - post_types
    persisted = (pre_types & comparable) & post_types
    newly_emerged = post_types - pre_types
    not_comparable = pre_types - comparable

    post_financial = calculate_financial_projection(
        allocation=selected_allocation,
        loan_amount=loan_amount,
        baseline_monthly_revenue=post_pos_data["monthly_revenue"],
        annual_interest_rate=annual_interest_rate,
        loan_term_months=loan_term_months,
        grace_months=grace_months,
        repayment_type=repayment_type,
    )

    status = _classify_breakeven_status(
        post_financial, breakeven_additional_revenue_target, newly_emerged
    )

    return {
        "resolved_bottlenecks": sorted(resolved),
        "persisted_bottlenecks": sorted(persisted),
        "new_bottlenecks": sorted(newly_emerged),
        "not_comparable_bottlenecks": sorted(not_comparable),
        "post_execution_findings": post_findings,
        "post_execution_financial_result": post_financial,
        "breakeven_status": status,
        "disclaimer": "집행 전후의 변화는 계절성, 상권 변화, 경쟁점 변화 등 자금 집행 외 요인의 영향을 받을 수 있으며 인과관계를 의미하지 않습니다.",
        # 이 스냅샷이 다음 run_simulation()의 pos_data 입력이 된다
        "next_round_pos_data_snapshot": post_pos_data,
    }


def _classify_breakeven_status(financial_result: dict, target_revenue: float, newly_emerged: set) -> dict:
    """
    조건 충족 / 일부 충족 / 미충족 / 비교 불가 4단계 판정 (스펙 12.3)
    """
    remaining_cash = financial_result["remaining_cash_after_payment"]

    if target_revenue is None:
        return {"status": "비교 불가", "reason": "집행 전 손익분기 목표값이 없어 비교할 수 없습니다."}

    if remaining_cash >= 0 and not newly_emerged:
        return {"status": "조건 충족", "reason": "잔여현금이 양수이며 새로 발생한 병목이 없습니다."}

    if remaining_cash >= 0 and newly_emerged:
        return {"status": "일부 충족", "reason": "잔여현금은 양수이나, 새로운 병목이 발생했습니다."}

    # remaining_cash < 0 인 경우: 목표 대비 얼마나 못 미쳤는지로 세분화
    shortfall_ratio = abs(remaining_cash) / target_revenue if target_revenue else 1.0
    if shortfall_ratio <= 0.5:
        return {"status": "일부 충족", "reason": "목표 손익분기 매출의 상당 부분을 달성했으나 아직 미달입니다."}

    return {"status": "미충족", "reason": "목표 손익분기 매출 대비 크게 미달했습니다."}


if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data
    from bottleneck_detector import compute_time_of_day_benchmark_with_sample_size
    from allocation_draft_generator import generate_scenario_drafts

    time_benchmark, sample_size = compute_time_of_day_benchmark_with_sample_size()
    loan_amount = 15_000_000

    # 1회차
    pre_pos = generate_mock_pos_data(scenario="evening_weak", monthly_revenue=7_500_000)
    pre_findings = detect_bottlenecks(pre_pos, time_benchmark, time_benchmark_sample_size=sample_size)
    drafts = generate_scenario_drafts(pre_findings)
    chosen = next(d for d in drafts if d["scenario_id"] == "B")
    pre_financial = calculate_financial_projection(chosen["allocation"], loan_amount, pre_pos["monthly_revenue"])

    print(f"1회차 병목: {[f['title'] for f in pre_findings]}")
    print(f"1회차 선택안: {chosen['scenario_id']}안, 잔여현금: {pre_financial['remaining_cash_after_payment']:,}원")

    # 2회차 (가정된 결과) - track_results_demo.py와 동일한 시나리오
    post_pos = generate_mock_pos_data(scenario="normal", monthly_revenue=8_100_000)
    post_pos["time_of_day_sales"]["TMZON_17_21_SELNG_AMT"] = round(8_100_000 * 0.195)
    post_pos["monthly_cogs"] = round(8_100_000 * 0.58)

    result = compare_outcomes(
        pre_findings=pre_findings,
        pre_pos_data=pre_pos,
        post_pos_data=post_pos,
        time_benchmark=time_benchmark,
        time_benchmark_sample_size=sample_size,
        selected_allocation=chosen["allocation"],
        loan_amount=loan_amount,
        breakeven_additional_revenue_target=abs(pre_financial["remaining_cash_after_payment"]) / 0.58,
    )

    print(f"\n해결된 병목: {result['resolved_bottlenecks']}")
    print(f"남은 병목: {result['persisted_bottlenecks']}")
    print(f"신규 병목: {result['new_bottlenecks']}")
    print(f"손익분기 판정: {result['breakeven_status']}")
    print(f"\n다음 시뮬레이션 입력으로 쓸 스냅샷 준비 완료 (next_round_pos_data_snapshot)")
