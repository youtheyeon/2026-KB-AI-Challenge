# 사업 상태 분석과 병목 진단의 비동기 실행·조회 API를 제공하는 라우터
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.routes.businesses import get_db
from app.domain.business import Business
from app.domain.dataset import Dataset
from app.domain.demo_session import DemoSession
from app.domain.diagnosis import Bottleneck, Diagnosis
from app.domain.enums import (
    BottleneckSeverity,
    DatasetStatus,
    DataSourceType,
    DemoSessionStatus,
    DiagnosisStatus,
)
from app.services.diagnosis_service import create_running_diagnosis, run_diagnosis


class DiagnosisRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        original_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except RequestValidationError:
                return error_response(
                    status.HTTP_400_BAD_REQUEST,
                    "INVALID_REQUEST",
                    "요청값이 올바르지 않습니다.",
                )

        return route_handler


router = APIRouter(tags=["diagnoses"], route_class=DiagnosisRoute)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class DiagnosisStartRequest(CamelModel):
    dataset_id: int = Field(alias="datasetId", gt=0)


class DiagnosisStartResponse(CamelModel):
    diagnosis_id: int = Field(alias="diagnosisId")
    business_id: int = Field(alias="businessId")
    status: Literal["RUNNING"]
    created_at: datetime = Field(alias="createdAt")


class FinancialMetricsResponse(CamelModel):
    monthly_sales_amount: int = Field(alias="monthlySalesAmount")
    operating_profit_rate: float = Field(alias="operatingProfitRate")
    material_cost_rate: float = Field(alias="materialCostRate")
    cash_surplus_amount: int = Field(alias="cashSurplusAmount")


class ActivityMetricsResponse(CamelModel):
    monthly_order_count: int = Field(alias="monthlyOrderCount")
    online_sales_ratio: float | None = Field(alias="onlineSalesRatio")
    employee_count: int = Field(alias="employeeCount")


class CommercialMetricsResponse(CamelModel):
    floating_population_growth_rate: float | None = Field(alias="floatingPopulationGrowthRate")
    sales_compared_to_peer_rate: float = Field(alias="salesComparedToPeerRate")


class BottleneckResponse(CamelModel):
    code: str
    title: str
    priority: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    detail: str
    evidence: str


class DiagnosisResultResponse(CamelModel):
    diagnosis_id: int = Field(alias="diagnosisId")
    status: Literal["RUNNING", "COMPLETED", "FAILED"]
    financial_metrics: FinancialMetricsResponse | None = Field(
        default=None,
        alias="financialMetrics",
    )
    activity_metrics: ActivityMetricsResponse | None = Field(
        default=None,
        alias="activityMetrics",
    )
    commercial_metrics: CommercialMetricsResponse | None = Field(
        default=None,
        alias="commercialMetrics",
    )
    bottlenecks: list[BottleneckResponse] | None = None


