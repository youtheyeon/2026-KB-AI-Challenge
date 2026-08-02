# 실제 성과를 목표와 비교하고 병목 변화를 다음 시뮬레이션 이력으로 저장하는 서비스
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.dataset import BusinessSnapshot
from app.domain.diagnosis import Diagnosis
from app.domain.enums import (
    BottleneckChangeType,
    OutcomeDataSourceType,
    OutcomeDataStatus,
    OutcomeMetricStatus,
    OutcomeStatus,
)
from app.domain.execution import Execution
from app.domain.outcome import (
    BottleneckChange,
    OutcomeComparison,
    OutcomeComparisonMetric,
    OutcomeData,
    ReassessmentSnapshot,
)
from app.domain.simulation import Simulation
from app.services.ai_contract import to_ai_bottleneck_type
from app.services.diagnosis_analysis import AnalysisInput, DiagnosisAnalysisError
from app.services.diagnosis_service import collect_analysis_input
from app.services.outcome_engine import (
    FinancialProjectionRequest,
    OutcomeCalculationError,
    OutcomeEngine,
    OutcomeEngineRequest,
)
from app.services.verification import require_owned_simulation

READY_OUTCOME_DATA_STATUSES = {
    OutcomeDataStatus.READY,
    OutcomeDataStatus.MAPPING_READY,
}
FILE_COMPARABLE_BOTTLENECKS = {
    "high_cost_ratio",
    "high_labor_ratio",
}
METRIC_LABELS = {
    "MONTHLY_SALES": "월 매출",
    "OPERATING_PROFIT": "영업이익",
    "ONLINE_ORDER_RATIO": "온라인 주문 비중",
    "CASH_AFTER_REPAYMENT": "상환 후 잔여 현금",
}
BOTTLENECK_TITLES = {
    "high_cost_ratio": "원가율 상승",
    "high_labor_ratio": "인건비 부담 상승",
    "low_online_sales_share": "낮은 온라인 판매 비중",
    "high_platform_cost_rate": "높은 플랫폼 비용률",
    "high_online_cancel_refund_rate": "높은 온라인 취소·환불률",
    "low_net_settlement_rate": "낮은 순정산율",
    "time_of_day_weakness": "특정 시간대 고객 유입 부족",
}


@dataclass(frozen=True)
class OutcomeCreationCommand:
    simulation_id: int
    execution_id: int
    outcome_data_id: int


@dataclass(frozen=True)
class OutcomeSummary:
    sales_growth_status: str
    online_ratio_status: str
    cash_after_repayment_status: str


@dataclass(frozen=True)
class OutcomeCreated:
    outcome_id: int
    simulation_id: int
    status: str
    summary: OutcomeSummary
    created_at: datetime


@dataclass(frozen=True)
class MetricTrend:
    metric_code: str
    before_value: Decimal | None
    after_value: Decimal | None
    unit: str


@dataclass(frozen=True)
class ComparisonRow:
    metric_code: str
    label: str
    target_value: Decimal | None
    break_even_value: Decimal | None
    observed_value: Decimal | None
    unit: str
    status: str


@dataclass(frozen=True)
class ReevaluationItem:
    bottleneck_type: str
    change_type: str
    detail: str | None


@dataclass(frozen=True)
class NewBottleneckResult:
    bottleneck_type: str
    title: str
    detail: str | None


@dataclass(frozen=True)
class OutcomeResult:
    outcome_id: int
    simulation_id: int
    overall_status: str
    trends: tuple[MetricTrend, ...]
    comparison_rows: tuple[ComparisonRow, ...]
    reevaluation: tuple[ReevaluationItem, ...]
    new_bottlenecks: tuple[NewBottleneckResult, ...]
    created_at: datetime


@dataclass(frozen=True)
class _PreparedOutcome:
    simulation_id: int
    execution_id: int
    outcome_data_id: int
    diagnosis_id: int
    observed_snapshot_id: int
    source_type: OutcomeDataSourceType
    allocation: dict[str, float]
    loan_amount: int
    monthly_revenue: int
    annual_interest_rate: Decimal
    term_months: int
    grace_months: int
    repayment_type: Any
    baseline_sales: int
    baseline_expense: int
    baseline_online_ratio: Decimal | None
    pre_findings: tuple[dict[str, Any], ...]
    previous_bottleneck_ids: dict[str, int | None]
    break_even_additional_revenue_target: int | None
    raw_pos_data: dict[str, Any] | None
    file_analysis: AnalysisInput | None
    manual_values: tuple[int | None, int | None, Decimal | None, int | None]


