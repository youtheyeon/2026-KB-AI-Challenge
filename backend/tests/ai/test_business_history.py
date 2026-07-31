# 완료 회차 이력이 다음 배분안의 지속 병목과 부작용 신호를 만드는지 검증하는 테스트
from allocation_draft_generator import BOTTLENECK_TO_CATEGORY, CATEGORIES
from business_history import (
    compute_escalated_min_shares,
    compute_persistence_counts,
    compute_tradeoff_warnings,
)


def completed_history() -> list[dict]:
    return [
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


def test_persistent_bottleneck_escalates_corresponding_minimum_share() -> None:
    counts = compute_persistence_counts(completed_history())
    shares = compute_escalated_min_shares(counts, BOTTLENECK_TO_CATEGORY, CATEGORIES)

    assert counts["high_cost_ratio"] == 2
    assert counts["time_of_day_weakness"] == 0
    assert shares["equipment_interior"] == 0.15
    assert shares["marketing_online"] == 0.05


def test_tradeoff_warning_records_new_bottleneck_after_funded_category() -> None:
    warnings = compute_tradeoff_warnings(completed_history(), BOTTLENECK_TO_CATEGORY)

    assert warnings == [
        {
            "category": "equipment_interior",
            "resulting_bottleneck": "high_cost_ratio",
            "occurred_after_round": 1,
        }
    ]
