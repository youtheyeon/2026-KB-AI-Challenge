# 월별 사업 지표를 계산하고 벤치마크 대비 병목 후보를 판정하는 서비스
import json
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from app.domain.enums import BottleneckSeverity, DataSourceType

PERCENT_QUANTUM = Decimal("0.1")
HUNDRED = Decimal("100")
TIME_BUCKETS = ("00_06", "06_11", "11_14", "14_17", "17_21", "21_24")


class DiagnosisAnalysisError(ValueError):
    pass


@dataclass(frozen=True)
class Benchmark:
    reference_date: date
    source_name: str
    snapshot_version: str
    reference_area: str
    sample_size: int
    median_monthly_sales_amount: int
    median_monthly_order_count: int
    time_of_day_sales_ratios: dict[str, Decimal]

    def to_raw_data(self) -> dict[str, Any]:
        return {
            "referenceDate": self.reference_date.isoformat(),
            "sourceName": self.source_name,
            "snapshotVersion": self.snapshot_version,
            "referenceArea": self.reference_area,
            "sampleSize": self.sample_size,
            "medianMonthlySalesAmount": self.median_monthly_sales_amount,
            "medianMonthlyOrderCount": self.median_monthly_order_count,
            "timeOfDaySalesRatios": {
                bucket: float(ratio) for bucket, ratio in self.time_of_day_sales_ratios.items()
            },
            "floatingPopulationGrowthRate": None,
            "floatingPopulationUnavailableReason": ("현재 캐시에는 유동인구 데이터가 없습니다."),
        }


@dataclass(frozen=True)
class AnalysisInput:
    reference_date: date
    monthly_sales_amount: int
    monthly_expense_amount: int
    material_cost_amount: int
    labor_cost_amount: int
    existing_monthly_repayment_amount: int
    monthly_order_count: int
    employee_count: int
    online_sales_amount: int | None
    online_gross_order_amount: int | None
    online_platform_cost_amount: int | None
    online_refund_amount: int | None
    online_settlement_amount: int | None
    timed_sales_by_bucket: dict[str, int]
    timed_sales_coverage: Decimal


@dataclass(frozen=True)
class MetricResult:
    code: str
    current_value: Decimal
    current_source_type: DataSourceType
    comparison_value: Decimal
    comparison_source_type: DataSourceType
    difference_value: Decimal
    unit: str


@dataclass(frozen=True)
class BottleneckResult:
    code: str
    title: str
    detail: str
    severity: BottleneckSeverity
    evidence_source_type: DataSourceType
    evidence_description: str
    related_categories: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisResult:
    metrics: tuple[MetricResult, ...]
    bottlenecks: tuple[BottleneckResult, ...]


def load_benchmark() -> Benchmark:
    path = Path(__file__).resolve().parents[1] / "data" / "seoul_cafe_benchmark.json"
    return benchmark_from_raw_data(json.loads(path.read_text(encoding="utf-8")))


def benchmark_from_raw_data(raw_data: dict[str, Any]) -> Benchmark:
    return Benchmark(
        reference_date=date.fromisoformat(str(raw_data["referenceDate"])),
        source_name=str(raw_data["sourceName"]),
        snapshot_version=str(raw_data["snapshotVersion"]),
        reference_area=str(raw_data["referenceArea"]),
        sample_size=int(raw_data["sampleSize"]),
        median_monthly_sales_amount=int(raw_data["medianMonthlySalesAmount"]),
        median_monthly_order_count=int(raw_data["medianMonthlyOrderCount"]),
        time_of_day_sales_ratios={
            bucket: Decimal(str(ratio))
            for bucket, ratio in dict(raw_data["timeOfDaySalesRatios"]).items()
        },
    )


def analyze(input_data: AnalysisInput, benchmark: Benchmark) -> AnalysisResult:
    if input_data.monthly_sales_amount <= 0:
        raise DiagnosisAnalysisError("월매출이 0보다 커야 합니다.")

    operating_profit_rate = _percentage(
        input_data.monthly_sales_amount - input_data.monthly_expense_amount,
        input_data.monthly_sales_amount,
    )
    material_cost_rate = _percentage(
        input_data.material_cost_amount,
        input_data.monthly_sales_amount,
    )
    cash_surplus_amount = (
        input_data.monthly_sales_amount
        - input_data.monthly_expense_amount
        - input_data.existing_monthly_repayment_amount
    )
    online_sales_ratio = (
        _percentage(input_data.online_sales_amount, input_data.monthly_sales_amount)
        if input_data.online_sales_amount is not None
        else None
    )
    sales_compared_to_peer_rate = _percentage(
        input_data.monthly_sales_amount - benchmark.median_monthly_sales_amount,
        benchmark.median_monthly_sales_amount,
    )

    metrics = _build_metrics(
        input_data,
        benchmark,
        operating_profit_rate,
        material_cost_rate,
        cash_surplus_amount,
        online_sales_ratio,
        sales_compared_to_peer_rate,
    )
    bottlenecks = _detect_bottlenecks(
        input_data,
        benchmark,
        material_cost_rate,
        online_sales_ratio,
    )
    return AnalysisResult(metrics=tuple(metrics), bottlenecks=tuple(bottlenecks))


