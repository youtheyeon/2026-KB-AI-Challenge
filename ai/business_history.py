"""
business_history.py — 회차가 쌓일수록 "업계 평균 → 본인 과거 실측치"로 전환되는 선순환 메커니즘

세 가지 메커니즘을 전부 결정론적 계산(평균/카운트)으로 구현한다. ML 아님, 명시적 규칙임.

  1) 개인 기준선 치환 (Self-Baseline Substitution)
     회차가 min_rounds 이상 쌓이면, 원가율/인건비율/재구매율 벤치마크를
     업계 가정치 대신 "이 사업자의 과거 회차 실측 평균"으로 교체한다.

  2) 지속 병목 가중치 상향 (Persistent Bottleneck Escalation)
     같은 병목이 최근 N회 연속 나타나면, 다음 배분안 생성 시 그 병목에
     대응하는 카테고리의 최소 배정 비중을 규칙적으로 상향한다.

  3) 부작용(trade-off) 이력 추적 (Side-effect Tracking)
     "회차 N에 카테고리 X에 유의미하게 배분 -> 회차 N+1에 병목 Y가 새로 발생"
     페어를 기록해두고, 다음에 카테고리 X를 다시 추천할 때 경고로 재사용한다.

history 구조 (백엔드가 회차마다 이 형태로 쌓아서 넘겨준다고 가정):
[
  {
    "round": 1,
    "findings": [...],              # 그 회차의 detect_bottlenecks() 결과
    "pos_data": {...},               # 그 회차에 실제로 관측된 사업 데이터
    "selected_allocation": {...},    # 그 회차에 사용자가 선택한 배분 비율
  },
  ...
]
"""

MIN_ROUNDS_FOR_PERSONAL_BASELINE = 3  # 이 회차 수 이상 쌓여야 개인 기준선으로 전환
PERSISTENCE_THRESHOLD = 2             # 이 횟수 이상 연속 발생하면 '지속 병목'으로 간주
BASE_MIN_CATEGORY_SHARE = 0.05
ESCALATED_MIN_CATEGORY_SHARE = 0.15   # 지속 병목 카테고리의 상향된 최소 비중


def compute_personal_baselines(history: list) -> dict:
    """
    회차가 충분히 쌓였으면(기본 3회 이상), 원가율/인건비율/재구매율을
    업계 가정치 대신 이 사업자의 과거 실측 평균으로 계산해서 반환한다.
    회차가 부족하면 None을 반환하고, 호출부는 계속 업계 가정치를 쓴다.
    """
    if len(history) < MIN_ROUNDS_FOR_PERSONAL_BASELINE:
        return None

    cogs_ratios, labor_ratios, repeat_rates = [], [], []
    for record in history:
        pos = record["pos_data"]
        revenue = pos.get("monthly_revenue", 0)
        if not revenue:
            continue
        cogs_ratios.append(pos["monthly_cogs"] / revenue)
        labor_ratios.append(pos["monthly_labor_cost"] / revenue)
        repeat_rates.append(pos["repeat_customer_rate"])

    if not cogs_ratios:
        return None

    return {
        "cogs_ratio_benchmark": sum(cogs_ratios) / len(cogs_ratios),
        "labor_ratio_benchmark": sum(labor_ratios) / len(labor_ratios),
        "repeat_customer_rate_benchmark": sum(repeat_rates) / len(repeat_rates),
        "based_on_rounds": len(history),
    }


def compute_persistence_counts(history: list) -> dict:
    """
    각 병목 유형이 '가장 최근 회차부터 거슬러 올라가며' 몇 회 연속 나타났는지 계산.
    최근 회차에 없으면 0 (연속이 끊긴 것이므로).
    """
    if not history:
        return {}

    counts = {}
    all_types_ever = {f["bottleneck_type"] for record in history for f in record["findings"]}

    for btype in all_types_ever:
        streak = 0
        for record in reversed(history):  # 최근 회차부터
            round_types = {f["bottleneck_type"] for f in record["findings"]}
            if btype in round_types:
                streak += 1
            else:
                break
        counts[btype] = streak

    return counts


