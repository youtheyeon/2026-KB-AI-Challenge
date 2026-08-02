# 완료 진단으로 자금 배분 시뮬레이션을 생성하고 전체 결과를 원자적으로 저장하는 서비스
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.diagnosis import Diagnosis
from app.domain.enums import (
    AllocationCategory,
    BottleneckChangeType,
    BottleneckSeverity,
    DatasetStatus,
    DataSourceType,
    DiagnosisStatus,
    RepaymentType,
    RiskLevel,
    ScenarioCode,
)
from app.domain.execution import Execution
from app.domain.outcome import OutcomeComparison, ReassessmentSnapshot
from app.domain.simulation import (
    LoanCondition,
    Scenario,
    ScenarioAllocation,
    ScenarioFinancialResult,
    ScenarioReason,
    ScenarioSelection,
    Simulation,
)
from app.services.ai_contract import to_ai_bottleneck_type
from app.services.simulation_engine import (
    SimulationEngine,
    SimulationEngineRequest,
    SimulationGenerationError,
)

SEVERITY_MAP = {
    BottleneckSeverity.MILD: "경미",
    BottleneckSeverity.CLEAR: "뚜렷",
    BottleneckSeverity.SEVERE: "심각",
}
CONFIDENCE_MAP = {
    DataSourceType.PUBLIC_DATA: "높음",
    DataSourceType.SYNTHETIC_SALES: "낮음",
    DataSourceType.SYNTHETIC_EXPENSE: "낮음",
    DataSourceType.SYNTHETIC_ONLINE_SALES: "높음",
    DataSourceType.BENCHMARK: "높음",
    DataSourceType.DOMAIN_ASSUMPTION: "보통",
}
TITLE_MAP = {
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
STRATEGY_MAP = {
    ScenarioCode.A: "BOTTLENECK_FOCUSED",
    ScenarioCode.B: "DIAGNOSIS_PROPORTIONAL",
    ScenarioCode.C: "EQUAL_DISTRIBUTION",
}
RISK_MAP = {
    "낮음": RiskLevel.LOW,
    "중간": RiskLevel.MEDIUM,
    "높음": RiskLevel.HIGH,
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
}
NEUTRAL_DISCLAIMER = (
    "AI는 특정 시나리오를 추천하거나 성과를 보장하지 않습니다. "
    "진단 근거와 재무 계산을 비교해 사용자가 직접 판단해야 합니다."
)


@dataclass(frozen=True)
class SimulationCreationCommand:
    business_id: int
    diagnosis_id: int
    loan_amount: int
    annual_interest_rate: Decimal
    term_months: int
    grace_months: int
    repayment_type: RepaymentType


@dataclass(frozen=True)
class SimulationCreated:
    simulation_id: int
    status: str


@dataclass(frozen=True)
class LoanConditionResult:
    amount: int
    annual_interest_rate: Decimal
    term_months: int
    grace_months: int
    repayment_type: str


@dataclass(frozen=True)
class AllocationResult:
    category: str
    ratio: Decimal
    amount: int


@dataclass(frozen=True)
class ReasonResult:
    bottleneck_id: int | None
    category: str
    description: str
    source_type: str


@dataclass(frozen=True)
class FinancialResult:
    monthly_loan_payment: int | None
    monthly_recurring_cost: int | None
    cash_after_payment: int | None
    break_even_additional_revenue: int | None
    required_additional_orders: int | None
    payback_period_months: int | None
    risk_level: str | None


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: int
    scenario_code: str
    strategy_type: str
    title: str
    allocations: tuple[AllocationResult, ...]
    reasons: tuple[ReasonResult, ...]
    financial_result: FinancialResult
    target_metrics: tuple[str, ...]
    risk_reasons: tuple[str, ...]
    allocation_rationale: str | None
    scb_growth_outlook: str | None


@dataclass(frozen=True)
class SimulationResult:
    simulation_id: int
    business_id: int
    diagnosis_id: int
    status: str
    loan_condition: LoanConditionResult
    scenarios: tuple[ScenarioResult, ...]
    selected_scenario_id: int | None
    created_at: datetime


@dataclass(frozen=True)
class ScenarioComparison:
    scenario_id: int
    scenario_code: str
    strategy_type: str
    title: str
    allocations: tuple[AllocationResult, ...]
    financial_result: FinancialResult
    target_metrics: tuple[str, ...]
    risk_reasons: tuple[str, ...]
    allocation_rationale: str | None
    scb_growth_outlook: str | None


@dataclass(frozen=True)
class SimulationComparison:
    simulation_id: int
    scenarios: tuple[ScenarioComparison, ...]
    recommendation_provided: bool
    disclaimer: str


@dataclass(frozen=True)
class ScenarioSelected:
    simulation_id: int
    selected_scenario_id: int
    selected_at: datetime
    locked: bool


@dataclass(frozen=True)
class _StoredBottleneck:
    id: int
    bottleneck_type: str
    detail: str
    related_categories: tuple[str, ...]


@dataclass(frozen=True)
class _PreparedSimulation:
    business_id: int
    dataset_id: int
    diagnosis_id: int
    business_snapshot_id: int
    public_data_reference_date: date
    engine_request: SimulationEngineRequest
    bottlenecks: tuple[_StoredBottleneck, ...]


class SimulationService:
    def __init__(self, database: Session, engine: SimulationEngine) -> None:
        self.database = database
        self.engine = engine

    def create(
        self,
        command: SimulationCreationCommand,
        session_cookie: str | None,
    ) -> SimulationCreated:
        try:
            prepared = self._prepare(command, session_cookie)
        except ApiError:
            self.database.rollback()
            raise
        self.database.rollback()

        try:
            generated = self.engine.run(prepared.engine_request)
            simulation = self._to_simulation(command, prepared, generated)
            simulation.validate_scenarios()
        except (KeyError, TypeError, ValueError, SimulationGenerationError) as error:
            raise ApiError(
                502,
                "SIMULATION_GENERATION_FAILED",
                "시뮬레이션 결과 생성에 실패했습니다.",
            ) from error

        with self.database.begin():
            self.database.add(simulation)
            self.database.flush()
            if simulation.id is None:
                raise RuntimeError("시뮬레이션 식별자가 생성되지 않았습니다.")
            simulation_id = simulation.id

        return SimulationCreated(simulation_id=simulation_id, status="COMPLETED")

    def get_result(
        self,
        simulation_id: int,
        session_cookie: str | None,
    ) -> SimulationResult:
        simulation = self._get_owned_simulation(simulation_id, session_cookie)
        if (
            simulation.id is None
            or simulation.business_id is None
            or simulation.diagnosis_id is None
            or simulation.created_at is None
        ):
            raise RuntimeError("저장된 시뮬레이션 식별 정보가 없습니다.")

        selected_scenario_id = (
            simulation.selection.scenario_id if simulation.selection is not None else None
        )
        return SimulationResult(
            simulation_id=simulation.id,
            business_id=simulation.business_id,
            diagnosis_id=simulation.diagnosis_id,
            status=simulation.status.upper(),
            loan_condition=LoanConditionResult(
                amount=simulation.loan_amount,
                annual_interest_rate=simulation.loan_interest_rate,
                term_months=simulation.loan_term_months,
                grace_months=simulation.loan_grace_months,
                repayment_type=simulation.loan_repayment_type.name,
            ),
            scenarios=tuple(
                _project_scenario(scenario)
                for scenario in sorted(simulation.scenarios, key=lambda item: item.code.value)
            ),
            selected_scenario_id=selected_scenario_id,
            created_at=simulation.created_at,
        )

    def get_comparison(
        self,
        simulation_id: int,
        session_cookie: str | None,
    ) -> SimulationComparison:
        result = self.get_result(simulation_id, session_cookie)
        return SimulationComparison(
            simulation_id=result.simulation_id,
            scenarios=tuple(
                ScenarioComparison(
                    scenario_id=scenario.scenario_id,
                    scenario_code=scenario.scenario_code,
                    strategy_type=scenario.strategy_type,
                    title=scenario.title,
                    allocations=scenario.allocations,
                    financial_result=scenario.financial_result,
                    target_metrics=scenario.target_metrics,
                    risk_reasons=scenario.risk_reasons,
                    allocation_rationale=scenario.allocation_rationale,
                    scb_growth_outlook=scenario.scb_growth_outlook,
                )
                for scenario in result.scenarios
            ),
            recommendation_provided=False,
            disclaimer=NEUTRAL_DISCLAIMER,
        )

    def select_scenario(
        self,
        simulation_id: int,
        scenario_id: int,
        session_cookie: str | None,
    ) -> ScenarioSelected:
        with self.database.begin():
            simulation = self._get_owned_simulation(simulation_id, session_cookie)
            scenario = self.database.get(Scenario, scenario_id)
            if scenario is None or scenario.simulation_id != simulation.id or scenario.id is None:
                raise ApiError(
                    400,
                    "SCENARIO_NOT_IN_SIMULATION",
                    "선택한 시나리오가 해당 시뮬레이션에 속하지 않습니다.",
                )

            selected_at = datetime.now(UTC)
            selection = simulation.selection
            if selection is None:
                selection = ScenarioSelection(
                    simulation_id=simulation.id,
                    scenario_id=scenario.id,
                    selected_at=selected_at,
                    locked=False,
                )
                simulation.selection = selection
                self.database.add(selection)
            else:
                try:
                    selection.change_scenario(scenario.id)
                except ValueError as error:
                    raise ApiError(
                        409,
                        "SELECTION_LOCKED",
                        "집행 등록 후에는 시나리오 선택을 변경할 수 없습니다.",
                    ) from error
                selection.selected_at = selected_at
            self.database.flush()

            return ScenarioSelected(
                simulation_id=simulation.id,
                selected_scenario_id=selection.scenario_id,
                selected_at=selection.selected_at,
                locked=selection.locked,
            )

    def _get_owned_simulation(
        self,
        simulation_id: int,
        session_cookie: str | None,
    ) -> Simulation:
        simulation = self.database.get(Simulation, simulation_id)
        session_id = _parse_session_id(session_cookie)
        business = (
            self.database.get(Business, simulation.business_id) if simulation is not None else None
        )
        if (
            simulation is None
            or business is None
            or session_id is None
            or business.demo_session_id != session_id
        ):
            raise ApiError(404, "RESOURCE_NOT_FOUND", "요청한 자원을 찾을 수 없습니다.")
        return simulation

    def _prepare(
        self,
        command: SimulationCreationCommand,
        session_cookie: str | None,
    ) -> _PreparedSimulation:
        business = self.database.get(Business, command.business_id)
        session_id = _parse_session_id(session_cookie)
        if business is None or session_id is None or business.demo_session_id != session_id:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "요청한 자원을 찾을 수 없습니다.")

        diagnosis = self.database.get(Diagnosis, command.diagnosis_id)
        if diagnosis is None or diagnosis.business_id != command.business_id:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "요청한 자원을 찾을 수 없습니다.")
        if diagnosis.status != DiagnosisStatus.COMPLETED:
            raise ApiError(
                409,
                "DIAGNOSIS_NOT_COMPLETED",
                "완료된 진단만 시뮬레이션에 사용할 수 있습니다.",
            )
        if (
            diagnosis.dataset is None
            or diagnosis.dataset.business_id != command.business_id
            or diagnosis.dataset.status != DatasetStatus.READY
        ):
            raise ApiError(
                409,
                "DATASET_NOT_READY",
                "준비된 데이터셋만 시뮬레이션에 사용할 수 있습니다.",
            )

        snapshot = diagnosis.business_snapshot
        public_snapshot = diagnosis.public_data_snapshot
        average_daily_customers = (
            round(snapshot.monthly_order_count / 30)
            if snapshot.monthly_order_count and snapshot.monthly_order_count > 0
            else 0
        )
        findings = tuple(_to_finding(bottleneck) for bottleneck in diagnosis.bottlenecks)
        business_history = _build_business_history(self.database, command.business_id)
        stored_bottlenecks = tuple(
            _StoredBottleneck(
                id=bottleneck.id,
                bottleneck_type=bottleneck.bottleneck_type,
                detail=bottleneck.detail,
                related_categories=tuple(bottleneck.related_categories),
            )
            for bottleneck in diagnosis.bottlenecks
        )

        return _PreparedSimulation(
            business_id=command.business_id,
            dataset_id=diagnosis.dataset.id,
            diagnosis_id=diagnosis.id,
            business_snapshot_id=snapshot.id,
            public_data_reference_date=public_snapshot.reference_date,
            engine_request=SimulationEngineRequest(
                findings=findings,
                business_history=business_history,
                loan_amount=command.loan_amount,
                annual_interest_rate=command.annual_interest_rate,
                term_months=command.term_months,
                grace_months=command.grace_months,
                repayment_type=command.repayment_type,
                baseline_monthly_revenue=snapshot.monthly_net_sales_amount,
                average_daily_customers=average_daily_customers,
            ),
            bottlenecks=stored_bottlenecks,
        )

    def _to_simulation(
        self,
        command: SimulationCreationCommand,
        prepared: _PreparedSimulation,
        generated: dict[str, Any],
    ) -> Simulation:
        versions = generated.get("versions", {})
        return Simulation(
            business_id=prepared.business_id,
            dataset_id=prepared.dataset_id,
            diagnosis_id=prepared.diagnosis_id,
            business_snapshot_id=prepared.business_snapshot_id,
            loan_condition=LoanCondition(
                amount=command.loan_amount,
                annual_interest_rate=command.annual_interest_rate,
                term_months=command.term_months,
                grace_months=command.grace_months,
                repayment_type=command.repayment_type,
            ),
            status="completed",
            allocation_generator_version=versions.get("allocation_generator_version"),
            calculation_version=versions.get("calculation_version"),
            prompt_version=versions.get("prompt_version"),
            public_data_reference_date=prepared.public_data_reference_date,
            scenarios=[
                _to_scenario(item, prepared.bottlenecks) for item in generated["scenario_results"]
            ],
        )


