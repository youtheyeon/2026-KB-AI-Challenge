"""
Mock POS/카드매출 데이터 생성기

실제 서비스에서는 사업자 동의를 받아 카드사/POS 데이터를 연동하지만,
지금은 그 데이터가 없으니 '병목 진단 로직을 테스트하기 위한' mock 데이터를 만든다.

중요: 이 mock 데이터의 필드 구조는 실제 연동 시 그대로 쓸 수 있도록 설계했다.
      즉, 나중에 진짜 POS 데이터가 들어와도 bottleneck_detector.py는 코드 수정 없이 작동해야 한다.
"""

import json
import random

# 실제 공공데이터(서울시 상권분석서비스)와 동일한 시간대 구간을 사용
# -> 나중에 세그먼트 벤치마크와 '같은 기준'으로 비교하기 위해 필드명을 맞춰둠
TIME_BUCKETS = ["00_06", "06_11", "11_14", "14_17", "17_21", "21_24"]
WEEKDAYS = ["MON", "TUES", "WED", "THUR", "FRI", "SAT", "SUN"]


def generate_mock_pos_data(scenario: str = "normal", monthly_revenue: int = 7_500_000, include_online_data: bool = True) -> dict:
    """
    scenario 옵션:
      - "normal": 특별한 병목 없는 평균적인 카페
      - "evening_weak": 저녁 시간대 매출이 유독 저조한 카페
      - "high_cost_ratio": 원가율이 높은 카페
      - "low_repeat": 재구매율이 낮은 카페
      - "high_labor_ratio": 인건비 비중이 높은 카페
      - "seat_shortage": 좌석 부족으로 피크타임 손실이 있는 카페
      - "high_platform_cost": 배달앱 등 플랫폼 비용률이 높은 카페
      - "low_online_sales_share": 온라인 판매 비중이 낮은 카페
      - "high_cancel_refund": 온라인 취소·환불률이 높고 정산율이 낮은 카페
      - "multi_bottleneck": 저녁시간대 부족 + 원가율 상승 + 재구매율 저조가
        동시에 나타나는 복합 시나리오 (A/B/C 배분안이 실제로 갈리는지 테스트용)
    """
    random.seed(hash(scenario) % 1000)  # 시나리오별로 같은 결과 재현되게

    # 시간대별 매출 비중 (기본 분포 -> 시나리오에 따라 왜곡)
    base_time_dist = {"00_06": 0.01, "06_11": 0.15, "11_14": 0.30, "14_17": 0.25, "17_21": 0.24, "21_24": 0.05}
    if scenario in ("evening_weak", "multi_bottleneck"):
        base_time_dist = {"00_06": 0.01, "06_11": 0.18, "11_14": 0.35, "14_17": 0.30, "17_21": 0.12, "21_24": 0.04}

    time_sales = {f"TMZON_{b}_SELNG_AMT": round(monthly_revenue * base_time_dist[b]) for b in TIME_BUCKETS}

    # 요일별 매출 비중 (평이한 분포)
    weekday_dist_base = 1 / 7
    weekday_sales = {f"{d}_SELNG_AMT": round(monthly_revenue * weekday_dist_base * random.uniform(0.85, 1.15)) for d in WEEKDAYS}

    # 원가율 (COGS / 매출)
    cogs_ratio = 0.45
    if scenario in ("high_cost_ratio", "multi_bottleneck"):
        cogs_ratio = 0.62
    monthly_cogs = round(monthly_revenue * cogs_ratio)

    # 인건비 비중
    labor_ratio = 0.18
    if scenario == "high_labor_ratio":
        labor_ratio = 0.35
    monthly_labor_cost = round(monthly_revenue * labor_ratio)

    # 재구매율 (전체 고객 중 해당 기간 재방문 고객 비율)
    repeat_customer_rate = 0.38
    if scenario in ("low_repeat", "multi_bottleneck"):
        repeat_customer_rate = 0.19

    # 좌석/처리용량 지표
    seat_count = 10
    avg_daily_customers = 90
    peak_hour_utilization_rate = 0.75  # 피크타임 좌석 점유율
    avg_wait_time_minutes = 4.0
    estimated_lost_customers_per_day = 0  # 대기 이탈 추정치
    if scenario == "seat_shortage":
        peak_hour_utilization_rate = 0.98
        avg_wait_time_minutes = 14.0
        estimated_lost_customers_per_day = 12

    # 온라인 채널·정산 데이터 (스펙 8.3, 10.3 -- 선택 자료. 없으면 None으로 명시)
    online_data = None
    if include_online_data:
        online_order_share = 0.22  # 정상 시나리오 기본값
        online_gross_order_amount = round(monthly_revenue * online_order_share)
        online_order_count = round(avg_daily_customers * 30 * online_order_share * 0.9)  # 온라인은 객단가가 조금 더 높다고 가정
        platform_fee_rate = 0.12
        payment_fee_rate = 0.03
        merchant_delivery_fee_rate = 0.02
        cancel_refund_rate = 0.03
        settlement_rate = 0.94

        if scenario == "high_platform_cost":
            platform_fee_rate, payment_fee_rate, merchant_delivery_fee_rate = 0.22, 0.04, 0.06
        elif scenario == "low_online_sales_share":
            online_order_share = 0.04
            online_gross_order_amount = round(monthly_revenue * online_order_share)
            online_order_count = round(avg_daily_customers * 30 * online_order_share * 0.9)
        elif scenario == "high_cancel_refund":
            cancel_refund_rate = 0.15
            settlement_rate = 0.80

        online_platform_fee = round(online_gross_order_amount * platform_fee_rate)
        online_payment_fee = round(online_gross_order_amount * payment_fee_rate)
        online_merchant_delivery_fee = round(online_gross_order_amount * merchant_delivery_fee_rate)
        online_cancel_refund_amount = round(online_gross_order_amount * cancel_refund_rate)
        online_net_sales_amount = online_gross_order_amount - online_cancel_refund_amount
        online_settlement_amount = round(online_gross_order_amount * settlement_rate)

        online_data = {
            "online_gross_order_amount": online_gross_order_amount,
            "online_order_count": online_order_count,
            "online_net_sales_amount": online_net_sales_amount,
            "online_cancel_refund_amount": online_cancel_refund_amount,
            "online_platform_fee": online_platform_fee,
            "online_payment_fee": online_payment_fee,
            "online_merchant_delivery_fee": online_merchant_delivery_fee,
            "online_settlement_amount": online_settlement_amount,
            # reconciliation_type 기본값 INCLUDED_IN_POS_TOTAL 고정 (스펙 8.3 원칙) -> 전체매출에 중복 합산하지 않음
            "reconciliation_type": "INCLUDED_IN_POS_TOTAL",
        }

    return {
        "scenario_label": scenario,  # mock 표시용, 실제 연동 시엔 없는 필드
        "monthly_revenue": monthly_revenue,
        "monthly_cogs": monthly_cogs,
        "monthly_labor_cost": monthly_labor_cost,
        "time_of_day_sales": time_sales,
        "weekday_sales": weekday_sales,
        "repeat_customer_rate": repeat_customer_rate,
        "seat_count": seat_count,
        "avg_daily_customers": avg_daily_customers,
        "peak_hour_utilization_rate": peak_hour_utilization_rate,
        "avg_wait_time_minutes": avg_wait_time_minutes,
        "estimated_lost_customers_per_day": estimated_lost_customers_per_day,
        "online_data": online_data,  # None이면 '온라인 자료 없음' -> 관련 병목 생성 안 함
    }


if __name__ == "__main__":
    import os

    os.makedirs("./raw_data/mock_pos", exist_ok=True)

    scenarios = ["normal", "evening_weak", "high_cost_ratio", "high_labor_ratio", "low_repeat", "seat_shortage",
                 "high_platform_cost", "low_online_sales_share", "high_cancel_refund", "multi_bottleneck"]
    for sc in scenarios:
        data = generate_mock_pos_data(scenario=sc)
        path = f"./raw_data/mock_pos/{sc}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"생성 완료: {path}")