"""
run_simulation.py — AI 엔진 전체를 묶는 단일 진입점

백엔드는 이 파일의 run_simulation(profile, loan, pos_data) 함수 하나만 호출하면 된다.
내부적으로 지금까지 만든 6개 컴포넌트를 순서대로 실행해서 최종 결과를 하나의 딕셔너리로 반환한다.

흐름:
  [1] 병목 진단 (bottleneck_detector) - 실데이터 벤치마크 + 업계 가정치
  [2] 배분안 생성 (allocation_draft_generator) - A/B/C 고정값
  [3] 각 시나리오별로:
        [3-1] 재무 계산 (financial_calculator) - 가정 없는 순수 계산
        [3-2] SCB 방향성 매핑 (scb_outlook) - 정성적, 숫자 없음
        [3-3] LLM 설명 생성 (llm_explainer) - 배분근거 + SCB성장가능성
  [4] 전체 결과를 하나의 JSON으로 조립
"""

import json

from bottleneck_detector import detect_bottlenecks_with_ai_clustering
from allocation_draft_generator import generate_scenario_drafts
from financial_calculator import calculate_financial_projection
from scb_outlook import generate_scb_outlook
from llm_explainer import generate_scenario_explanation

# 재현성을 위한 버전 정보 (스펙 19번). 로직을 바꿀 때마다 사람이 수동으로 올린다.
BENCHMARK_VERSION = "2026-07-v2"
DIAGNOSIS_VERSION = "1.1"  # 온라인 채널 병목 4종 추가
ALLOCATION_GENERATOR_VERSION = "1.1"  # target_metrics 필드 추가
CALCULATION_VERSION = "1.1"  # 손익분기 3필드 추가
PROMPT_VERSION = "1.0"


def run_allocation_simulation(findings: list[dict], loan: dict, pos_data: dict) -> dict:
    """저장된 병목 진단을 사용해 A·B·C 배분안과 재무 결과를 생성한다."""
    drafts = generate_scenario_drafts(findings)

    loan_amount = loan["amount"]
    baseline_revenue = pos_data["monthly_revenue"]
    annual_rate = loan.get("annual_interest_rate")
    term_months = loan.get("term_months")

    scenario_results = []
    for d in drafts:
        # [3-1] 재무 계산
        finance_kwargs = {}
        if annual_rate is not None:
            finance_kwargs["annual_interest_rate"] = annual_rate
        if term_months is not None:
            finance_kwargs["loan_term_months"] = term_months
        finance_kwargs["grace_months"] = loan.get("grace_months", 0)
        finance_kwargs["repayment_type"] = loan.get("repayment_type", "equal_payment")

        financial_result = calculate_financial_projection(
            allocation=d["allocation"],
            loan_amount=loan_amount,
            baseline_monthly_revenue=baseline_revenue,
            avg_daily_customers=pos_data.get("avg_daily_customers"),
            **finance_kwargs,
        )

        # [3-2] SCB 방향성
        scb_result = generate_scb_outlook(d["allocation"])

        # [3-3] LLM 설명 (배분근거 + SCB성장가능성, 시나리오당 1회 호출)
        explanation = generate_scenario_explanation(
            scenario_id=d["scenario_id"],
            scenario_label=d["label"],
            allocation=d["allocation"],
            diagnosis=findings,
            scb_outlook=scb_result["scb_outlook"],
        )

        # 배분 비율을 실제 원 단위 금액으로도 변환 -> 화면/설명에서 "몇 %"뿐 아니라 "몇 원"도 보여주기 위함
        allocation_amounts = {cat: round(loan_amount * pct) for cat, pct in d["allocation"].items()}

        scenario_results.append({
            "scenario_id": d["scenario_id"],
            "label": d["label"],
            "allocation": d["allocation"],
            "allocation_amounts_won": allocation_amounts,
            "loan_amount": loan_amount,
            "target_metrics": d.get("target_metrics", []),
            "financial_result": financial_result,
            "scb_outlook": scb_result["scb_outlook"],
            "allocation_rationale": explanation.get("allocation_rationale"),
            "scb_growth_outlook": explanation.get("scb_growth_outlook"),
        })

    return {
        "bottleneck_diagnosis": findings,
        "scenario_results": scenario_results,
        "note": "AI는 특정 안을 추천하지 않습니다. 진단 결과와 재무 계산을 참고해 직접 선택하세요.",
        "versions": {
            "benchmark_version": BENCHMARK_VERSION,
            "diagnosis_version": DIAGNOSIS_VERSION,
            "allocation_generator_version": ALLOCATION_GENERATOR_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "prompt_version": PROMPT_VERSION,
        },
    }


