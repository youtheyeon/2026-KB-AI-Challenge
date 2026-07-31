"""
병목 진단 (Bottleneck Detector)

목적: 사용자(mock POS)의 현재 상태를, 실제 데이터 기반 벤치마크 / 업계 가정치와 비교해서
     "어디가 병목인지"를 진단한다. 매출이 얼마나 오를지는 예측하지 않는다.
     대신 "이 병목엔 이런 유형의 자금 사용이 대응된다"는 방향성만 제시한다.

입력: mock_pos_data.py가 만든 사용자 데이터
참고 벤치마크:
  - 시간대별 매출 비중: raw_data의 실제 서울시 카페 매출 데이터에서 계산 (진짜 데이터 기반)
  - 원가율/인건비율/재구매율: 명시적 업계 가정치 (실증 데이터 없음, 출처 표기)
"""

import json
import os
from collections import defaultdict

RAW_CAFE_DATA_CANDIDATES = [
    "./raw_data/seoul_cafe_sales_full.json",
    "./raw_data/seoul_cafe_sales.json",
]

TIME_BUCKETS = ["00_06", "06_11", "11_14", "14_17", "17_21", "21_24"]


# ─────────────────────────────────────────────
# 1) 시간대별 벤치마크 — 실제 데이터로 계산 (가정 아님)
# ─────────────────────────────────────────────
def compute_time_of_day_benchmark() -> dict:
    benchmark, _ = compute_time_of_day_benchmark_with_sample_size()
    return benchmark


