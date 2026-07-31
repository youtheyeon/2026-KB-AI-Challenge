# 자금 배분 시뮬레이션의 생성·조회·비교·선택 HTTP 계약을 제공하는 라우터
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from fastapi import APIRouter, Cookie, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.api.routes.businesses import get_db
from app.domain.enums import RepaymentType
from app.services.simulation import SimulationCreationCommand, SimulationService
from app.services.simulation_engine import (
    SimulationEngine,
    get_simulation_engine,
)

router = APIRouter(tags=["simulations"])


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RepaymentTypeRequest(StrEnum):
    EQUAL_PAYMENT = "EQUAL_PAYMENT"
    EQUAL_PRINCIPAL = "EQUAL_PRINCIPAL"
    BULLET_PAYMENT = "BULLET_PAYMENT"


class SimulationCreationRequest(ApiModel):
    diagnosis_id: int = Field(gt=0, alias="diagnosisId")
    loan_amount: int = Field(gt=0, le=9_223_372_036_854_775_807, alias="loanAmount")
    annual_interest_rate: Decimal = Field(
        ge=Decimal(),
        le=Decimal(1),
        alias="annualInterestRate",
    )
    term_months: int = Field(gt=0, le=2_147_483_647, alias="termMonths")
    grace_months: int = Field(ge=0, le=2_147_483_647, alias="graceMonths")
    repayment_type: RepaymentTypeRequest = Field(alias="repaymentType")

    @model_validator(mode="after")
    def validate_grace_period(self) -> Self:
        if self.grace_months >= self.term_months:
            raise ValueError("거치 기간은 전체 상환 기간보다 짧아야 합니다.")
        return self


class SimulationCreatedResponse(ApiModel):
    simulation_id: int = Field(alias="simulationId")
    status: str


class LoanConditionResponse(ApiModel):
    amount: int
    annual_interest_rate: float = Field(alias="annualInterestRate")
    term_months: int = Field(alias="termMonths")
    grace_months: int = Field(alias="graceMonths")
    repayment_type: str = Field(alias="repaymentType")


class AllocationResponse(ApiModel):
    category: str
    ratio: float
    amount: int


class ReasonResponse(ApiModel):
    bottleneck_id: int | None = Field(alias="bottleneckId")
    category: str
    description: str
    source_type: str = Field(alias="sourceType")


class FinancialResultResponse(ApiModel):
    monthly_loan_payment: int | None = Field(alias="monthlyLoanPayment")
    monthly_recurring_cost: int | None = Field(alias="monthlyRecurringCost")
    cash_after_payment: int | None = Field(alias="cashAfterPayment")
    break_even_additional_revenue: int | None = Field(alias="breakEvenAdditionalRevenue")
    required_additional_orders: int | None = Field(alias="requiredAdditionalOrders")
    payback_period_months: int | None = Field(alias="paybackPeriodMonths")
    risk_level: str | None = Field(alias="riskLevel")


class ScenarioResponse(ApiModel):
    scenario_id: int = Field(alias="scenarioId")
    scenario_code: str = Field(alias="scenarioCode")
    strategy_type: str = Field(alias="strategyType")
    title: str
    allocations: list[AllocationResponse]
    reasons: list[ReasonResponse]
    financial_result: FinancialResultResponse = Field(alias="financialResult")
    target_metrics: list[str] = Field(alias="targetMetrics")
    risk_reasons: list[str] = Field(alias="riskReasons")


class SimulationResponse(ApiModel):
    simulation_id: int = Field(alias="simulationId")
    business_id: int = Field(alias="businessId")
    diagnosis_id: int = Field(alias="diagnosisId")
    status: str
    loan_condition: LoanConditionResponse = Field(alias="loanCondition")
    scenarios: list[ScenarioResponse]
    selected_scenario_id: int | None = Field(alias="selectedScenarioId")
    created_at: datetime = Field(alias="createdAt")


class ScenarioComparisonResponse(ApiModel):
    scenario_id: int = Field(alias="scenarioId")
    scenario_code: str = Field(alias="scenarioCode")
    strategy_type: str = Field(alias="strategyType")
    title: str
    allocations: list[AllocationResponse]
    financial_result: FinancialResultResponse = Field(alias="financialResult")
    target_metrics: list[str] = Field(alias="targetMetrics")
    risk_reasons: list[str] = Field(alias="riskReasons")


class SimulationComparisonResponse(ApiModel):
    simulation_id: int = Field(alias="simulationId")
    scenarios: list[ScenarioComparisonResponse]
    recommendation_provided: bool = Field(alias="recommendationProvided")
    disclaimer: str


class ScenarioSelectionRequest(ApiModel):
    scenario_id: int = Field(gt=0, alias="scenarioId")


class ScenarioSelectionResponse(ApiModel):
    simulation_id: int = Field(alias="simulationId")
    selected_scenario_id: int = Field(alias="selectedScenarioId")
    selected_at: datetime = Field(alias="selectedAt")
    locked: bool


def get_simulation_service(
    database: Annotated[Session, Depends(get_db)],
    engine: Annotated[SimulationEngine, Depends(get_simulation_engine)],
) -> SimulationService:
    return SimulationService(database, engine)


@router.post(
    "/api/businesses/{business_id}/simulations",
    response_model=SimulationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_simulation(
    business_id: int,
    request: SimulationCreationRequest,
    service: Annotated[SimulationService, Depends(get_simulation_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> SimulationCreatedResponse:
    return service.create(
        SimulationCreationCommand(
            business_id=business_id,
            diagnosis_id=request.diagnosis_id,
            loan_amount=request.loan_amount,
            annual_interest_rate=request.annual_interest_rate,
            term_months=request.term_months,
            grace_months=request.grace_months,
            repayment_type=RepaymentType[request.repayment_type.value],
        ),
        demo_session_cookie,
    )


@router.get(
    "/api/simulations/{simulation_id}",
    response_model=SimulationResponse,
)
def get_simulation(
    simulation_id: int,
    service: Annotated[SimulationService, Depends(get_simulation_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> SimulationResponse:
    return service.get_result(simulation_id, demo_session_cookie)


@router.get(
    "/api/simulations/{simulation_id}/comparison",
    response_model=SimulationComparisonResponse,
)
def get_simulation_comparison(
    simulation_id: int,
    service: Annotated[SimulationService, Depends(get_simulation_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> SimulationComparisonResponse:
    return service.get_comparison(simulation_id, demo_session_cookie)


@router.post(
    "/api/simulations/{simulation_id}/selection",
    response_model=ScenarioSelectionResponse,
)
def select_simulation_scenario(
    simulation_id: int,
    request: ScenarioSelectionRequest,
    service: Annotated[SimulationService, Depends(get_simulation_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> ScenarioSelectionResponse:
    return service.select_scenario(
        simulation_id,
        request.scenario_id,
        demo_session_cookie,
    )