def run_simulation(profile: dict, loan: dict, pos_data: dict) -> dict:
    """
    profile: {"trade_area_usage_type": "university", "monthly_revenue_band": "500-1000", ...}
    loan: {"amount": 15000000, "annual_interest_rate": 0.045, "term_months": 36}
    pos_data: mock_pos_data.py와 동일한 스키마 (실제 연동 시 이 부분만 실제 데이터로 교체)

    반환: 병목 진단 + 시나리오별(A/B/C) 재무결과·SCB설명이 모두 담긴 딕셔너리
    """
    findings, cluster_info = detect_bottlenecks_with_ai_clustering(pos_data)
    result = run_allocation_simulation(findings, loan, pos_data)
    return {**result, "ai_cluster_assignment": cluster_info}


# ─────────────────────────────────────────────
# 실행 (테스트) — 백엔드가 호출할 것과 동일한 방식으로 전체 파이프라인 1회 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data

    profile = {
        "trade_area_usage_type": "university",
        "business_age": "1-3y",
        "store_type": "seated",
        "employee_count": "1-2",
        "monthly_revenue_band": "500-1000",
    }
    loan = {"amount": 15_000_000, "annual_interest_rate": 0.045, "term_months": 36}
    pos_data = generate_mock_pos_data(scenario="multi_bottleneck", monthly_revenue=7_500_000)

    result = run_simulation(profile, loan, pos_data)

    print("=" * 70)
    print("AI 클러스터 배정 결과 (K-means 비지도학습)")
    print("=" * 70)
    ci = result["ai_cluster_assignment"]
    print(f"  클러스터 {ci['cluster_id']}번 배정 (구성원 {ci['cluster_member_count']}개 상권)")
    print(f"  특징: {ci['cluster_dominant_time']}시·{ci['cluster_dominant_weekday']}요일 강세")
    print(f"  대표 상권: {', '.join(ci['cluster_example_trade_areas'][:3])}")

    print("\n" + "=" * 70)
    print("병목 진단 결과")
    print("=" * 70)
    for f in result["bottleneck_diagnosis"]:
        print(f"  [{f['title']}] {f['priority_badge']} / 신뢰도 {f['confidence_badge']}")

    print("\n" + "=" * 70)
    print(f"시나리오별 결과 (대출금 총액: {loan['amount']:,}원)")
    print("=" * 70)
    for s in result["scenario_results"]:
        amt_str = ", ".join(f"{cat} {won:,}원({pct*100:.0f}%)"
                             for cat, won, pct in zip(s["allocation"].keys(), s["allocation_amounts_won"].values(), s["allocation"].values()))
        print(f"\n[{s['scenario_id']}안 - {s['label']}]")
        print(f"  배분: {amt_str}")
        fin = s["financial_result"]
        print(f"  잔여현금: {fin['remaining_cash_after_payment']:,}원 / 위험도: {fin['risk_level']}")
        print(f"  배분근거: {s['allocation_rationale'][:80]}...")
        print(f"  SCB설명: {s['scb_growth_outlook'][:80]}...")

    # 최종 JSON을 파일로도 저장 -> 백엔드 담당자에게 실제 응답 형태 예시로 전달 가능
    with open("./run_simulation_sample_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n전체 결과를 run_simulation_sample_output.json 에 저장했습니다.")
