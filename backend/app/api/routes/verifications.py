# 결과 검증과 선순환 대시보드의 여섯 HTTP 계약을 제공하는 라우터
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from json import JSONDecodeError
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.api.routes.businesses import get_db
from app.core.errors import ApiError
from app.domain.enums import ExecutionType, OutcomeDataSourceType
from app.services.dashboard import DashboardService
from app.services.outcome import OutcomeCreationCommand, OutcomeService
from app.services.outcome_data import (
    ManualOutcomeMetrics,
    OutcomeDataCreationCommand,
    OutcomeDataService,
    OutcomeFile,
)
from app.services.outcome_engine import OutcomeEngine, get_outcome_engine
from app.services.verification import (
    ExecutionCreationCommand,
    ExecutionItemCommand,
    VerificationService,
)

router = APIRouter(tags=["verifications"])
MAX_BIGINT = 9_223_372_036_854_775_807
MIN_BIGINT = -9_223_372_036_854_775_808


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExecutionModeRequest(StrEnum):
    SAME_AS_A = "SAME_AS_A"
    SAME_AS_B = "SAME_AS_B"
    SAME_AS_C = "SAME_AS_C"
    MIXED = "MIXED"
    CUSTOM = "CUSTOM"


class OutcomeSourceRequest(StrEnum):
    MOCK = "MOCK"
    FILE_UPLOAD = "FILE_UPLOAD"
    MANUAL_INPUT = "MANUAL_INPUT"


class PlanSummaryResponse(ApiModel):
    plan_code: str = Field(alias="planCode")
    title: str


class VerificationTargetResponse(ApiModel):
    simulation_id: int = Field(alias="simulationId")
    saved_at: datetime = Field(alias="savedAt")
    days_elapsed: int = Field(alias="daysElapsed")
    execution_registered: bool = Field(alias="executionRegistered")
    business_name: str = Field(alias="businessName")
    region: str
    loan_amount: int = Field(alias="loanAmount")
    plan_summaries: list[PlanSummaryResponse] = Field(alias="planSummaries")


class VerificationTargetsResponse(ApiModel):
    business_id: int = Field(alias="businessId")
    targets: list[VerificationTargetResponse]


