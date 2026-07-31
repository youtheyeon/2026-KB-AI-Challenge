# 백엔드 도메인 코드와 AI 모듈 입력 코드를 명시적으로 변환하는 경계

AI_BOTTLENECK_TYPE_BY_STORED_TYPE = {
    "HIGH_MATERIAL_COST": "high_cost_ratio",
    "HIGH_LABOR_COST": "high_labor_ratio",
    "CHANNEL_CONCENTRATION": "low_online_sales_share",
    "HIGH_PLATFORM_COST": "high_platform_cost_rate",
    "HIGH_ONLINE_REFUND_RATE": "high_online_cancel_refund_rate",
    "LOW_NET_SETTLEMENT_RATE": "low_net_settlement_rate",
    "TIME_OF_DAY_WEAKNESS": "time_of_day_weakness",
}


def to_ai_bottleneck_type(bottleneck_type: str) -> str:
    return AI_BOTTLENECK_TYPE_BY_STORED_TYPE.get(bottleneck_type, bottleneck_type)