@dataclass(frozen=True)
class _CalculatedOutcome:
    status: OutcomeStatus
    metrics: tuple[OutcomeComparisonMetric, ...]
    changes: tuple[BottleneckChange, ...]
    next_round_snapshot: dict[str, Any]


def classify_metric(
    target_value: Decimal | None,
    break_even_value: Decimal | None,
    observed_value: Decimal | None,
) -> OutcomeMetricStatus:
    if (
        target_value is None
        or break_even_value is None
        or observed_value is None
        or target_value < break_even_value
    ):
        return OutcomeMetricStatus.NOT_COMPARABLE
    if observed_value >= target_value:
        return OutcomeMetricStatus.ABOVE_EXPECTED
    if observed_value >= break_even_value:
        return OutcomeMetricStatus.WITHIN_RANGE
    return OutcomeMetricStatus.BELOW_EXPECTED


class OutcomeService:
    def __init__(self, database: Session, engine: OutcomeEngine) -> None:
        self.database = database
        self.engine = engine

    def create(
        self,
        command: OutcomeCreationCommand,
        session_cookie: str | None,
        *,
        now: datetime | None = None,
    ) -> OutcomeCreated:
        saved_at = now or datetime.now(UTC)
        try:
            prepared = self._prepare(command, session_cookie)
        except ApiError:
            self.database.rollback()
            raise
        self.database.rollback()

        try:
            calculated = self._calculate(prepared)
        except OutcomeCalculationError as error:
            raise ApiError(
                502,
                "OUTCOME_CALCULATION_FAILED",
                "결과 검증 계산에 실패했습니다.",
            ) from error

        try:
            with self.database.begin():
                simulation = require_owned_simulation(
                    self.database,
                    command.simulation_id,
                    session_cookie,
                    with_for_update=True,
                )
                execution = self.database.get(
                    Execution,
                    command.execution_id,
                    with_for_update=True,
                )
                outcome_data = self.database.get(
                    OutcomeData,
                    command.outcome_data_id,
                    with_for_update=True,
                )
                self._validate_sources(simulation, execution, outcome_data, command)
                self._require_no_comparison(command.simulation_id)

                reassessment = ReassessmentSnapshot(
                    latest_business_snapshot_id=prepared.observed_snapshot_id,
                    previous_diagnosis_id=prepared.diagnosis_id,
                    current_diagnosis_id=None,
                    changes=list(calculated.changes),
                )
                comparison = OutcomeComparison(
                    simulation_id=command.simulation_id,
                    execution_id=command.execution_id,
                    outcome_data_id=command.outcome_data_id,
                    status=calculated.status,
                    next_round_pos_data_snapshot=calculated.next_round_snapshot,
                    metrics=list(calculated.metrics),
                    reassessment_snapshot=reassessment,
                )
                self.database.add(comparison)
                self.database.flush()
                if comparison.id is None:
                    raise RuntimeError("결과 비교 ID가 생성되지 않았습니다.")
                comparison.created_at = saved_at
        except IntegrityError as error:
            raise _duplicate_outcome() from error

        metrics = {metric.metric_code: metric for metric in comparison.metrics}
        return OutcomeCreated(
            outcome_id=comparison.id,
            simulation_id=comparison.simulation_id,
            status="COMPLETED",
            summary=OutcomeSummary(
                sales_growth_status=metrics["MONTHLY_SALES"].status.name,
                online_ratio_status=metrics["ONLINE_ORDER_RATIO"].status.name,
                cash_after_repayment_status=metrics["CASH_AFTER_REPAYMENT"].status.name,
            ),
            created_at=comparison.created_at,
        )

    def get_result(
        self,
        simulation_id: int,
        session_cookie: str | None,
    ) -> OutcomeResult:
        simulation = require_owned_simulation(self.database, simulation_id, session_cookie)
        comparisons = (
            self.database.scalars(
                select(OutcomeComparison)
                .where(OutcomeComparison.simulation_id == simulation_id)
                .options(
                    selectinload(OutcomeComparison.metrics),
                    selectinload(OutcomeComparison.reassessment_snapshot).selectinload(
                        ReassessmentSnapshot.changes
                    ),
                )
            )
            .unique()
            .all()
        )
        comparison = next(
            (item for item in comparisons if item.simulation_id == simulation_id),
            None,
        )
        if comparison is None or comparison.id is None:
            raise ApiError(404, "OUTCOME_NOT_FOUND", "결과 검증 정보를 찾을 수 없습니다.")

        baseline = self.database.get(BusinessSnapshot, simulation.business_snapshot_id)
        if baseline is None:
            raise ApiError(409, "BASELINE_NOT_FOUND", "기준 사업 스냅샷을 찾을 수 없습니다.")
        before_values = {
            "MONTHLY_SALES": _decimal(baseline.monthly_net_sales_amount),
            "OPERATING_PROFIT": _decimal(
                baseline.monthly_net_sales_amount - baseline.monthly_expense_amount
            ),
            "ONLINE_ORDER_RATIO": baseline.online_sales_ratio,
            "CASH_AFTER_REPAYMENT": None,
        }
        metrics = tuple(
            sorted(
                comparison.metrics,
                key=lambda item: _metric_order(item.metric_code),
            )
        )
        trends = tuple(
            MetricTrend(
                metric_code=metric.metric_code,
                before_value=before_values.get(metric.metric_code),
                after_value=metric.observed_value,
                unit=metric.unit,
            )
            for metric in metrics
        )
        rows = tuple(
            ComparisonRow(
                metric_code=metric.metric_code,
                label=METRIC_LABELS.get(metric.metric_code, metric.metric_code),
                target_value=metric.target_value,
                break_even_value=metric.break_even_value,
                observed_value=metric.observed_value,
                unit=metric.unit,
                status=metric.status.name,
            )
            for metric in metrics
        )
        changes = tuple(
            sorted(
                comparison.reassessment_snapshot.changes
                if comparison.reassessment_snapshot is not None
                else [],
                key=lambda item: (item.change_type.value, item.bottleneck_type),
            )
        )
        reevaluation = tuple(
            ReevaluationItem(
                bottleneck_type=change.bottleneck_type,
                change_type=change.change_type.name,
                detail=change.detail,
            )
            for change in changes
        )
        new_bottlenecks = tuple(
            NewBottleneckResult(
                bottleneck_type=change.bottleneck_type,
                title=BOTTLENECK_TITLES.get(change.bottleneck_type, change.bottleneck_type),
                detail=change.detail,
            )
            for change in changes
            if change.change_type is BottleneckChangeType.NEW
        )
        return OutcomeResult(
            outcome_id=comparison.id,
            simulation_id=simulation_id,
            overall_status=comparison.status.name,
            trends=trends,
            comparison_rows=rows,
            reevaluation=reevaluation,
            new_bottlenecks=new_bottlenecks,
            created_at=comparison.created_at,
        )

    def _prepare(
        self,
        command: OutcomeCreationCommand,
        session_cookie: str | None,
    ) -> _PreparedOutcome:
        simulation = require_owned_simulation(
            self.database,
            command.simulation_id,
            session_cookie,
        )
        execution = self.database.get(Execution, command.execution_id)
        outcome_data = self.database.get(OutcomeData, command.outcome_data_id)
        self._validate_sources(simulation, execution, outcome_data, command)
        self._require_no_comparison(command.simulation_id)
        if simulation.diagnosis_id is None or simulation.business_snapshot_id is None:
            raise ApiError(409, "SIMULATION_INCOMPLETE", "기준 진단을 찾을 수 없습니다.")
        diagnosis = self.database.get(Diagnosis, simulation.diagnosis_id)
        baseline = self.database.get(BusinessSnapshot, simulation.business_snapshot_id)
        if diagnosis is None or baseline is None:
            raise ApiError(409, "SIMULATION_INCOMPLETE", "기준 진단을 찾을 수 없습니다.")
        if outcome_data is None or outcome_data.observed_business_snapshot_id is None:
            raise ApiError(409, "OUTCOME_DATA_NOT_READY", "사용 가능한 사후 데이터가 아닙니다.")

        previous_ids: dict[str, int | None] = {}
        pre_findings = []
        for bottleneck in diagnosis.bottlenecks:
            ai_type = to_ai_bottleneck_type(bottleneck.bottleneck_type)
            previous_ids.setdefault(ai_type, bottleneck.id)
            pre_findings.append(
                {
                    "bottleneck_type": ai_type,
                    "detail": bottleneck.detail,
                }
            )
        allocation = _allocation_ratios(execution, simulation.loan_amount)
        file_analysis = None
        if outcome_data.source_type is OutcomeDataSourceType.FILE_UPLOAD:
            if outcome_data.dataset is None or simulation.business_id is None:
                raise ApiError(409, "OUTCOME_DATA_NOT_READY", "사용 가능한 사후 데이터가 아닙니다.")
            business = self.database.get(Business, simulation.business_id)
            if business is None:
                raise ApiError(404, "RESOURCE_NOT_FOUND", "요청한 정보를 찾을 수 없습니다.")
            try:
                file_analysis = collect_analysis_input(business, outcome_data.dataset)
            except DiagnosisAnalysisError as error:
                raise ApiError(
                    409,
                    "OUTCOME_DATA_NOT_READY",
                    "사용 가능한 사후 데이터가 아닙니다.",
                ) from error

        break_even_target = None
        selection = getattr(simulation, "selection", None)
        selected_scenario = getattr(selection, "scenario", None)
        if selected_scenario is not None:
            break_even_target = selected_scenario.break_even_additional_revenue
        return _PreparedOutcome(
            simulation_id=simulation.id,
            execution_id=execution.id,
            outcome_data_id=outcome_data.id,
            diagnosis_id=diagnosis.id,
            observed_snapshot_id=outcome_data.observed_business_snapshot_id,
            source_type=outcome_data.source_type,
            allocation=allocation,
            loan_amount=simulation.loan_amount,
            monthly_revenue=baseline.monthly_net_sales_amount,
            annual_interest_rate=simulation.loan_interest_rate,
            term_months=simulation.loan_term_months,
            grace_months=simulation.loan_grace_months,
            repayment_type=simulation.loan_repayment_type,
            baseline_sales=baseline.monthly_net_sales_amount,
            baseline_expense=baseline.monthly_expense_amount,
            baseline_online_ratio=baseline.online_sales_ratio,
            pre_findings=tuple(pre_findings),
            previous_bottleneck_ids=previous_ids,
            break_even_additional_revenue_target=break_even_target,
            raw_pos_data=(dict(outcome_data.raw_pos_data) if outcome_data.raw_pos_data else None),
            file_analysis=file_analysis,
            manual_values=(
                outcome_data.monthly_sales_amount,
                outcome_data.operating_profit_amount,
                outcome_data.online_order_ratio,
                outcome_data.cash_after_repayment_amount,
            ),
        )

    def _validate_sources(
        self,
        simulation: Simulation,
        execution: Execution | None,
        outcome_data: OutcomeData | None,
        command: OutcomeCreationCommand,
    ) -> None:
        if (
            execution is None
            or outcome_data is None
            or execution.simulation_id != command.simulation_id
            or outcome_data.simulation_id != command.simulation_id
            or simulation.id != command.simulation_id
        ):
            raise ApiError(404, "RESOURCE_NOT_FOUND", "요청한 정보를 찾을 수 없습니다.")
        if outcome_data.status not in READY_OUTCOME_DATA_STATUSES:
            raise ApiError(
                409,
                "OUTCOME_DATA_NOT_READY",
                "사용 가능한 사후 데이터가 아닙니다.",
            )

    def _require_no_comparison(self, simulation_id: int) -> None:
        comparisons = self.database.scalars(
            select(OutcomeComparison).where(OutcomeComparison.simulation_id == simulation_id)
        ).all()
        if any(item.simulation_id == simulation_id for item in comparisons):
            raise _duplicate_outcome()

    def _calculate(self, prepared: _PreparedOutcome) -> _CalculatedOutcome:
        financial_request = FinancialProjectionRequest(
            allocation=prepared.allocation,
            loan_amount=prepared.loan_amount,
            monthly_revenue=prepared.monthly_revenue,
            annual_interest_rate=prepared.annual_interest_rate,
            term_months=prepared.term_months,
            grace_months=prepared.grace_months,
            repayment_type=prepared.repayment_type,
        )
        if prepared.source_type is OutcomeDataSourceType.MANUAL_INPUT:
            financial = self.engine.project_financial(financial_request)
            sales, profit, online_ratio, cash = prepared.manual_values
            status = None
            snapshot = {
                "monthly_revenue": sales,
                "operating_profit_amount": profit,
                "online_order_ratio": float(online_ratio) if online_ratio is not None else None,
                "cash_after_repayment_amount": cash,
            }
            changes = _manual_changes(prepared)
        else:
            post_pos_data, comparable = _post_pos_data(prepared)
            result = self.engine.compare(
                OutcomeEngineRequest(
                    **financial_request.__dict__,
                    pre_findings=prepared.pre_findings,
                    post_pos_data=post_pos_data,
                    comparable_bottleneck_types=comparable,
                    break_even_additional_revenue_target=(
                        prepared.break_even_additional_revenue_target
                    ),
                )
            )
            financial = result["post_execution_financial_result"]
            sales, profit, online_ratio, cash = _observed_from_pos(post_pos_data, financial)
            status = _outcome_status_from_ai(result["breakeven_status"].get("status"))
            snapshot = dict(result["next_round_pos_data_snapshot"])
            changes = _changes_from_result(prepared, result)

        metrics = _build_metrics(
            prepared,
            financial,
            sales=sales,
            profit=profit,
            online_ratio=online_ratio,
            cash=cash,
        )
        return _CalculatedOutcome(
            status=status or _outcome_status_from_metrics(metrics),
            metrics=metrics,
            changes=changes,
            next_round_snapshot=snapshot,
        )