def compute_time_of_day_benchmark_with_sample_size() -> tuple:
    """벤치마크 비중과 함께, 몇 건의 실제 데이터로 계산했는지(표본 수)도 반환한다."""
    raw_path = next((p for p in RAW_CAFE_DATA_CANDIDATES if os.path.exists(p)), None)
    if not raw_path:
        raise FileNotFoundError("카페 매출 원본 데이터가 없습니다. fetch_benchmark_data.py를 먼저 실행하세요.")

    with open(raw_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    bucket_totals = defaultdict(float)
    revenue_total = 0.0
    for row in rows:
        for b in TIME_BUCKETS:
            bucket_totals[b] += row.get(f"TMZON_{b}_SELNG_AMT", 0)
        revenue_total += row.get("THSMON_SELNG_AMT", 0)

    if revenue_total == 0:
        raise ValueError("매출 합계가 0입니다. 데이터 확인 필요.")

    benchmark = {b: round(bucket_totals[b] / revenue_total, 4) for b in TIME_BUCKETS}
    return benchmark, len(rows)


# ─────────────────────────────────────────────
# 2) 업계 가정치 (실증 데이터 없음 — 출처를 명시하고 '가정'이라고 라벨링)
# ─────────────────────────────────────────────
INDUSTRY_ASSUMPTIONS = {
    # 소상공인실태조사(2023) 기반: 매출 대비 영업이익률 12.6% -> 총비용률 87.4%를
    # 원가/인건비/기타로 임의 분해한 가정치 (실제 항목별 분해 통계는 없음 -> 가정)
    "cogs_ratio_benchmark": 0.42,
    "labor_ratio_benchmark": 0.20,
    # 재구매율/좌석점유율 벤치마크는 공개된 업종 통계가 없어 업계 통상 추정치를 가정으로 사용
    "repeat_customer_rate_benchmark": 0.35,
    "peak_utilization_warning_threshold": 0.90,
    "wait_time_warning_minutes": 10,
}

# 병목 유형별 3단계 판정 기준: (trigger=병목 판정 최소격차, severe=뚜렷, critical=심각)
# 시간대는 '벤치마크 대비 상대 비율', 나머지는 '%p 절대 격차', 대기시간은 '분' 단위
SEVERITY_THRESHOLDS = {
    "time_of_day_weakness": {"trigger": 0.15, "severe": 0.35, "critical": 0.60},  # 상대 비율
    "high_cost_ratio": {"trigger": 0.05, "severe": 0.10, "critical": 0.15},        # %p
    "high_labor_ratio": {"trigger": 0.05, "severe": 0.10, "critical": 0.15},       # %p
    "low_repeat_rate": {"trigger": 0.10, "severe": 0.15, "critical": 0.22},        # %p
    "seat_capacity_shortage": {"trigger": 10, "severe": 15, "critical": 20},       # 분(대기시간 기준)
    # 온라인 채널 병목 (온라인 자료가 있을 때만 진단됨)
    "low_online_sales_share": {"trigger": 0.05, "severe": 0.10, "critical": 0.15},        # %p (업계 참고 비중 대비)
    "high_platform_cost_rate": {"trigger": 0.05, "severe": 0.10, "critical": 0.15},       # %p
    "high_online_cancel_refund_rate": {"trigger": 0.05, "severe": 0.08, "critical": 0.12},# %p
    "low_net_settlement_rate": {"trigger": 0.05, "severe": 0.10, "critical": 0.15},       # %p
}

# 온라인 채널 관련 업계 참고치 (실증 데이터 아님, 가정치)
ONLINE_INDUSTRY_ASSUMPTIONS = {
    "online_sales_share_benchmark": 0.20,       # 업계 참고 온라인 판매 비중
    "platform_cost_rate_benchmark": 0.15,       # 업계 참고 플랫폼 비용률
    "online_cancel_refund_rate_benchmark": 0.05,# 업계 참고 취소·환불률
    "net_settlement_rate_benchmark": 0.92,      # 업계 참고 순정산율
}

# 병목 유형별로 "무엇과 비교했고, 어떤 기준으로 심각도를 나눴는지"를 문장으로 명시.
# LLM 설명 생성 시 이 문구를 그대로 인용해서, 판정 근거를 얼버무리지 않고 명확히 말하게 한다.
METHODOLOGY_TEMPLATE = {
    "time_of_day_weakness": (
        "서울시 상권분석서비스에서 수집한 카페(커피-음료) 업종 매출 데이터 {sample_size}건의 "
        "시간대별 평균 매출 비중과 비교했습니다. 벤치마크 대비 상대적으로 15% 이상 낮으면 병목으로 판정하며, "
        "35% 이상 낮으면 '뚜렷', 60% 이상 낮으면 '심각'으로 분류합니다."
    ),
    "high_cost_ratio": (
        "업계 참고 원가율(매출 대비 {benchmark_pct}%)과 비교했습니다. "
        "이 참고치는 실제 카페 업종 원가 데이터가 아니라 일반 업종 가정치이며, "
        "격차가 5%p 이상이면 병목, 10%p 이상 '뚜렷', 15%p 이상 '심각'으로 분류합니다."
    ),
    "high_labor_ratio": (
        "업계 참고 인건비 비중(매출 대비 {benchmark_pct}%)과 비교했습니다. "
        "이 참고치는 실제 카페 업종 데이터가 아니라 일반 업종 가정치이며, "
        "격차가 5%p 이상이면 병목, 10%p 이상 '뚜렷', 15%p 이상 '심각'으로 분류합니다."
    ),
    "low_repeat_rate": (
        "업계 참고 재구매율({benchmark_pct}%)과 비교했습니다. "
        "이 참고치는 실증 데이터가 아니라 업계 통상 추정치이며, "
        "격차가 10%p 이상이면 병목, 15%p 이상 '뚜렷', 22%p 이상 '심각'으로 분류합니다."
    ),
    "seat_capacity_shortage": (
        "사용자의 피크타임 좌석점유율과 평균 대기시간을 직접 확인했습니다. "
        "점유율 90% 이상이면서 대기시간이 10분 이상이면 병목, 15분 이상 '뚜렷', 20분 이상 '심각'으로 분류합니다."
    ),
}


def classify_severity_3tier(value: float, bottleneck_type: str) -> str:
    """공통 3단계 심각도 판정: 경미 < 뚜렷 < 심각. value는 '벤치마크와의 격차 크기'."""
    t = SEVERITY_THRESHOLDS[bottleneck_type]
    if value >= t["critical"]:
        return "심각"
    elif value >= t["severe"]:
        return "뚜렷"
    elif value >= t["trigger"]:
        return "경미"
    return None  # 병목 아님


# ─────────────────────────────────────────────
# 3) 병목 -> 처방 유형 매핑 (숫자 예측 아님, 방향성 매칭)
# ─────────────────────────────────────────────
PRESCRIPTION_MAP = {
    "time_of_day_weakness": {
        "category": "마케팅·온라인채널",
        "rationale": "특정 시간대 고객 유입이 부족하면, 그 시간대를 타깃으로 한 프로모션이나 배달앱 노출 확대가 대응 방향으로 알려져 있습니다.",
    },
    "high_cost_ratio": {
        "category": "설비·재고관리",
        "rationale": "원가율이 높으면 식자재 폐기 감소, 조리효율 개선(설비 교체) 등이 대응 방향으로 알려져 있습니다.",
    },
    "high_labor_ratio": {
        "category": "설비·자동화",
        "rationale": "인건비 비중이 높으면 추가 채용보다 자동화(키오스크, 조리설비 등)로 효율을 높이는 방향이 우선 검토 대상입니다.",
    },
    "low_repeat_rate": {
        "category": "마케팅·온라인채널",
        "rationale": "재구매율이 낮으면 멤버십/적립 프로그램, SNS 재방문 유도 등이 대응 방향으로 알려져 있습니다.",
    },
    "seat_capacity_shortage": {
        "category": "설비·인테리어",
        "rationale": "피크타임 좌석 점유율이 높고 대기시간이 길면, 좌석 확충이나 회전율 개선 설비가 대응 방향으로 알려져 있습니다.",
    },
    "low_online_sales_share": {
        "category": "마케팅·온라인채널",
        "rationale": "온라인 판매 비중이 낮으면, 배달앱·자사몰 등 온라인 채널 확장이 대응 방향으로 알려져 있습니다.",
    },
    "high_platform_cost_rate": {
        "category": "설비·재고관리",
        "rationale": "플랫폼 비용률이 높으면, 채널 재조정이나 자체 주문 채널 구축이 대응 방향으로 알려져 있습니다.",
    },
    "high_online_cancel_refund_rate": {
        "category": "설비·재고관리",
        "rationale": "온라인 취소·환불률이 높으면, 재고·조리 프로세스 점검이 대응 방향으로 알려져 있습니다.",
    },
    "low_net_settlement_rate": {
        "category": "마케팅·온라인채널",
        "rationale": "순정산율이 낮으면, 수수료 구조가 더 유리한 채널로의 비중 조정이 대응 방향으로 알려져 있습니다.",
    },
}

# ── UI 카드 표시용 (이미지2 형태): 제목 / 우선순위 배지 / 신뢰도 배지 ──
DISPLAY_TITLE = {
    "time_of_day_weakness": "특정 시간대 고객 유입 부족",
    "high_cost_ratio": "원가율 상승",
    "high_labor_ratio": "인건비 부담 상승",
    "low_repeat_rate": "재구매율 저조",
    "seat_capacity_shortage": "처리 용량 한계",
    "low_online_sales_share": "낮은 온라인 판매 비중",
    "high_platform_cost_rate": "높은 플랫폼 비용률",
    "high_online_cancel_refund_rate": "높은 온라인 취소·환불률",
    "low_net_settlement_rate": "낮은 순정산율",
}

# 심각도 -> 화면에 노출할 '우선순위' 배지
SEVERITY_TO_PRIORITY_BADGE = {
    "심각": "우선 확인",
    "뚜렷": "확인 필요",
    "경미": "참고",
}

# 근거 종류 -> 화면에 노출할 '신뢰도' 배지
# 실제 데이터 > 업계 가정치 > mock(실제 POS 연동 전) 순으로 신뢰도를 다르게 표시한다.
EVIDENCE_TO_CONFIDENCE_BADGE = {
    "실제 서울시 카페 매출 데이터 기반 벤치마크": "높음",
    "업계 가정치 (실증 데이터 없음)": "보통",
    "사용자 POS 데이터": "낮음",  # 지금은 mock 데이터라 낮음으로 표시, 실제 연동 후 상향 가능
    "AI 비지도학습(K-means)으로 분류된 유사 소비패턴 상권군 평균": "높음",
    "업계 가정치 (온라인 채널, 실증 데이터 없음)": "보통",
    "사용자 온라인 판매·정산 자료 (선택 업로드)": "높음",
}

BOTTLENECK_DISCLAIMER = "병목 후보는 분석 후보이며 확정이 아닙니다. 현장 상황과 다를 수 있으며 사용자가 판단을 수정할 수 있습니다."


# ─────────────────────────────────────────────
# 4) 진단 본체
# ─────────────────────────────────────────────
def detect_bottlenecks(
    user_data: dict,
    time_benchmark: dict,
    assumptions: dict = INDUSTRY_ASSUMPTIONS,
    time_benchmark_sample_size: int = None,
    personal_baselines: dict = None,
    comparable_bottleneck_types: set[str] = None,
) -> list:
    """
    personal_baselines가 주어지면(회차가 충분히 쌓인 경우), 원가율/인건비율/재구매율
    비교 기준을 업계 가정치 대신 '이 사업자의 과거 실측 평균'으로 교체한다.
    이 경우 evidence_source/confidence_badge도 '실측 기반, 신뢰도 높음'으로 바뀐다.
    """
    findings = []

    def can_compare(bottleneck_type: str) -> bool:
        return (
            comparable_bottleneck_types is None
            or bottleneck_type in comparable_bottleneck_types
        )

    # personal_baselines가 있으면 해당 항목만 값 교체 (없는 항목은 업계 가정치 유지)
    effective_assumptions = dict(assumptions)
    using_personal = {}
    if personal_baselines:
        for key in ("cogs_ratio_benchmark", "labor_ratio_benchmark", "repeat_customer_rate_benchmark"):
            if key in personal_baselines:
                effective_assumptions[key] = personal_baselines[key]
                using_personal[key] = True
    assumptions = effective_assumptions

    def _evidence_and_confidence(assumption_key: str, base_evidence: str) -> tuple:
        if using_personal.get(assumption_key):
            n = personal_baselines["based_on_rounds"]
            return (f"본인 과거 실측 평균 ({n}회차 누적)", "높음")
        return (base_evidence, None)  # None이면 호출부에서 기존 EVIDENCE_TO_CONFIDENCE_BADGE로 결정

    # (1) 시간대별 병목 -- 실제 데이터 벤치마크 사용 (상대 격차 기준)
    user_revenue = user_data["monthly_revenue"]
    if can_compare("time_of_day_weakness"):
        for b in TIME_BUCKETS:
            user_amt = user_data["time_of_day_sales"].get(f"TMZON_{b}_SELNG_AMT", 0)
            user_share = user_amt / user_revenue if user_revenue else 0
            bench_share = time_benchmark.get(b, 0)
            if bench_share <= 0.05:
                continue  # 원래 비중이 작은 시간대(예: 새벽)는 격차가 커도 의미 없음 -> 제외
            relative_gap = (bench_share - user_share) / bench_share
            severity = classify_severity_3tier(relative_gap, "time_of_day_weakness")
            if severity:
                n_text = f"{time_benchmark_sample_size:,}" if time_benchmark_sample_size else "다수"
                findings.append({
                    "bottleneck_type": "time_of_day_weakness",
                    "title": f"{b.replace('_', '~')}시 고객 유입 부족",
                    "detail": f"{b.replace('_', '~')}시 매출 비중이 {user_share*100:.1f}% (벤치마크 {bench_share*100:.1f}%)로 낮음",
                    "comparison_chip": f"{b.replace('_', '~')}시 매출비중 {user_share*100:.1f}% · 벤치마크 {bench_share*100:.1f}%",
                    "evidence_source": "실제 서울시 카페 매출 데이터 기반 벤치마크",
                    "methodology": METHODOLOGY_TEMPLATE["time_of_day_weakness"].format(sample_size=n_text),
                    "severity": severity,
                })

    # (2) 원가율 -- 가정치 또는 개인 기준선 사용 (%p 절대 격차 기준)
    if can_compare("high_cost_ratio"):
        cogs_ratio = user_data["monthly_cogs"] / user_revenue if user_revenue else 0
        cogs_gap = cogs_ratio - assumptions["cogs_ratio_benchmark"]
        severity = classify_severity_3tier(cogs_gap, "high_cost_ratio")
    else:
        severity = None
    if severity:
        cogs_evidence, cogs_confidence_override = _evidence_and_confidence(
            "cogs_ratio_benchmark", "업계 가정치 (실증 데이터 없음)"
        )
        benchmark_label = "본인 과거 평균" if using_personal.get("cogs_ratio_benchmark") else "업계 참고치"
        finding = {
            "bottleneck_type": "high_cost_ratio",
            "detail": f"원가율 {cogs_ratio*100:.1f}% ({benchmark_label} {assumptions['cogs_ratio_benchmark']*100:.1f}%)로 높음",
            "comparison_chip": f"원가율 {cogs_ratio*100:.1f}% · {benchmark_label} {assumptions['cogs_ratio_benchmark']*100:.1f}%",
            "evidence_source": cogs_evidence,
            "methodology": METHODOLOGY_TEMPLATE["high_cost_ratio"].format(
                benchmark_pct=round(assumptions["cogs_ratio_benchmark"] * 100, 1)
            ),
            "severity": severity,
        }
        if cogs_confidence_override:
            finding["_confidence_override"] = cogs_confidence_override
        findings.append(finding)

    # (3) 인건비 비중 -- 가정치 또는 개인 기준선 사용
    if can_compare("high_labor_ratio"):
        labor_ratio = user_data["monthly_labor_cost"] / user_revenue if user_revenue else 0
        labor_gap = labor_ratio - assumptions["labor_ratio_benchmark"]
        severity = classify_severity_3tier(labor_gap, "high_labor_ratio")
    else:
        severity = None
    if severity:
        labor_evidence, labor_confidence_override = _evidence_and_confidence(
            "labor_ratio_benchmark", "업계 가정치 (실증 데이터 없음)"
        )
        benchmark_label = "본인 과거 평균" if using_personal.get("labor_ratio_benchmark") else "업계 참고치"
        finding = {
            "bottleneck_type": "high_labor_ratio",
            "detail": f"인건비 비중 {labor_ratio*100:.1f}% ({benchmark_label} {assumptions['labor_ratio_benchmark']*100:.1f}%)로 높음",
            "comparison_chip": f"인건비 비중 {labor_ratio*100:.1f}% · {benchmark_label} {assumptions['labor_ratio_benchmark']*100:.1f}%",
            "evidence_source": labor_evidence,
            "methodology": METHODOLOGY_TEMPLATE["high_labor_ratio"].format(
                benchmark_pct=round(assumptions["labor_ratio_benchmark"] * 100, 1)
            ),
            "severity": severity,
        }
        if labor_confidence_override:
            finding["_confidence_override"] = labor_confidence_override
        findings.append(finding)

    # (4) 재구매율 -- 가정치 또는 개인 기준선 사용
    if can_compare("low_repeat_rate"):
        repeat_rate = user_data["repeat_customer_rate"]
        repeat_gap = assumptions["repeat_customer_rate_benchmark"] - repeat_rate
        severity = classify_severity_3tier(repeat_gap, "low_repeat_rate")
    else:
        severity = None
    if severity:
        repeat_evidence, repeat_confidence_override = _evidence_and_confidence(
            "repeat_customer_rate_benchmark", "업계 가정치 (실증 데이터 없음)"
        )
        benchmark_label = "본인 과거 평균" if using_personal.get("repeat_customer_rate_benchmark") else "업계 참고치"
        finding = {
            "bottleneck_type": "low_repeat_rate",
            "detail": f"재구매율 {repeat_rate*100:.1f}% ({benchmark_label} {assumptions['repeat_customer_rate_benchmark']*100:.1f}%)로 낮음",
            "comparison_chip": f"재구매율 {repeat_rate*100:.1f}% · {benchmark_label} {assumptions['repeat_customer_rate_benchmark']*100:.1f}%",
            "evidence_source": repeat_evidence,
            "methodology": METHODOLOGY_TEMPLATE["low_repeat_rate"].format(
                benchmark_pct=round(assumptions["repeat_customer_rate_benchmark"] * 100, 1)
            ),
            "severity": severity,
        }
        if repeat_confidence_override:
            finding["_confidence_override"] = repeat_confidence_override
        findings.append(finding)

    # (5) 좌석/처리용량 -- 사용자 자체 데이터 (mock), 대기시간(분) 기준으로 3단계 판정
    if can_compare("seat_capacity_shortage"):
        peak_util = user_data["peak_hour_utilization_rate"]
        wait_time = user_data["avg_wait_time_minutes"]
    else:
        peak_util = None
        wait_time = None
    if peak_util is not None and peak_util >= assumptions["peak_utilization_warning_threshold"]:
        severity = classify_severity_3tier(wait_time, "seat_capacity_shortage")
        if severity:
            findings.append({
                "bottleneck_type": "seat_capacity_shortage",
                "detail": f"피크타임 좌석점유율 {peak_util*100:.0f}%, 평균 대기시간 {wait_time}분으로 처리용량 부족 의심",
                "comparison_chip": f"평균 대기시간 {wait_time}분 · 좌석점유율 {peak_util*100:.0f}%",
                "evidence_source": "사용자 POS 데이터",
                "methodology": METHODOLOGY_TEMPLATE["seat_capacity_shortage"],
                "severity": severity,
            })

    # (6) 온라인 채널 병목 4종 -- 온라인 자료(선택 업로드)가 있을 때만 진단.
    #     스펙 원칙: "온라인 매출 비중이 낮다는 사실만으로 병목을 확정하지 않는다" ->
    #     여기서는 최소 구현으로 비율 기반 판정만 두되, 실제 적용 시 storeType 등 문맥 고려 필요.
    online = user_data.get("online_data")
    if online:
        online_assump = ONLINE_INDUSTRY_ASSUMPTIONS
        gross = online["online_gross_order_amount"]
        revenue = user_data["monthly_revenue"]

        # 6-1. 낮은 온라인 판매 비중
        if can_compare("low_online_sales_share"):
            online_share = gross / revenue if revenue else 0
            gap = online_assump["online_sales_share_benchmark"] - online_share
            severity = classify_severity_3tier(gap, "low_online_sales_share")
        else:
            severity = None
        if severity:
            findings.append({
                "bottleneck_type": "low_online_sales_share",
                "detail": f"온라인 판매 비중 {online_share*100:.1f}% (업계 참고치 {online_assump['online_sales_share_benchmark']*100:.1f}%)로 낮음",
                "comparison_chip": f"온라인 비중 {online_share*100:.1f}% · 업계 참고치 {online_assump['online_sales_share_benchmark']*100:.1f}%",
                "evidence_source": "업계 가정치 (온라인 채널, 실증 데이터 없음)",
                "methodology": "업계 참고 온라인 판매 비중과 비교했습니다. 이 참고치는 실증 데이터가 아니라 가정치이며, 격차가 5%p 이상이면 병목으로 판정합니다.",
                "severity": severity,
            })

        # 6-2. 높은 플랫폼 비용률
        if can_compare("high_platform_cost_rate"):
            platform_cost = online["online_platform_fee"] + online["online_payment_fee"] + online["online_merchant_delivery_fee"]
            platform_cost_rate = platform_cost / gross if gross else 0
            gap = platform_cost_rate - online_assump["platform_cost_rate_benchmark"]
            severity = classify_severity_3tier(gap, "high_platform_cost_rate")
        else:
            severity = None
        if severity:
            findings.append({
                "bottleneck_type": "high_platform_cost_rate",
                "detail": f"플랫폼 비용률 {platform_cost_rate*100:.1f}% (업계 참고치 {online_assump['platform_cost_rate_benchmark']*100:.1f}%)로 높음",
                "comparison_chip": f"플랫폼 비용률 {platform_cost_rate*100:.1f}% · 업계 참고치 {online_assump['platform_cost_rate_benchmark']*100:.1f}%",
                "evidence_source": "사용자 온라인 판매·정산 자료 (선택 업로드)",
                "methodology": "사용자가 업로드한 온라인 판매·정산 자료의 플랫폼수수료·결제수수료·배달비 합계를 총주문금액으로 나눈 값을 업계 참고치와 비교했습니다.",
                "severity": severity,
            })

        # 6-3. 높은 온라인 취소·환불률
        if can_compare("high_online_cancel_refund_rate"):
            cancel_rate = online["online_cancel_refund_amount"] / gross if gross else 0
            gap = cancel_rate - online_assump["online_cancel_refund_rate_benchmark"]
            severity = classify_severity_3tier(gap, "high_online_cancel_refund_rate")
        else:
            severity = None
        if severity:
            findings.append({
                "bottleneck_type": "high_online_cancel_refund_rate",
                "detail": f"온라인 취소·환불률 {cancel_rate*100:.1f}% (업계 참고치 {online_assump['online_cancel_refund_rate_benchmark']*100:.1f}%)로 높음",
                "comparison_chip": f"취소·환불률 {cancel_rate*100:.1f}% · 업계 참고치 {online_assump['online_cancel_refund_rate_benchmark']*100:.1f}%",
                "evidence_source": "사용자 온라인 판매·정산 자료 (선택 업로드)",
                "methodology": "사용자가 업로드한 온라인 판매·정산 자료의 취소환불금액을 총주문금액으로 나눈 값을 업계 참고치와 비교했습니다.",
                "severity": severity,
            })

        # 6-4. 낮은 순정산율
        if can_compare("low_net_settlement_rate"):
            settlement_rate = online["online_settlement_amount"] / gross if gross else 0
            gap = online_assump["net_settlement_rate_benchmark"] - settlement_rate
            severity = classify_severity_3tier(gap, "low_net_settlement_rate")
        else:
            severity = None
        if severity:
            findings.append({
                "bottleneck_type": "low_net_settlement_rate",
                "detail": f"순정산율 {settlement_rate*100:.1f}% (업계 참고치 {online_assump['net_settlement_rate_benchmark']*100:.1f}%)로 낮음",
                "comparison_chip": f"순정산율 {settlement_rate*100:.1f}% · 업계 참고치 {online_assump['net_settlement_rate_benchmark']*100:.1f}%",
                "evidence_source": "사용자 온라인 판매·정산 자료 (선택 업로드)",
                "methodology": "사용자가 업로드한 온라인 판매·정산 자료의 정산금액을 총주문금액으로 나눈 값을 업계 참고치와 비교했습니다.",
                "severity": severity,
            })

    # 처방 매핑 + UI 카드용 필드 추가
    for finding in findings:
        prescription = PRESCRIPTION_MAP.get(finding["bottleneck_type"], {})
        finding["suggested_category"] = prescription.get("category")
        finding["rationale"] = prescription.get("rationale")
        finding["title"] = finding.get("title") or DISPLAY_TITLE.get(finding["bottleneck_type"], finding["bottleneck_type"])
        finding["priority_badge"] = SEVERITY_TO_PRIORITY_BADGE.get(finding["severity"])
        finding["confidence_badge"] = finding.pop("_confidence_override", None) or EVIDENCE_TO_CONFIDENCE_BADGE.get(finding["evidence_source"], "보통")

    return findings


def detect_bottlenecks_with_ai_clustering(
    pos_data: dict, assumptions: dict = INDUSTRY_ASSUMPTIONS, personal_baselines: dict = None
) -> tuple:
    """
    기존 detect_bottlenecks()는 '전체 카페 평균'과 비교했다.
    이 함수는 그 대신, cluster_benchmark.py의 K-means 결과를 이용해
    '이 사용자와 소비패턴이 가장 비슷한 상권 그룹의 평균'과 비교한다.

    personal_baselines가 주어지면 원가율/인건비율/재구매율은 개인 실측 평균으로 대체된다.

    반환: (findings, cluster_info) -- cluster_info는 어느 클러스터로 배정됐는지 등 메타데이터
    """
    from cluster_benchmark import assign_user_cluster

    cluster_result = assign_user_cluster(pos_data)
    time_benchmark = cluster_result["time_of_day_benchmark"]

    findings = detect_bottlenecks(
        pos_data, time_benchmark, assumptions,
        time_benchmark_sample_size=cluster_result["cluster_member_count"],
        personal_baselines=personal_baselines,
    )

    # 시간대 병목의 근거 문구를 '전체 평균'이 아니라 '클러스터링 결과' 기준으로 교체
    example_areas = ", ".join(cluster_result["cluster_example_trade_areas"][:3])
    for f in findings:
        if f["bottleneck_type"] == "time_of_day_weakness":
            f["evidence_source"] = "AI 비지도학습(K-means)으로 분류된 유사 소비패턴 상권군 평균"
            f["methodology"] = (
                f"시간대별·요일별 매출 패턴을 기준으로 K-means 클러스터링을 실행해 서울시 카페 상권을 "
                f"자동으로 그룹화했습니다. 이 사용자는 '{cluster_result['cluster_dominant_time']}시·"
                f"{cluster_result['cluster_dominant_weekday']}요일 강세' 특징을 가진 그룹"
                f"(상권 {cluster_result['cluster_member_count']}개, 예: {example_areas})으로 분류되었으며, "
                f"이 그룹 내 평균 시간대 비중과 비교했습니다. 격차가 15% 이상이면 병목, 35% 이상 '뚜렷', "
                f"60% 이상 '심각'으로 분류합니다."
            )

    return findings, cluster_result


# ─────────────────────────────────────────────
# 실행 (테스트)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from mock_pos_data import generate_mock_pos_data

    print("실제 데이터 기반 시간대 벤치마크 계산 중...")
    time_benchmark, sample_size = compute_time_of_day_benchmark_with_sample_size()
    print(f"표본 수: {sample_size}건")
    print("시간대별 벤치마크 비중:", {k: f"{v*100:.1f}%" for k, v in time_benchmark.items()})

    for scenario in ["normal", "evening_weak", "high_cost_ratio", "low_repeat", "seat_shortage"]:
        print(f"\n{'='*60}")
        print(f"시나리오: {scenario}")
        print("=" * 60)

        user_data = generate_mock_pos_data(scenario=scenario)
        findings = detect_bottlenecks(user_data, time_benchmark, time_benchmark_sample_size=sample_size)

        if not findings:
            print("발견된 병목 없음 (정상 범위)")
        for f in findings:
            print(f"\n[{f['title']}] 우선순위: {f['priority_badge']} / 신뢰도: {f['confidence_badge']}")
            print(f"  {f['detail']}")
            print(f"  비교칩: {f['comparison_chip']}")
            print(f"  근거: {f['evidence_source']}")
            print(f"  판정방법(근거보기): {f['methodology']}")
            print(f"  대응 방향: {f['suggested_category']} — {f['rationale']}")
    print(f"\n※ {BOTTLENECK_DISCLAIMER}")