@router.post(
    "/api/businesses/{business_id}/diagnoses",
    response_model=DiagnosisStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_diagnosis(
    business_id: int,
    request: DiagnosisStartRequest,
    background_tasks: BackgroundTasks,
    database: Annotated[Session, Depends(get_db)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> DiagnosisStartResponse | JSONResponse:
    with database.begin():
        business = database.get(Business, business_id)
        dataset = database.get(
            Dataset,
            request.dataset_id,
            with_for_update=True,
        )
        if (
            business is None
            or not _owns_active_session(database, business, demo_session_cookie)
            or dataset is None
            or dataset.business is None
            or dataset.business.id != business_id
        ):
            return error_response(
                status.HTTP_404_NOT_FOUND,
                "RESOURCE_NOT_FOUND",
                "사업장 또는 데이터셋을 찾을 수 없습니다.",
            )
        if dataset.status is not DatasetStatus.READY:
            return error_response(
                status.HTTP_409_CONFLICT,
                "DATASET_NOT_READY",
                "컬럼 매핑이 확정된 데이터셋만 진단할 수 있습니다.",
            )

        diagnosis = create_running_diagnosis(database, business, dataset)
        if diagnosis.id is None or diagnosis.created_at is None:
            raise RuntimeError("저장된 진단 식별자 또는 생성 시각이 없습니다.")
        response = DiagnosisStartResponse(
            diagnosis_id=diagnosis.id,
            business_id=business_id,
            status="RUNNING",
            created_at=diagnosis.created_at,
        )

    background_tasks.add_task(run_diagnosis, response.diagnosis_id)
    return response


@router.get(
    "/api/diagnoses/{diagnosis_id}",
    response_model=DiagnosisResultResponse,
)
def get_diagnosis(
    diagnosis_id: int,
    database: Annotated[Session, Depends(get_db)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> DiagnosisResultResponse | JSONResponse:
    diagnosis = database.get(Diagnosis, diagnosis_id)
    if (
        diagnosis is None
        or diagnosis.business is None
        or not _owns_active_session(
            database,
            diagnosis.business,
            demo_session_cookie,
        )
    ):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "DIAGNOSIS_NOT_FOUND",
            "진단 결과를 찾을 수 없습니다.",
        )

    response_status = diagnosis.status.value.upper()
    if diagnosis.status is not DiagnosisStatus.COMPLETED:
        return DiagnosisResultResponse(
            diagnosis_id=diagnosis_id,
            status=response_status,
        )

    values = {metric.metric_code: metric.current_value for metric in diagnosis.metrics}
    return DiagnosisResultResponse(
        diagnosis_id=diagnosis_id,
        status=response_status,
        financial_metrics=FinancialMetricsResponse(
            monthly_sales_amount=int(_required_metric(values, "MONTHLY_SALES_AMOUNT")),
            operating_profit_rate=float(_required_metric(values, "OPERATING_PROFIT_RATE")),
            material_cost_rate=float(_required_metric(values, "MATERIAL_COST_RATE")),
            cash_surplus_amount=int(_required_metric(values, "CASH_SURPLUS_AMOUNT")),
        ),
        activity_metrics=ActivityMetricsResponse(
            monthly_order_count=int(_required_metric(values, "MONTHLY_ORDER_COUNT")),
            online_sales_ratio=(
                float(values["ONLINE_SALES_RATIO"]) if "ONLINE_SALES_RATIO" in values else None
            ),
            employee_count=int(_required_metric(values, "EMPLOYEE_COUNT")),
        ),
        commercial_metrics=CommercialMetricsResponse(
            floating_population_growth_rate=None,
            sales_compared_to_peer_rate=float(
                _required_metric(values, "SALES_COMPARED_TO_PEER_RATE")
            ),
        ),
        bottlenecks=[_bottleneck_response(item) for item in diagnosis.bottlenecks],
    )


def error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _parse_session_id(session_cookie: str | None) -> UUID | None:
    try:
        return UUID(session_cookie) if session_cookie else None
    except ValueError:
        return None


def _owns_active_session(
    database: Session,
    business: Business,
    session_cookie: str | None,
) -> bool:
    session_id = _parse_session_id(session_cookie)
    if session_id is None or business.demo_session_id != session_id:
        return False

    demo_session = database.get(DemoSession, session_id)
    return (
        demo_session is not None
        and demo_session.status is DemoSessionStatus.ACTIVE
        and demo_session.expires_at > datetime.now(UTC)
    )


def _required_metric(values: dict[str, object], code: str) -> object:
    if code not in values:
        raise RuntimeError(f"완료된 진단에 {code} 지표가 없습니다.")
    return values[code]


def _bottleneck_response(bottleneck: Bottleneck) -> BottleneckResponse:
    titles = {
        "HIGH_MATERIAL_COST": "재료비 부담 상승",
        "HIGH_LABOR_COST": "인건비 부담 상승",
        "CHANNEL_CONCENTRATION": "판매 채널 편중",
        "HIGH_PLATFORM_COST": "플랫폼 비용 부담",
        "HIGH_ONLINE_REFUND_RATE": "온라인 취소·환불 증가",
        "LOW_NET_SETTLEMENT_RATE": "온라인 순정산율 저조",
        "TIME_OF_DAY_WEAKNESS": "특정 시간대 고객 유입 부족",
    }
    priorities = {
        BottleneckSeverity.MILD: "LOW",
        BottleneckSeverity.CLEAR: "MEDIUM",
        BottleneckSeverity.SEVERE: "HIGH",
    }
    high_confidence_sources = {
        DataSourceType.PUBLIC_DATA,
        DataSourceType.BENCHMARK,
        DataSourceType.USER_INPUT,
        DataSourceType.CALCULATED,
    }
    low_confidence_sources = {
        DataSourceType.SYNTHETIC_SALES,
        DataSourceType.SYNTHETIC_EXPENSE,
        DataSourceType.SYNTHETIC_ONLINE_SALES,
    }
    if bottleneck.evidence_source_type in high_confidence_sources:
        confidence = "HIGH"
    elif bottleneck.evidence_source_type in low_confidence_sources:
        confidence = "LOW"
    else:
        confidence = "MEDIUM"
    return BottleneckResponse(
        code=bottleneck.bottleneck_type,
        title=titles.get(bottleneck.bottleneck_type, bottleneck.bottleneck_type),
        priority=priorities[bottleneck.severity],
        confidence=confidence,
        detail=bottleneck.detail,
        evidence=bottleneck.evidence_description,
    )