def _allocation_ratios(execution: Execution, loan_amount: int) -> dict[str, float]:
    allocation = {}
    for item in execution.allocations:
        key = item.category.value if item.category is not None else f"custom_{item.id}"
        allocation[key] = float(Decimal(item.amount) / Decimal(loan_amount))
    return allocation


def _post_pos_data(
    prepared: _PreparedOutcome,
) -> tuple[dict[str, Any], frozenset[str] | None]:
    if prepared.source_type is OutcomeDataSourceType.MOCK:
        if prepared.raw_pos_data is None:
            raise ApiError(409, "OUTCOME_DATA_NOT_READY", "사용 가능한 사후 데이터가 아닙니다.")
        return dict(prepared.raw_pos_data), None
    analysis = prepared.file_analysis
    if analysis is None:
        raise ApiError(409, "OUTCOME_DATA_NOT_READY", "사용 가능한 사후 데이터가 아닙니다.")
    comparable = set(FILE_COMPARABLE_BOTTLENECKS)
    if analysis.timed_sales_coverage == Decimal(1):
        comparable.add("time_of_day_weakness")
    return (
        {
            "monthly_revenue": analysis.monthly_sales_amount,
            "monthly_cogs": analysis.material_cost_amount,
            "monthly_labor_cost": analysis.labor_cost_amount,
            "avg_daily_customers": analysis.monthly_order_count / 30,
            "time_of_day_sales": {
                f"TMZON_{bucket}_SELNG_AMT": amount
                for bucket, amount in analysis.timed_sales_by_bucket.items()
            },
        },
        frozenset(comparable),
    )