def _build_metrics(
    input_data: AnalysisInput,
    benchmark: Benchmark,
    operating_profit_rate: Decimal,
    material_cost_rate: Decimal,
    cash_surplus_amount: int,
    online_sales_ratio: Decimal | None,
    sales_compared_to_peer_rate: Decimal,
) -> list[MetricResult]:
    calculated = DataSourceType.CALCULATED
    benchmark_source = DataSourceType.BENCHMARK
    assumption = DataSourceType.DOMAIN_ASSUMPTION
    metrics = [
        _metric(
            "MONTHLY_SALES_AMOUNT",
            input_data.monthly_sales_amount,
            benchmark.median_monthly_sales_amount,
            "KRW",
            calculated,
            benchmark_source,
        ),
        _metric(
            "OPERATING_PROFIT_RATE",
            operating_profit_rate,
            Decimal("12.6"),
            "PERCENT",
            calculated,
            assumption,
        ),
        _metric(
            "MATERIAL_COST_RATE",
            material_cost_rate,
            Decimal("42.0"),
            "PERCENT",
            calculated,
            assumption,
        ),
        _metric(
            "CASH_SURPLUS_AMOUNT",
            cash_surplus_amount,
            0,
            "KRW",
            calculated,
            assumption,
        ),
        _metric(
            "MONTHLY_ORDER_COUNT",
            input_data.monthly_order_count,
            benchmark.median_monthly_order_count,
            "COUNT",
            calculated,
            benchmark_source,
        ),
        _metric(
            "EMPLOYEE_COUNT",
            input_data.employee_count,
            0,
            "COUNT",
            DataSourceType.USER_INPUT,
            assumption,
        ),
        _metric(
            "SALES_COMPARED_TO_PEER_RATE",
            sales_compared_to_peer_rate,
            0,
            "PERCENT",
            calculated,
            benchmark_source,
        ),
    ]
    if online_sales_ratio is not None:
        metrics.append(
            _metric(
                "ONLINE_SALES_RATIO",
                online_sales_ratio,
                Decimal("20.0"),
                "PERCENT",
                calculated,
                assumption,
            )
        )
    return metrics


def _metric(
    code: str,
    current_value: int | Decimal,
    comparison_value: int | Decimal,
    unit: str,
    current_source_type: DataSourceType,
    comparison_source_type: DataSourceType,
) -> MetricResult:
    current = Decimal(current_value)
    comparison = Decimal(comparison_value)
    return MetricResult(
        code=code,
        current_value=current,
        current_source_type=current_source_type,
        comparison_value=comparison,
        comparison_source_type=comparison_source_type,
        difference_value=current - comparison,
        unit=unit,
    )


def _detect_bottlenecks(
    input_data: AnalysisInput,
    benchmark: Benchmark,
    material_cost_rate: Decimal,
    online_sales_ratio: Decimal | None,
) -> list[BottleneckResult]:
    findings: list[BottleneckResult] = []
    _append_assumption_finding(
        findings,
        code="HIGH_MATERIAL_COST",
        title="재료비 부담 상승",
        actual=material_cost_rate,
        baseline=Decimal("42.0"),
        detail_label="재료비율",
        high_is_bad=True,
        thresholds=(Decimal("5"), Decimal("10"), Decimal("15")),
        related_categories=("inventory",),
    )

    labor_cost_rate = _percentage(
        input_data.labor_cost_amount,
        input_data.monthly_sales_amount,
    )
    _append_assumption_finding(
        findings,
        code="HIGH_LABOR_COST",
        title="인건비 부담 상승",
        actual=labor_cost_rate,
        baseline=Decimal("20.0"),
        detail_label="인건비율",
        high_is_bad=True,
        thresholds=(Decimal("5"), Decimal("10"), Decimal("15")),
        related_categories=("labor",),
    )

    if online_sales_ratio is not None:
        _append_assumption_finding(
            findings,
            code="CHANNEL_CONCENTRATION",
            title="판매 채널 편중",
            actual=online_sales_ratio,
            baseline=Decimal("20.0"),
            detail_label="온라인 매출 비중",
            high_is_bad=False,
            thresholds=(Decimal("5"), Decimal("10"), Decimal("15")),
            related_categories=("marketing_online",),
        )
        _append_online_cost_findings(findings, input_data)

    if input_data.timed_sales_coverage >= Decimal("0.80"):
        findings.extend(_time_of_day_findings(input_data, benchmark))
    return findings


