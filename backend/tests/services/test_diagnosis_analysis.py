# 사업 진단 지표 계산과 병목 판정 규칙을 검증하는 테스트
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.domain.enums import BottleneckSeverity
from app.services.diagnosis_analysis import (
    AnalysisInput,
    Benchmark,
    DiagnosisAnalysisError,
    analyze,
    load_benchmark,
)


def benchmark() -> Benchmark:
    return Benchmark(
        reference_date=date(2024, 6, 30),
        source_name="서울시 상권분석서비스 추정매출-상권",
        snapshot_version="20242-cafe-v1",
        reference_area="서울 전체 커피-음료 상권",
        sample_size=326,
        median_monthly_sales_amount=32_608_696,
        median_monthly_order_count=500,
        time_of_day_sales_ratios={
            "00_06": Decimal("0.01"),
            "06_11": Decimal("0.15"),
            "11_14": Decimal("0.30"),
            "14_17": Decimal("0.25"),
            "17_21": Decimal("0.24"),
            "21_24": Decimal("0.05"),
        },
    )


def input_data() -> AnalysisInput:
    return AnalysisInput(
        reference_date=date(2026, 7, 31),
        monthly_sales_amount=30_000_000,
        monthly_expense_amount=26_700_000,
        material_cost_amount=12_000_000,
        labor_cost_amount=6_000_000,
        existing_monthly_repayment_amount=1_500_000,
        monthly_order_count=420,
        employee_count=2,
        online_sales_amount=2_700_000,
        online_gross_order_amount=3_000_000,
        online_platform_cost_amount=450_000,
        online_refund_amount=150_000,
        online_settlement_amount=2_760_000,
        timed_sales_by_bucket={},
        timed_sales_coverage=Decimal("0"),
    )


def test_load_benchmark_reads_versioned_public_data_snapshot() -> None:
    loaded = load_benchmark()

    assert loaded.reference_date == date(2024, 6, 30)
    assert loaded.snapshot_version == "20242-cafe-v1"
    assert loaded.sample_size == 326
    assert loaded.median_monthly_sales_amount == 94_283_406
    assert loaded.median_monthly_order_count == 11_729


def test_analyze_calculates_financial_activity_and_commercial_metrics() -> None:
    result = analyze(input_data(), benchmark())

    values = {metric.code: metric.current_value for metric in result.metrics}
    assert values["MONTHLY_SALES_AMOUNT"] == Decimal("30000000")
    assert values["OPERATING_PROFIT_RATE"] == Decimal("11.0")
    assert values["MATERIAL_COST_RATE"] == Decimal("40.0")
    assert values["CASH_SURPLUS_AMOUNT"] == Decimal("1800000")
    assert values["MONTHLY_ORDER_COUNT"] == Decimal("420")
    assert values["ONLINE_SALES_RATIO"] == Decimal("9.0")
    assert values["EMPLOYEE_COUNT"] == Decimal("2")
    assert values["SALES_COMPARED_TO_PEER_RATE"] == Decimal("-8.0")


def test_analyze_rejects_zero_monthly_sales() -> None:
    with pytest.raises(DiagnosisAnalysisError, match="월매출"):
        analyze(replace(input_data(), monthly_sales_amount=0), benchmark())


def test_analyze_detects_severe_material_cost_and_channel_concentration() -> None:
    result = analyze(
        replace(
            input_data(),
            material_cost_amount=17_100_000,
            online_sales_amount=1_500_000,
        ),
        benchmark(),
    )

    by_code = {item.code: item for item in result.bottlenecks}
    assert by_code["HIGH_MATERIAL_COST"].severity is BottleneckSeverity.SEVERE
    assert by_code["CHANNEL_CONCENTRATION"].severity is BottleneckSeverity.SEVERE


def test_analyze_omits_online_metrics_and_bottlenecks_without_online_data() -> None:
    result = analyze(
        replace(
            input_data(),
            online_sales_amount=None,
            online_gross_order_amount=None,
            online_platform_cost_amount=None,
            online_refund_amount=None,
            online_settlement_amount=None,
        ),
        benchmark(),
    )

    codes = {metric.code for metric in result.metrics}
    bottleneck_codes = {item.code for item in result.bottlenecks}
    assert "ONLINE_SALES_RATIO" not in codes
    assert bottleneck_codes.isdisjoint(
        {
            "CHANNEL_CONCENTRATION",
            "HIGH_PLATFORM_COST",
            "HIGH_ONLINE_REFUND_RATE",
            "LOW_NET_SETTLEMENT_RATE",
        }
    )


def test_analyze_requires_eighty_percent_timed_sales_coverage() -> None:
    below_threshold = analyze(
        replace(
            input_data(),
            timed_sales_by_bucket={"17_21": 1_000_000},
            timed_sales_coverage=Decimal("0.79"),
        ),
        benchmark(),
    )
    at_threshold = analyze(
        replace(
            input_data(),
            timed_sales_by_bucket={"17_21": 1_000_000},
            timed_sales_coverage=Decimal("0.80"),
        ),
        benchmark(),
    )

    assert "TIME_OF_DAY_WEAKNESS" not in {item.code for item in below_threshold.bottlenecks}
    assert "TIME_OF_DAY_WEAKNESS" in {item.code for item in at_threshold.bottlenecks}