def _observed_from_pos(
    post_pos_data: dict[str, Any],
    financial: dict[str, Any],
) -> tuple[int, int, Decimal | None, int]:
    sales = int(post_pos_data["monthly_revenue"])
    profit = (
        sales
        - int(post_pos_data.get("monthly_cogs", 0))
        - int(post_pos_data.get("monthly_labor_cost", 0))
    )
    online_ratio = None
    online_data = post_pos_data.get("online_data")
    daily_customers = post_pos_data.get("avg_daily_customers")
    if isinstance(online_data, dict) and daily_customers:
        online_ratio = Decimal(str(online_data.get("online_order_count", 0))) / (
            Decimal(str(daily_customers)) * Decimal(30)
        )
    cash = (
        profit
        - int(financial["monthly_loan_payment"])
        - int(financial["additional_fixed_cost_per_month"])
    )
    return sales, profit, online_ratio, cash


def _build_metrics(
    prepared: _PreparedOutcome,
    financial: dict[str, Any],
    *,
    sales: int | None,
    profit: int | None,
    online_ratio: Decimal | None,
    cash: int | None,
) -> tuple[OutcomeComparisonMetric, ...]:
    sales_break_even = _decimal(prepared.baseline_sales)
    sales_target = sales_break_even + _decimal(financial["break_even_additional_revenue"])
    profit_target = _decimal(financial["monthly_loan_payment"]) + _decimal(
        financial["additional_fixed_cost_per_month"]
    )
    online_baseline = prepared.baseline_online_ratio
    online_reference = Decimal("0.20")
    online_target = (
        max(online_baseline, online_reference) if online_baseline is not None else online_reference
    )
    online_break_even = (
        min(online_baseline, online_reference) if online_baseline is not None else online_reference
    )
    cash_target = max(Decimal(), _decimal(financial["remaining_cash_after_payment"]))
    specs = (
        ("MONTHLY_SALES", sales_target, sales_break_even, _optional_decimal(sales), "KRW"),
        ("OPERATING_PROFIT", profit_target, Decimal(), _optional_decimal(profit), "KRW"),
        (
            "ONLINE_ORDER_RATIO",
            online_target,
            online_break_even,
            online_ratio,
            "RATIO",
        ),
        ("CASH_AFTER_REPAYMENT", cash_target, Decimal(), _optional_decimal(cash), "KRW"),
    )
    return tuple(
        OutcomeComparisonMetric(
            metric_code=code,
            target_value=target,
            break_even_value=break_even,
            observed_value=observed,
            unit=unit,
            status=classify_metric(target, break_even, observed),
            note=None,
        )
        for code, target, break_even, observed, unit in specs
    )