def _parse_session_id(session_cookie: str | None) -> UUID | None:
    try:
        return UUID(session_cookie) if session_cookie else None
    except ValueError:
        return None


def _to_finding(bottleneck) -> dict:
    bottleneck_type = to_ai_bottleneck_type(bottleneck.bottleneck_type)
    evidence = bottleneck.evidence_description
    suggested_category = next(
        (
            category
            for category in bottleneck.related_categories
            if category in {item.value for item in AllocationCategory}
        ),
        None,
    )
    return {
        "bottleneck_type": bottleneck_type,
        "title": TITLE_MAP.get(bottleneck_type, bottleneck_type),
        "detail": bottleneck.detail,
        "comparison_chip": bottleneck.detail,
        "evidence_source": evidence,
        "methodology": evidence,
        "severity": SEVERITY_MAP[bottleneck.severity],
        "confidence_badge": CONFIDENCE_MAP.get(bottleneck.evidence_source_type, "보통"),
        "suggested_category": suggested_category,
    }


def _build_business_history(
    database: Session,
    business_id: int,
) -> tuple[dict, ...]:
    simulations = database.scalars(
        select(Simulation).where(Simulation.business_id == business_id)
    ).all()
    simulations_by_id = {
        simulation.id: simulation
        for simulation in simulations
        if simulation.id is not None
        and simulation.business_id == business_id
        and simulation.status.upper() == "COMPLETED"
    }
    if not simulations_by_id:
        return ()

    simulation_ids = list(simulations_by_id)
    comparisons = (
        database.scalars(
            select(OutcomeComparison)
            .where(OutcomeComparison.simulation_id.in_(simulation_ids))
            .options(
                selectinload(OutcomeComparison.reassessment_snapshot).selectinload(
                    ReassessmentSnapshot.changes
                )
            )
        )
        .unique()
        .all()
    )
    executions = (
        database.scalars(
            select(Execution)
            .where(Execution.simulation_id.in_(simulation_ids))
            .options(selectinload(Execution.allocations))
        )
        .unique()
        .all()
    )
    executions_by_simulation = {
        execution.simulation_id: execution
        for execution in executions
        if execution.simulation_id in simulations_by_id
    }

    completed = sorted(
        (
            comparison
            for comparison in comparisons
            if comparison.simulation_id in simulations_by_id
            and isinstance(comparison.next_round_pos_data_snapshot, dict)
            and comparison.reassessment_snapshot is not None
        ),
        key=lambda comparison: (
            comparison.created_at or datetime.min.replace(tzinfo=UTC),
            comparison.id or 0,
        ),
    )
    history = []
    for round_number, comparison in enumerate(completed, start=1):
        simulation = simulations_by_id[comparison.simulation_id]
        execution = executions_by_simulation.get(comparison.simulation_id)
        if execution is None:
            continue
        findings = [
            {
                "bottleneck_type": to_ai_bottleneck_type(change.bottleneck_type),
                "detail": change.detail,
            }
            for change in comparison.reassessment_snapshot.changes
            if change.change_type
            in {
                BottleneckChangeType.REMAINING,
                BottleneckChangeType.NEW,
            }
        ]
        allocation = {
            item.category.value: float(Decimal(item.amount) / Decimal(simulation.loan_amount))
            for item in execution.allocations
            if item.category is not None
        }
        history.append(
            {
                "round": round_number,
                "findings": findings,
                "pos_data": dict(comparison.next_round_pos_data_snapshot),
                "selected_allocation": allocation,
            }
        )
    return tuple(history)