def compute_escalated_min_shares(persistence_counts: dict, bottleneck_to_category: dict, categories: list) -> dict:
    """
    지속 병목(연속 threshold회 이상)에 대응하는 카테고리는 최소 배정 비중을 상향한다.
    나머지 카테고리는 기본 최소 비중(5%) 그대로.
    """
    escalated_categories = set()
    for btype, streak in persistence_counts.items():
        if streak >= PERSISTENCE_THRESHOLD:
            cat = bottleneck_to_category.get(btype)
            if cat:
                escalated_categories.add(cat)

    return {
        cat: (ESCALATED_MIN_CATEGORY_SHARE if cat in escalated_categories else BASE_MIN_CATEGORY_SHARE)
        for cat in categories
    }


def compute_tradeoff_warnings(history: list, bottleneck_to_category: dict) -> list:
    """
    회차 N의 배분(카테고리 X에 유의미하게 배정) 이후, 회차 N+1에 새로 나타난 병목 Y를
    "X에 배분했더니 Y가 발생한 이력"으로 기록해서 반환한다.
    """
    warnings = []
    for i in range(len(history) - 1):
        prev_record = history[i]
        next_record = history[i + 1]

        prev_types = {f["bottleneck_type"] for f in prev_record["findings"]}
        next_types = {f["bottleneck_type"] for f in next_record["findings"]}
        newly_emerged = next_types - prev_types

        prev_allocation = prev_record.get("selected_allocation", {})
        funded_categories = {cat for cat, pct in prev_allocation.items() if pct > BASE_MIN_CATEGORY_SHARE}

        for new_type in newly_emerged:
            related_category = bottleneck_to_category.get(new_type)
            if related_category in funded_categories:
                warnings.append({
                    "category": related_category,
                    "resulting_bottleneck": new_type,
                    "occurred_after_round": prev_record["round"],
                })

    return warnings


# ─────────────────────────────────────────────
# 실행 (테스트) — 4회차 가상 히스토리로 세 메커니즘이 전부 작동하는지 확인
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from allocation_draft_generator import BOTTLENECK_TO_CATEGORY, CATEGORIES

    # 가상의 4회차 히스토리: 원가율 병목이 계속 지속되고, 회차1의 마케팅 배분 이후
    # 회차2에 원가율 병목이 새로 발생하는 케이스를 시뮬레이션
    fake_history = [
        {
            "round": 1,
            "findings": [{"bottleneck_type": "time_of_day_weakness"}],
            "pos_data": {"monthly_revenue": 7_500_000, "monthly_cogs": 3_375_000,
                         "monthly_labor_cost": 1_350_000, "repeat_customer_rate": 0.30},
            "selected_allocation": {"marketing_online": 0.85, "equipment_interior": 0.05,
                                     "labor": 0.05, "inventory": 0.05},
        },
        {
            "round": 2,
            "findings": [{"bottleneck_type": "high_cost_ratio"}],
            "pos_data": {"monthly_revenue": 8_100_000, "monthly_cogs": 4_536_000,
                         "monthly_labor_cost": 1_458_000, "repeat_customer_rate": 0.32},
            "selected_allocation": {"marketing_online": 0.2, "equipment_interior": 0.6,
                                     "labor": 0.1, "inventory": 0.1},
        },
        {
            "round": 3,
            "findings": [{"bottleneck_type": "high_cost_ratio"}],
            "pos_data": {"monthly_revenue": 8_300_000, "monthly_cogs": 4_648_000,
                         "monthly_labor_cost": 1_494_000, "repeat_customer_rate": 0.33},
            "selected_allocation": {"marketing_online": 0.2, "equipment_interior": 0.6,
                                     "labor": 0.1, "inventory": 0.1},
        },
    ]

    print("=" * 70)
    print("메커니즘 1: 개인 기준선 치환")
    print("=" * 70)
    baselines = compute_personal_baselines(fake_history)
    print(f"3회차 누적 -> 개인 기준선 계산됨: {baselines}")

    print("\n" + "=" * 70)
    print("메커니즘 2: 지속 병목 가중치 상향")
    print("=" * 70)
    persistence = compute_persistence_counts(fake_history)
    print(f"병목별 연속 발생 횟수: {persistence}")
    min_shares = compute_escalated_min_shares(persistence, BOTTLENECK_TO_CATEGORY, CATEGORIES)
    print(f"카테고리별 최소 배정 비중 (상향 반영): {min_shares}")

    print("\n" + "=" * 70)
    print("메커니즘 3: 부작용(trade-off) 이력 추적")
    print("=" * 70)
    warnings = compute_tradeoff_warnings(fake_history, BOTTLENECK_TO_CATEGORY)
    print(f"발견된 부작용 이력: {warnings}")