def _manual_changes(prepared: _PreparedOutcome) -> tuple[BottleneckChange, ...]:
    return tuple(
        BottleneckChange(
            bottleneck_type=bottleneck_type,
            change_type=BottleneckChangeType.NOT_COMPARABLE,
            previous_bottleneck_id=previous_id,
            current_bottleneck_id=None,
            detail="수동 입력 지표만으로 병목 변화를 판정할 수 없습니다.",
        )
        for bottleneck_type, previous_id in prepared.previous_bottleneck_ids.items()
    )


def _changes_from_result(
    prepared: _PreparedOutcome,
    result: dict[str, Any],
) -> tuple[BottleneckChange, ...]:
    change_specs = (
        ("resolved_bottlenecks", BottleneckChangeType.RESOLVED),
        ("persisted_bottlenecks", BottleneckChangeType.REMAINING),
        ("new_bottlenecks", BottleneckChangeType.NEW),
        ("not_comparable_bottlenecks", BottleneckChangeType.NOT_COMPARABLE),
    )
    details = {
        finding.get("bottleneck_type"): finding.get("detail")
        for finding in result["post_execution_findings"]
        if isinstance(finding, dict)
    }
    changes = []
    for result_key, change_type in change_specs:
        for bottleneck_type in result[result_key]:
            changes.append(
                BottleneckChange(
                    bottleneck_type=bottleneck_type,
                    change_type=change_type,
                    previous_bottleneck_id=(
                        None
                        if change_type is BottleneckChangeType.NEW
                        else prepared.previous_bottleneck_ids.get(bottleneck_type)
                    ),
                    current_bottleneck_id=None,
                    detail=details.get(bottleneck_type),
                )
            )
    return tuple(changes)


