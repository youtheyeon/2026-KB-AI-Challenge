# 완료 진단으로 자금 배분 시뮬레이션을 생성하고 전체 결과를 원자적으로 저장하는 서비스
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.diagnosis import Diagnosis
from app.domain.enums import (
    AllocationCategory,
    BottleneckSeverity,
    DatasetStatus,
    DataSourceType,
    DiagnosisStatus,
    RepaymentType,
    RiskLevel,
    ScenarioCode,
)
from app.domain.simulation import (
    LoanCondition,
    Scenario,
    ScenarioAllocation,
    ScenarioFinancialResult,
    ScenarioReason,
    Simulation,
)
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
        "bottleneck_type": bottleneck.bottleneck_type,
        "title": TITLE_MAP.get(bottleneck.bottleneck_type, bottleneck.bottleneck_type),
        "detail": bottleneck.detail,
        "comparison_chip": bottleneck.detail,
        "evidence_source": evidence,
        "methodology": evidence,
        "severity": SEVERITY_MAP[bottleneck.severity],
        "confidence_badge": CONFIDENCE_MAP.get(bottleneck.evidence_source_type, "보통"),
        "suggested_category": suggested_category,
    }


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
        allocations=allocations,
        reasons=[],
    )
    scenario.reasons.extend(_calculated_reasons(bottlenecks, ratios))

    rationale = generated.get("allocation_rationale")
    if rationale:
        largest_category = max(AllocationCategory, key=ratios.__getitem__)
        scenario.reasons.append(
            ScenarioReason(
                bottleneck_id=None,
                category=largest_category,
                description=rationale,
                source_type=DataSourceType.AI_GENERATED_TEXT,
            )
        )
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