def _to_scenario(
    generated: dict[str, Any],
    bottlenecks: tuple[_StoredBottleneck, ...],
) -> Scenario:
    code = ScenarioCode(generated["scenario_id"])
    ratios = {
        AllocationCategory(category): Decimal(str(ratio))
        for category, ratio in generated["allocation"].items()
    }
    amounts = {
        AllocationCategory(category): amount
        for category, amount in generated["allocation_amounts_won"].items()
    }
    allocations = [
        ScenarioAllocation(category=category, ratio=ratios[category], amount=amounts[category])
        for category in AllocationCategory
    ]
    financial = generated["financial_result"]
    risk_reasons = [financial["risk_level_basis"]]
    warning = financial.get("loan_scale_warning", {}).get("message")
    if warning:
        risk_reasons.append(warning)

    scenario = Scenario(
        code=code,
        strategy_type=STRATEGY_MAP[code],
        title=generated["label"],
        total_amount=generated["loan_amount"],
        financial_result=ScenarioFinancialResult(
            monthly_loan_payment=financial["monthly_loan_payment"],
            monthly_recurring_cost=financial["additional_fixed_cost_per_month"],
            cash_after_payment=financial["remaining_cash_after_payment"],
            break_even_additional_revenue=financial["break_even_additional_revenue"],
            required_additional_orders=financial["required_additional_orders"],
            payback_period_months=financial["payback_period"]["months"],
            risk_level=RISK_MAP[financial["risk_level"]],
        ),
        target_metrics=list(generated.get("target_metrics", [])),
        risk_reasons=risk_reasons,
        allocation_rationale=generated.get("allocation_rationale"),
        scb_growth_outlook=generated.get("scb_growth_outlook"),
        allocations=allocations,
        reasons=[],
    )
    scenario.reasons.extend(_calculated_reasons(bottlenecks, ratios))
    return scenario


