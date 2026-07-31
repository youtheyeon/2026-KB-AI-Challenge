"""
배분안 초안 생성기 (Allocation Draft Generator)

목적: bottleneck_detector가 찾은 병목을 근거로 A/B/C 세 개의 배분안을 생성한다.

설계 변경사항 (v2): 사용자가 슬라이더로 배분을 직접 수정하는 단계는 제거했다.
  이유: 병목 진단 결과를 근거로 만든 배분안을, 사용자가 자유롭게 다시 바꿔버리면
       '진단에 기반한 제안'이라는 의미 자체가 사라지기 때문이다.
  → 사용자는 A/B/C 중 하나를 '선택'만 한다. 배분 비율 자체는 고정값이다.
  → 선택된 배분안의 재무 결과(원리금/잔여현금/회수기간 등)만 비교해서 보여준다.

경계선 (변함없음):
  - "이 배분이 정답"이라고 추천하지 않는다. A/B/C는 서로 다른 해석 방식일 뿐,
    시나리오 간 우열은 매기지 않는다 (compare_scenarios_neutral 원칙 유지).
"""

from collections import defaultdict

CATEGORIES = ["marketing_online", "equipment_interior", "labor", "inventory"]

SEVERITY_WEIGHT = {"경미": 1, "뚜렷": 2, "심각": 3}

# 병목 유형 -> 대응 카테고리 매핑 (bottleneck_detector.py의 PRESCRIPTION_MAP과 동일한 매핑을
# 카테고리 코드로 변환해서 사용. 인건비 관련 병목은 의도적으로 '자동화(설비)'로 매핑되지,
# '인력 증원'으로 매핑되지 않는다 -> 인건비 부담을 늘리는 처방은 대응 방향에서 제외)
BOTTLENECK_TO_CATEGORY = {
    "time_of_day_weakness": "marketing_online",
    "low_repeat_rate": "marketing_online",
    "high_cost_ratio": "equipment_interior",
    "high_labor_ratio": "equipment_interior",
    "seat_capacity_shortage": "equipment_interior",
    "low_online_sales_share": "marketing_online",
    "high_platform_cost_rate": "equipment_interior",
    "high_online_cancel_refund_rate": "equipment_interior",
    "low_net_settlement_rate": "marketing_online",
}

MIN_CATEGORY_SHARE = 0.05  # 진단에서 안 나온 카테고리도 최소 이 비율은 배정 (0%는 부자연스러움)

# 병목 유형 -> 집행 후 확인해야 할 목표 사업지표 (스펙 10.4 targetMetrics)
BOTTLENECK_TO_TARGET_METRICS = {
    "time_of_day_weakness": ["EVENING_REVENUE", "ORDER_COUNT"],
    "high_cost_ratio": ["COGS_RATIO", "GROSS_MARGIN"],
    "high_labor_ratio": ["LABOR_COST_RATIO", "EMPLOYEE_COUNT"],
    "low_repeat_rate": ["REPEAT_CUSTOMER_RATE"],
    "seat_capacity_shortage": ["PEAK_HOUR_UTILIZATION", "AVG_WAIT_TIME"],
    "low_online_sales_share": ["ONLINE_SALES_SHARE"],
    "high_platform_cost_rate": ["PLATFORM_COST_RATE"],
    "high_online_cancel_refund_rate": ["ONLINE_CANCEL_REFUND_RATE"],
    "low_net_settlement_rate": ["NET_SETTLEMENT_RATE"],
}


def _severity_score_by_category(findings: list) -> dict:
    """병목들을 카테고리별로 묶어 심각도 점수 합산."""
    scores = defaultdict(float)
    for f in findings:
        cat = BOTTLENECK_TO_CATEGORY.get(f["bottleneck_type"])
        if cat:
            scores[cat] += SEVERITY_WEIGHT.get(f["severity"], 1)
    return scores


def _normalize(allocation: dict) -> dict:
    total = sum(allocation.values())
    if total == 0:
        # 병목이 하나도 없으면 균등 배분
        return {c: round(1 / len(CATEGORIES), 3) for c in CATEGORIES}
    return {c: round(v / total, 3) for c, v in allocation.items()}


def draft_concentrated(findings: list, min_shares: dict = None) -> dict:
    """A안: '병목 집중형' — 가장 심각한 병목 카테고리에 자금을 집중."""
    min_shares = min_shares or {c: MIN_CATEGORY_SHARE for c in CATEGORIES}
    scores = _severity_score_by_category(findings)
    if not scores:
        return _normalize({c: 1 for c in CATEGORIES})

    top_category = max(scores, key=scores.get)
    allocation = dict(min_shares)
    remaining = 1 - sum(min_shares.values())
    allocation[top_category] += remaining
    return _normalize(allocation)


