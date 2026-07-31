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
from allocation_draft_generator import generate_scenario_drafts, BOTTLENECK_TO_CATEGORY, CATEGORIES
from financial_calculator import calculate_financial_projection
from scb_outlook import generate_scb_outlook
from llm_explainer import generate_scenario_explanation
from business_history import (
    compute_personal_baselines,
    compute_persistence_counts,
    compute_escalated_min_shares,
    compute_tradeoff_warnings,
)

# 재현성을 위한 버전 정보 (스펙 19번). 로직을 바꿀 때마다 사람이 수동으로 올린다.
BENCHMARK_VERSION = "2026-07-v2"
DIAGNOSIS_VERSION = "1.2"  # 개인 기준선 치환 메커니즘 추가
ALLOCATION_GENERATOR_VERSION = "1.2"  # 지속 병목 최소비중 상향 메커니즘 추가
CALCULATION_VERSION = "1.1"  # 손익분기 3필드 추가
PROMPT_VERSION = "1.1"  # 부작용(trade-off) 경고 반영


def run_allocation_simulation(
    findings: list[dict],
    loan: dict,
    pos_data: dict,
    min_shares: dict = None,
    tradeoff_warnings: list = None,
) -> dict:
    """저장된 병목 진단을 사용해 A·B·C 배분안과 재무 결과를 생성한다.

    min_shares/tradeoff_warnings는 회차 히스토리(business_history.py)에서 파생되는 선순환
    메커니즘 입력값이다. 둘 다 생략 가능 -- 저장된 findings만으로 1회차와 동일하게 동작한다.
    """
    drafts = generate_scenario_drafts(findings, min_shares=min_shares)

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

        # [3-3] LLM 설명 (배분근거 + SCB성장가능성 + 부작용경고, 시나리오당 1회 호출)
        explanation = generate_scenario_explanation(
            scenario_id=d["scenario_id"],
            scenario_label=d["label"],
            allocation=d["allocation"],
            diagnosis=findings,
            scb_outlook=scb_result["scb_outlook"],
            tradeoff_warnings=tradeoff_warnings,
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


def run_simulation(profile: dict, loan: dict, pos_data: dict, business_history: list = None) -> dict:
    """
    profile: {"trade_area_usage_type": "university", "monthly_revenue_band": "500-1000", ...}
    loan: {"amount": 15000000, "annual_interest_rate": 0.045, "term_months": 36}
    pos_data: mock_pos_data.py와 동일한 스키마 (실제 연동 시 이 부분만 실제 데이터로 교체)
    business_history: 이 사업자의 과거 회차 기록 (business_history.py 참고). None이면 1회차로 간주,
                      업계 가정치·기본 최소비중을 그대로 사용한다.

    반환: 병목 진단 + 시나리오별(A/B/C) 재무결과·SCB설명이 모두 담긴 딕셔너리

    ── 선순환 3대 메커니즘 (회차가 쌓일수록 자동으로 정교해짐, ML 아님, 결정론적 규칙) ──
      1) 개인 기준선 치환: 3회차부터 원가율/인건비율/재구매율 벤치마크가 본인 과거 실측 평균으로 전환
      2) 지속 병목 가중치 상향: 같은 병목 2회 연속 발생 시 해당 카테고리 최소비중 5%->15%
      3) 부작용 이력 추적: 과거 특정 카테고리 배분 이후 새 병목이 발생한 이력을 LLM 설명에 경고로 반영
    """
    business_history = business_history or []

    # ── 메커니즘 1: 개인 기준선 (회차 3 이상 쌓였을 때만 작동, 그 전엔 None -> 업계 가정치 유지) ──
    personal_baselines = compute_personal_baselines(business_history)

    # [1] 병목 진단 -- K-means 클러스터링으로 찾은 '유사 소비패턴 그룹' 대비 진단 + 개인기준선 반영
    findings, cluster_info = detect_bottlenecks_with_ai_clustering(
        pos_data, personal_baselines=personal_baselines
    )

    # ── 메커니즘 2: 지속 병목 가중치 상향 ──
    persistence_counts = compute_persistence_counts(business_history)
    escalated_min_shares = compute_escalated_min_shares(persistence_counts, BOTTLENECK_TO_CATEGORY, CATEGORIES)

    # ── 메커니즘 3: 부작용(trade-off) 이력 ──
    tradeoff_warnings = compute_tradeoff_warnings(business_history, BOTTLENECK_TO_CATEGORY)

    # [2]+[3] 배분안 생성 + 재무/SCB/LLM 설명 (지속 병목 최소비중 상향 + 부작용 경고 반영)
    result = run_allocation_simulation(
        findings, loan, pos_data, min_shares=escalated_min_shares, tradeoff_warnings=tradeoff_warnings
    )

    return {
        **result,
        "ai_cluster_assignment": cluster_info,
        "personalization_status": {
            "round_number": len(business_history) + 1,
            "using_personal_baseline": personal_baselines is not None,
            "personal_baseline_basis_rounds": personal_baselines["based_on_rounds"] if personal_baselines else 0,
            "escalated_categories": [c for c, v in escalated_min_shares.items() if v > 0.05],
            "active_tradeoff_warnings": tradeoff_warnings,
        },
    }


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

    # 1회차: 히스토리 없음 -> 업계 가정치, 기본 최소비중(5%) 그대로
    pos_data_r1 = generate_mock_pos_data(scenario="high_cost_ratio", monthly_revenue=7_500_000)
    result_r1 = run_simulation(profile, loan, pos_data_r1, business_history=[])

    print("=" * 70)
    print("1회차 (히스토리 없음)")
    print("=" * 70)
    print(f"개인기준선 사용여부: {result_r1['personalization_status']['using_personal_baseline']}")
    for f in result_r1["bottleneck_diagnosis"]:
        print(f"  [{f['title']}] 근거: {f['evidence_source']} / 신뢰도 {f['confidence_badge']}")

    # 가짜 히스토리 구성: 원가율 병목이 2회 연속 발생했다고 가정 (2,3회차)
    fake_history = [
        {
            "round": 1,
            "findings": result_r1["bottleneck_diagnosis"],
            "pos_data": pos_data_r1,
            "selected_allocation": {"marketing_online": 0.2, "equipment_interior": 0.6, "labor": 0.1, "inventory": 0.1},
        },
        {
            "round": 2,
            "findings": [{"bottleneck_type": "high_cost_ratio"}],
            "pos_data": generate_mock_pos_data(scenario="high_cost_ratio", monthly_revenue=8_000_000),
            "selected_allocation": {"marketing_online": 0.2, "equipment_interior": 0.6, "labor": 0.1, "inventory": 0.1},
        },
        {
            "round": 3,
            "findings": [{"bottleneck_type": "high_cost_ratio"}],
            "pos_data": generate_mock_pos_data(scenario="high_cost_ratio", monthly_revenue=8_200_000),
            "selected_allocation": {"marketing_online": 0.2, "equipment_interior": 0.6, "labor": 0.1, "inventory": 0.1},
        },
    ]

    pos_data_r4 = generate_mock_pos_data(scenario="high_cost_ratio", monthly_revenue=8_400_000)
    result_r4 = run_simulation(profile, loan, pos_data_r4, business_history=fake_history)

    print("\n" + "=" * 70)
    print("4회차 (3회 히스토리 누적 -> 개인기준선 전환 + 지속병목 상향 발동)")
    print("=" * 70)
    status = result_r4["personalization_status"]
    print(f"개인기준선 사용여부: {status['using_personal_baseline']} ({status['personal_baseline_basis_rounds']}회차 기반)")
    print(f"최소비중 상향된 카테고리: {status['escalated_categories']}")
    print(f"부작용 경고 이력: {status['active_tradeoff_warnings']}")
    for f in result_r4["bottleneck_diagnosis"]:
        print(f"  [{f['title']}] 근거: {f['evidence_source']} / 신뢰도 {f['confidence_badge']}")
    for s in result_r4["scenario_results"]:
        print(f"\n  [{s['scenario_id']}안] 배분: {s['allocation']}")

    # 최종 JSON을 파일로도 저장 -> 백엔드 담당자에게 실제 응답 형태 예시로 전달 가능
    with open("./run_simulation_sample_output.json", "w", encoding="utf-8") as f:
        json.dump(result_r4, f, ensure_ascii=False, indent=2)
    print("\n전체 결과를 run_simulation_sample_output.json 에 저장했습니다.")