class ExecutionItemRequest(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    amount: int = Field(gt=0, le=MAX_BIGINT)


class ExecutionCreationRequest(ApiModel):
    execution_mode: ExecutionModeRequest = Field(alias="executionMode")
    executed_at: date = Field(alias="executedAt")
    items: list[ExecutionItemRequest] = Field(default_factory=list)
    unused_amount: int = Field(ge=0, le=MAX_BIGINT, alias="unusedAmount")
    note: str | None = Field(default=None, max_length=1000)


class ExecutionCreatedResponse(ApiModel):
    execution_id: int = Field(alias="executionId")
    simulation_id: int = Field(alias="simulationId")
    execution_mode: str = Field(alias="executionMode")
    total_executed_amount: int = Field(alias="totalExecutedAmount")
    saved_at: datetime = Field(alias="savedAt")


class ManualOutcomeMetricsRequest(ApiModel):
    monthly_sales_amount: int = Field(gt=0, le=MAX_BIGINT, alias="monthlySalesAmount")
    operating_profit_amount: int = Field(
        ge=MIN_BIGINT,
        le=MAX_BIGINT,
        alias="operatingProfitAmount",
    )
    online_order_ratio: Decimal = Field(
        ge=Decimal(),
        le=Decimal(1),
        alias="onlineOrderRatio",
    )
    cash_after_repayment_amount: int = Field(
        ge=MIN_BIGINT,
        le=MAX_BIGINT,
        alias="cashAfterRepaymentAmount",
    )


class OutcomeDataJsonRequest(ApiModel):
    source_type: OutcomeSourceRequest = Field(alias="sourceType")
    metrics: ManualOutcomeMetricsRequest | None = None


class OutcomeDataFileRequest(ApiModel):
    source_type: OutcomeSourceRequest = Field(alias="sourceType")
    sales_file: UploadFile = Field(alias="salesFile")
    cost_file: UploadFile = Field(alias="costFile")


class OutcomeDataCreatedResponse(ApiModel):
    outcome_data_id: int = Field(alias="outcomeDataId")
    simulation_id: int = Field(alias="simulationId")
    source_type: str = Field(alias="sourceType")
    status: str
    dataset_id: int = Field(alias="datasetId")


class OutcomeCreationRequest(ApiModel):
    execution_id: int = Field(gt=0, alias="executionId")
    outcome_data_id: int = Field(gt=0, alias="outcomeDataId")


class OutcomeSummaryResponse(ApiModel):
    sales_growth_status: str = Field(alias="salesGrowthStatus")
    online_ratio_status: str = Field(alias="onlineRatioStatus")
    cash_after_repayment_status: str = Field(alias="cashAfterRepaymentStatus")


class OutcomeCreatedResponse(ApiModel):
    outcome_id: int = Field(alias="outcomeId")
    simulation_id: int = Field(alias="simulationId")
    status: str
    summary: OutcomeSummaryResponse
    created_at: datetime = Field(alias="createdAt")


class MetricTrendResponse(ApiModel):
    metric_code: str = Field(alias="metricCode")
    before_value: float | None = Field(alias="beforeValue")
    after_value: float | None = Field(alias="afterValue")
    unit: str


class ComparisonRowResponse(ApiModel):
    metric_code: str = Field(alias="metricCode")
    label: str
    target_value: float | None = Field(alias="targetValue")
    break_even_value: float | None = Field(alias="breakEvenValue")
    observed_value: float | None = Field(alias="observedValue")
    unit: str
    status: str


class ReevaluationResponse(ApiModel):
    bottleneck_type: str = Field(alias="bottleneckType")
    change_type: str = Field(alias="changeType")
    detail: str | None


class NewBottleneckResponse(ApiModel):
    bottleneck_type: str = Field(alias="bottleneckType")
    title: str
    detail: str | None


class OutcomeResultResponse(ApiModel):
    outcome_id: int = Field(alias="outcomeId")
    simulation_id: int = Field(alias="simulationId")
    overall_status: str = Field(alias="overallStatus")
    trends: list[MetricTrendResponse]
    comparison_rows: list[ComparisonRowResponse] = Field(alias="comparisonRows")
    reevaluation: list[ReevaluationResponse]
    new_bottlenecks: list[NewBottleneckResponse] = Field(alias="newBottlenecks")
    created_at: datetime = Field(alias="createdAt")


class DashboardBusinessResponse(ApiModel):
    business_id: int = Field(alias="businessId")
    name: str
    region: str
    industry: str


class LoanStatusResponse(ApiModel):
    loan_amount: int = Field(alias="loanAmount")
    monthly_repayment_amount: int = Field(alias="monthlyRepaymentAmount")
    paid_amount: int = Field(alias="paidAmount")
    estimated_remaining_principal: int = Field(alias="estimatedRemainingPrincipal")
    progress_rate: float = Field(alias="progressRate")
    repayment_data_type: str = Field(alias="repaymentDataType")


class DashboardMetricTrendResponse(MetricTrendResponse):
    simulation_id: int = Field(alias="simulationId")
    status: str
    recorded_at: datetime = Field(alias="recordedAt")


class SelectedPlanResponse(ApiModel):
    scenario_id: int = Field(alias="scenarioId")
    scenario_code: str = Field(alias="scenarioCode")
    title: str


class ExecutionCycleResponse(ApiModel):
    execution_id: int = Field(alias="executionId")
    execution_mode: str = Field(alias="executionMode")
    executed_at: datetime | None = Field(alias="executedAt")
    total_executed_amount: int = Field(alias="totalExecutedAmount")
    unused_amount: int = Field(alias="unusedAmount")


class OutcomeCycleResponse(ApiModel):
    outcome_id: int = Field(alias="outcomeId")
    overall_status: str = Field(alias="overallStatus")
    completed_at: datetime = Field(alias="completedAt")


class CycleHistoryResponse(ApiModel):
    simulation_id: int = Field(alias="simulationId")
    simulated_at: datetime = Field(alias="simulatedAt")
    selected_plan: SelectedPlanResponse | None = Field(alias="selectedPlan")
    execution: ExecutionCycleResponse | None
    outcome: OutcomeCycleResponse


class UnresolvedBottleneckResponse(ApiModel):
    bottleneck_type: str = Field(alias="bottleneckType")
    change_type: str = Field(alias="changeType")
    detail: str | None


class DashboardResponse(ApiModel):
    business: DashboardBusinessResponse
    loan_status: LoanStatusResponse | None = Field(alias="loanStatus")
    metric_trends: list[DashboardMetricTrendResponse] = Field(alias="metricTrends")
    cycle_histories: list[CycleHistoryResponse] = Field(alias="cycleHistories")
    unresolved_bottlenecks: list[UnresolvedBottleneckResponse] = Field(
        alias="unresolvedBottlenecks"
    )
    next_initial_conditions: dict | None = Field(alias="nextInitialConditions")


def get_verification_service(
    database: Annotated[Session, Depends(get_db)],
) -> VerificationService:
    return VerificationService(database)


def get_outcome_data_service(
    database: Annotated[Session, Depends(get_db)],
    engine: Annotated[OutcomeEngine, Depends(get_outcome_engine)],
) -> OutcomeDataService:
    return OutcomeDataService(database, engine)


def get_outcome_service(
    database: Annotated[Session, Depends(get_db)],
    engine: Annotated[OutcomeEngine, Depends(get_outcome_engine)],
) -> OutcomeService:
    return OutcomeService(database, engine)


def get_dashboard_service(
    database: Annotated[Session, Depends(get_db)],
) -> DashboardService:
    return DashboardService(database)


@router.get(
    "/api/businesses/{business_id}/verification-targets",
    response_model=VerificationTargetsResponse,
)
def list_verification_targets(
    business_id: int,
    service: Annotated[VerificationService, Depends(get_verification_service)],
    include_completed: Annotated[bool, Query(alias="includeCompleted")] = False,
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> VerificationTargetsResponse:
    return service.list_targets(
        business_id,
        include_completed,
        demo_session_cookie,
    )


@router.post(
    "/api/simulations/{simulation_id}/executions",
    response_model=ExecutionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_execution(
    simulation_id: int,
    request: ExecutionCreationRequest,
    service: Annotated[VerificationService, Depends(get_verification_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> ExecutionCreatedResponse:
    return service.create_execution(
        ExecutionCreationCommand(
            simulation_id=simulation_id,
            mode=ExecutionType[request.execution_mode.value],
            executed_at=request.executed_at,
            items=tuple(
                ExecutionItemCommand(name=item.name, amount=item.amount) for item in request.items
            ),
            unused_amount=request.unused_amount,
            note=request.note,
        ),
        demo_session_cookie,
    )


OUTCOME_DATA_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "oneOf": [
                        {
                            "type": "object",
                            "required": ["sourceType"],
                            "properties": {"sourceType": {"type": "string", "enum": ["MOCK"]}},
                        },
                        {
                            "type": "object",
                            "required": ["sourceType", "metrics"],
                            "properties": {
                                "sourceType": {
                                    "type": "string",
                                    "enum": ["MANUAL_INPUT"],
                                },
                                "metrics": {
                                    "type": "object",
                                    "required": [
                                        "monthlySalesAmount",
                                        "operatingProfitAmount",
                                        "onlineOrderRatio",
                                        "cashAfterRepaymentAmount",
                                    ],
                                    "properties": {
                                        "monthlySalesAmount": {
                                            "type": "integer",
                                            "minimum": 1,
                                        },
                                        "operatingProfitAmount": {"type": "integer"},
                                        "onlineOrderRatio": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },
                                        "cashAfterRepaymentAmount": {"type": "integer"},
                                    },
                                },
                            },
                        },
                    ]
                }
            },
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["sourceType", "salesFile", "costFile"],
                    "properties": {
                        "sourceType": {"type": "string", "enum": ["FILE_UPLOAD"]},
                        "salesFile": {"type": "string", "format": "binary"},
                        "costFile": {"type": "string", "format": "binary"},
                    },
                }
            },
        },
    }
}