def draft_balanced(findings: list, min_shares: dict = None) -> dict:
    """B안: '진단 비례 대응형' — 발견된 모든 병목의 심각도에 비례해서 배분."""
    min_shares = min_shares or {c: MIN_CATEGORY_SHARE for c in CATEGORIES}
    scores = _severity_score_by_category(findings)
    if not scores:
        return _normalize({c: 1 for c in CATEGORIES})

    allocation = dict(min_shares)
    remaining = 1 - sum(min_shares.values())
    score_total = sum(scores.values())
    for cat, score in scores.items():
        allocation[cat] += remaining * (score / score_total)
    return _normalize(allocation)


def draft_conservative_baseline(findings: list) -> dict:
    """C안: '균등 분산형' — 진단 결과와 무관하게 4개 카테고리에 고르게 배분 (비교 기준선)."""
    return _normalize({c: 1 for c in CATEGORIES})


def get_target_metrics_for_scenario(findings: list, allocation: dict) -> list:
    """
    이 배분안이 '의미있게(최소비중 이상)' 자금을 배정한 카테고리에 대응하는 병목들의
    확인지표를 모아서 반환한다. 최소비중(5%)만 형식적으로 받은 카테고리는 제외한다.
    """
    meaningfully_funded_categories = {cat for cat, pct in allocation.items() if pct > MIN_CATEGORY_SHARE}

    metrics = []
    for f in findings:
        category = BOTTLENECK_TO_CATEGORY.get(f["bottleneck_type"])
        if category in meaningfully_funded_categories:
            for m in BOTTLENECK_TO_TARGET_METRICS.get(f["bottleneck_type"], []):
                if m not in metrics:
                    metrics.append(m)

    return metrics


def generate_scenario_drafts(findings: list, min_shares: dict = None) -> list:
    """
    A/B/C 세 개의 배분 초안을 생성한다.
    min_shares가 주어지면(회차 히스토리에서 지속 병목이 발견된 경우), 해당 카테고리의
    최소 배정 비중이 5% -> 15%로 상향된 상태로 A/B안이 생성된다. (메커니즘 2: 지속 병목 가중치 상향)
    C안(균등 분산형)은 정의상 '진단과 무관한 기준선'이므로 상향을 적용하지 않는다.
    """
    scores = _severity_score_by_category(findings)
    top_category = max(scores, key=scores.get) if scores else None

    escalated_note = ""
    if min_shares:
        escalated_cats = [c for c, v in min_shares.items() if v > MIN_CATEGORY_SHARE]
        if escalated_cats:
            escalated_note = f" (참고: {', '.join(escalated_cats)}은(는) 병목이 지속되어 최소 배정 비중이 상향되었습니다.)"

    drafts = [
        {
            "scenario_id": "A",
            "label": "병목 집중형",
            "allocation": draft_concentrated(findings, min_shares),
            "rationale": (
                f"가장 심각도가 높은 병목({top_category})에 자금을 집중 배분한 초안입니다.{escalated_note}"
                if top_category else "발견된 병목이 없어 균등 배분을 기본값으로 제시합니다."
            ),
        },
        {
            "scenario_id": "B",
            "label": "진단 비례 대응형",
            "allocation": draft_balanced(findings, min_shares),
            "rationale": f"발견된 모든 병목의 심각도에 비례해서 자금을 나눠 배분한 초안입니다.{escalated_note}",
        },
        {
            "scenario_id": "C",
            "label": "균등 분산형 (기준선)",
            "allocation": draft_conservative_baseline(findings),
            "rationale": "진단 결과와 무관하게 4개 항목에 고르게 배분한 비교 기준선입니다.",
        },
    ]

    for d in drafts:
        d["is_editable"] = False
        d["note"] = "이 배분은 병목 진단 결과에 기반한 고정 제안값입니다. A/B/C 중 하나를 선택해 결과를 확인하세요."
        d["target_metrics"] = get_target_metrics_for_scenario(findings, d["allocation"])

    return drafts


# ─────────────────────────────────────────────
# 실행 (테스트)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data
    from bottleneck_detector import compute_time_of_day_benchmark, detect_bottlenecks

    time_benchmark = compute_time_of_day_benchmark()

    for scenario in ["normal", "evening_weak", "high_cost_ratio", "seat_shortage"]:
        print(f"\n{'='*60}")
        print(f"사용자 상황: {scenario}")
        print("=" * 60)

        user_data = generate_mock_pos_data(scenario=scenario)
        findings = detect_bottlenecks(user_data, time_benchmark)

        if findings:
            print("발견된 병목:", [f"{f['bottleneck_type']}({f['severity']})" for f in findings])
        else:
            print("발견된 병목 없음")

        drafts = generate_scenario_drafts(findings)
        for d in drafts:
            pct_str = ", ".join(f"{k}:{v*100:.0f}%" for k, v in d["allocation"].items())
            print(f"\n[{d['scenario_id']}안 - {d['label']}]")
            print(f"  배분: {pct_str}")
            print(f"  근거: {d['rationale']}")