def _append_online_cost_findings(
    findings: list[BottleneckResult],
    input_data: AnalysisInput,
) -> None:
    gross = input_data.online_gross_order_amount
    if gross is None or gross <= 0:
        return

    if input_data.online_platform_cost_amount is not None:
        _append_assumption_finding(
            findings,
            code="HIGH_PLATFORM_COST",
            title="플랫폼 비용 부담",
            actual=_percentage(input_data.online_platform_cost_amount, gross),
            baseline=Decimal("15.0"),
            detail_label="플랫폼 비용률",
            high_is_bad=True,
            thresholds=(Decimal("5"), Decimal("10"), Decimal("15")),
            related_categories=("marketing_online",),
        )
    if input_data.online_refund_amount is not None:
        _append_assumption_finding(
            findings,
            code="HIGH_ONLINE_REFUND_RATE",
            title="온라인 취소·환불 증가",
            actual=_percentage(input_data.online_refund_amount, gross),
            baseline=Decimal("5.0"),
            detail_label="온라인 취소·환불률",
            high_is_bad=True,
            thresholds=(Decimal("5"), Decimal("8"), Decimal("12")),
            related_categories=("inventory",),
        )
    if input_data.online_settlement_amount is not None:
        _append_assumption_finding(
            findings,
            code="LOW_NET_SETTLEMENT_RATE",
            title="온라인 순정산율 저조",
            actual=_percentage(input_data.online_settlement_amount, gross),
            baseline=Decimal("92.0"),
            detail_label="온라인 순정산율",
            high_is_bad=False,
            thresholds=(Decimal("5"), Decimal("10"), Decimal("15")),
            related_categories=("marketing_online",),
        )


def _append_assumption_finding(
    findings: list[BottleneckResult],
    *,
    code: str,
    title: str,
    actual: Decimal,
    baseline: Decimal,
    detail_label: str,
    high_is_bad: bool,
    thresholds: tuple[Decimal, Decimal, Decimal],
    related_categories: tuple[str, ...],
) -> None:
    gap = actual - baseline if high_is_bad else baseline - actual
    severity = _severity(gap, thresholds)
    if severity is None:
        return
    findings.append(
        BottleneckResult(
            code=code,
            title=title,
            detail=f"{detail_label} {actual}% · 업계 참고치 {baseline}%.",
            severity=severity,
            evidence_source_type=DataSourceType.DOMAIN_ASSUMPTION,
            evidence_description="업로드 자료를 실증 데이터가 아닌 업계 참고치와 비교했습니다.",
            related_categories=related_categories,
        )
    )


def _time_of_day_findings(
    input_data: AnalysisInput,
    benchmark: Benchmark,
) -> list[BottleneckResult]:
    findings = []
    for bucket in TIME_BUCKETS:
        benchmark_ratio = benchmark.time_of_day_sales_ratios.get(bucket, Decimal("0"))
        if benchmark_ratio <= Decimal("0.05"):
            continue
        actual_ratio = Decimal(input_data.timed_sales_by_bucket.get(bucket, 0)) / Decimal(
            input_data.monthly_sales_amount
        )
        relative_gap = (benchmark_ratio - actual_ratio) / benchmark_ratio
        severity = _severity(
            relative_gap,
            (Decimal("0.15"), Decimal("0.35"), Decimal("0.60")),
        )
        if severity is None:
            continue
        findings.append(
            BottleneckResult(
                code="TIME_OF_DAY_WEAKNESS",
                title=f"{bucket.replace('_', '~')}시 고객 유입 부족",
                detail=(
                    f"매출 비중 {_as_percent(actual_ratio)}% · "
                    f"서울 카페 벤치마크 {_as_percent(benchmark_ratio)}%."
                ),
                severity=severity,
                evidence_source_type=DataSourceType.PUBLIC_DATA,
                evidence_description=(
                    f"서울시 카페 매출 데이터 {benchmark.sample_size}개 상권의 "
                    "시간대별 평균과 비교했습니다."
                ),
                related_categories=("marketing_online",),
            )
        )
    return findings


def _severity(
    gap: Decimal,
    thresholds: tuple[Decimal, Decimal, Decimal],
) -> BottleneckSeverity | None:
    mild, clear, severe = thresholds
    if gap >= severe:
        return BottleneckSeverity.SEVERE
    if gap >= clear:
        return BottleneckSeverity.CLEAR
    if gap >= mild:
        return BottleneckSeverity.MILD
    return None


def _percentage(numerator: int | Decimal, denominator: int | Decimal) -> Decimal:
    if Decimal(denominator) == 0:
        return Decimal("0.0")
    return (Decimal(numerator) * HUNDRED / Decimal(denominator)).quantize(
        PERCENT_QUANTUM, rounding=ROUND_HALF_UP
    )


def _as_percent(ratio: Decimal) -> Decimal:
    return (ratio * HUNDRED).quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP)