@router.post(
    "/api/simulations/{simulation_id}/outcome-data",
    response_model=OutcomeDataCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=OUTCOME_DATA_OPENAPI,
)
async def create_outcome_data(
    simulation_id: int,
    request: Request,
    service: Annotated[OutcomeDataService, Depends(get_outcome_data_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> OutcomeDataCreatedResponse:
    content_type = request.headers.get("content-type", "").lower()
    try:
        if content_type.startswith("application/json"):
            payload = OutcomeDataJsonRequest.model_validate(await request.json())
            command = _json_outcome_command(simulation_id, payload)
        elif content_type.startswith("multipart/form-data"):
            form = await request.form()
            payload = OutcomeDataFileRequest.model_validate(
                {
                    "sourceType": form.get("sourceType"),
                    "salesFile": form.get("salesFile"),
                    "costFile": form.get("costFile"),
                }
            )
            command = await _file_outcome_command(simulation_id, payload)
        else:
            raise ApiError(
                400,
                "UNSUPPORTED_CONTENT_TYPE",
                "지원하지 않는 Content-Type입니다.",
            )
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    except JSONDecodeError as error:
        raise RequestValidationError(
            [{"type": "json_invalid", "loc": ("body",), "msg": "Invalid JSON"}]
        ) from error
    return service.create(command, demo_session_cookie)


@router.post(
    "/api/simulations/{simulation_id}/outcomes",
    response_model=OutcomeCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_outcome(
    simulation_id: int,
    request: OutcomeCreationRequest,
    service: Annotated[OutcomeService, Depends(get_outcome_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> OutcomeCreatedResponse:
    return service.create(
        OutcomeCreationCommand(
            simulation_id=simulation_id,
            execution_id=request.execution_id,
            outcome_data_id=request.outcome_data_id,
        ),
        demo_session_cookie,
    )


@router.get(
    "/api/simulations/{simulation_id}/outcomes",
    response_model=OutcomeResultResponse,
)
def get_outcome(
    simulation_id: int,
    service: Annotated[OutcomeService, Depends(get_outcome_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> OutcomeResultResponse:
    return service.get_result(simulation_id, demo_session_cookie)


@router.get(
    "/api/businesses/{business_id}/dashboard",
    response_model=DashboardResponse,
)
def get_dashboard(
    business_id: int,
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> DashboardResponse:
    return service.get(business_id, demo_session_cookie)


def _json_outcome_command(
    simulation_id: int,
    payload: OutcomeDataJsonRequest,
) -> OutcomeDataCreationCommand:
    if payload.source_type is OutcomeSourceRequest.FILE_UPLOAD:
        raise ApiError(
            400,
            "INVALID_OUTCOME_SOURCE",
            "FILE_UPLOAD은 multipart/form-data로 요청해야 합니다.",
        )
    metrics = None
    if payload.metrics is not None:
        metrics = ManualOutcomeMetrics(
            monthly_sales_amount=payload.metrics.monthly_sales_amount,
            operating_profit_amount=payload.metrics.operating_profit_amount,
            online_order_ratio=payload.metrics.online_order_ratio,
            cash_after_repayment_amount=payload.metrics.cash_after_repayment_amount,
        )
    return OutcomeDataCreationCommand(
        simulation_id=simulation_id,
        source_type=OutcomeDataSourceType[payload.source_type.value],
        metrics=metrics,
    )


async def _file_outcome_command(
    simulation_id: int,
    payload: OutcomeDataFileRequest,
) -> OutcomeDataCreationCommand:
    if payload.source_type is not OutcomeSourceRequest.FILE_UPLOAD:
        raise ApiError(
            400,
            "INVALID_OUTCOME_SOURCE",
            "파일 요청의 sourceType은 FILE_UPLOAD이어야 합니다.",
        )
    _validate_xlsx_name(payload.sales_file.filename)
    _validate_xlsx_name(payload.cost_file.filename)
    return OutcomeDataCreationCommand(
        simulation_id=simulation_id,
        source_type=OutcomeDataSourceType.FILE_UPLOAD,
        sales_file=OutcomeFile(
            filename=payload.sales_file.filename,
            contents=await payload.sales_file.read(),
        ),
        expense_file=OutcomeFile(
            filename=payload.cost_file.filename,
            contents=await payload.cost_file.read(),
        ),
    )


def _validate_xlsx_name(filename: str | None) -> None:
    if filename is None or len(filename) > 255 or not filename.lower().endswith(".xlsx"):
        raise ApiError(400, "OUTCOME_FILE_INVALID", "xlsx 파일이 필요합니다.")