def _outcome_status_from_ai(status: object) -> OutcomeStatus:
    return {
        "조건 충족": OutcomeStatus.MET,
        "일부 충족": OutcomeStatus.PARTIALLY_MET,
        "미충족": OutcomeStatus.NOT_MET,
    }.get(status, OutcomeStatus.NOT_COMPARABLE)


def _outcome_status_from_metrics(
    metrics: tuple[OutcomeComparisonMetric, ...],
) -> OutcomeStatus:
    statuses = {metric.status for metric in metrics}
    if statuses == {OutcomeMetricStatus.NOT_COMPARABLE}:
        return OutcomeStatus.NOT_COMPARABLE
    if OutcomeMetricStatus.BELOW_EXPECTED in statuses:
        return OutcomeStatus.NOT_MET
    comparable = statuses - {OutcomeMetricStatus.NOT_COMPARABLE}
    if comparable == {OutcomeMetricStatus.ABOVE_EXPECTED}:
        return OutcomeStatus.MET
    return OutcomeStatus.PARTIALLY_MET


def _metric_order(metric_code: str) -> int:
    return (
        "MONTHLY_SALES",
        "OPERATING_PROFIT",
        "ONLINE_ORDER_RATIO",
        "CASH_AFTER_REPAYMENT",
    ).index(metric_code)


def _decimal(value: int | float | Decimal) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: int | Decimal | None) -> Decimal | None:
    return None if value is None else _decimal(value)


def _duplicate_outcome() -> ApiError:
    return ApiError(409, "OUTCOME_ALREADY_EXISTS", "이미 결과 검증이 완료된 시뮬레이션입니다.")