def _calculated_reasons(
    bottlenecks: tuple[_StoredBottleneck, ...],
    ratios: dict[AllocationCategory, Decimal],
) -> list[ScenarioReason]:
    reasons = []
    for bottleneck in bottlenecks:
        for category_text in bottleneck.related_categories:
            try:
                category = AllocationCategory(category_text)
            except ValueError:
                continue
            if ratios[category] > Decimal("0.05"):
                reasons.append(
                    ScenarioReason(
                        bottleneck_id=bottleneck.id,
                        category=category,
                        description=f"{bottleneck.detail}에 대응하는 배분입니다.",
                        source_type=DataSourceType.CALCULATED,
                    )
                )
    return reasons


def _project_scenario(scenario: Scenario) -> ScenarioResult:
    if scenario.id is None:
        raise RuntimeError("저장된 시나리오 식별자가 없습니다.")
    allocation_order = {category: index for index, category in enumerate(AllocationCategory)}
    return ScenarioResult(
        scenario_id=scenario.id,
        scenario_code=scenario.code.name,
        strategy_type=scenario.strategy_type,
        title=scenario.title,
        allocations=tuple(
            AllocationResult(
                category=allocation.category.name,
                ratio=allocation.ratio,
                amount=allocation.amount,
            )
            for allocation in sorted(
                scenario.allocations,
                key=lambda item: allocation_order[item.category],
            )
        ),
        reasons=tuple(
            ReasonResult(
                bottleneck_id=reason.bottleneck_id,
                category=reason.category.name,
                description=reason.description,
                source_type=reason.source_type.name,
            )
            for reason in scenario.reasons
        ),
        financial_result=FinancialResult(
            monthly_loan_payment=scenario.monthly_loan_payment,
            monthly_recurring_cost=scenario.monthly_recurring_cost,
            cash_after_payment=scenario.cash_after_payment,
            break_even_additional_revenue=scenario.break_even_additional_revenue,
            required_additional_orders=scenario.required_additional_orders,
            payback_period_months=scenario.payback_period_months,
            risk_level=scenario.risk_level.name if scenario.risk_level is not None else None,
        ),
        target_metrics=tuple(scenario.target_metrics),
        risk_reasons=tuple(scenario.risk_reasons),
        allocation_rationale=scenario.allocation_rationale,
        scb_growth_outlook=scenario.scb_growth_outlook,
    )
