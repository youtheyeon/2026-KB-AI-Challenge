# 결과 검증과 선순환 대시보드 여섯 API의 HTTP 계약 테스트
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.routes.verifications import (
    get_dashboard_service,
    get_outcome_data_service,
    get_outcome_service,
    get_verification_service,
)
from app.core.errors import ApiError
from app.domain.enums import ExecutionType, OutcomeDataSourceType
from app.main import app

SESSION_COOKIE = "12345678-1234-5678-1234-567812345678"
SAVED_AT = datetime(2026, 7, 31, 12, tzinfo=UTC)


class FakeVerificationService:
    def __init__(self) -> None:
        self.execution_command = None

    def list_targets(self, business_id, include_completed, session_cookie):
        return {
            "business_id": business_id,
            "targets": [
                {
                    "simulation_id": 45,
                    "saved_at": datetime(2026, 4, 30, 12, tzinfo=UTC),
                    "days_elapsed": 92,
                    "execution_registered": False,
                    "business_name": "청춘카페",
                    "region": "서울",
                    "loan_amount": 15_000_000,
                    "plan_summaries": [{"plan_code": "A", "title": "병목 집중형"}],
                }
            ],
        }

    def create_execution(self, command, session_cookie):
        self.execution_command = command
        return {
            "execution_id": 81,
            "simulation_id": command.simulation_id,
            "execution_mode": command.mode.name,
            "total_executed_amount": 14_500_000,
            "saved_at": SAVED_AT,
        }


class FakeOutcomeDataService:
    def __init__(self) -> None:
        self.commands = []
        self.error = None

    def create(self, command, session_cookie):
        if self.error is not None:
            raise self.error
        self.commands.append(command)
        return {
            "outcome_data_id": 91,
            "simulation_id": command.simulation_id,
            "source_type": command.source_type.name,
            "status": (
                "MAPPING_READY"
                if command.source_type is OutcomeDataSourceType.FILE_UPLOAD
                else "READY"
            ),
            "dataset_id": 62,
            "observed_at": date(2026, 7, 31),
        }


class FakeOutcomeService:
    def __init__(self) -> None:
        self.command = None

    def create(self, command, session_cookie):
        self.command = command
        return {
            "outcome_id": 101,
            "simulation_id": command.simulation_id,
            "status": "COMPLETED",
            "summary": {
                "sales_growth_status": "ABOVE_EXPECTED",
                "online_ratio_status": "WITHIN_RANGE",
                "cash_after_repayment_status": "BELOW_EXPECTED",
            },
            "created_at": datetime(2026, 7, 31, 12, 10, tzinfo=UTC),
        }

    def get_result(self, simulation_id, session_cookie):
        return {
            "outcome_id": 101,
            "simulation_id": simulation_id,
            "overall_status": "PARTIALLY_MET",
            "trends": [
                {
                    "metric_code": "MONTHLY_SALES",
                    "before_value": Decimal("7500000"),
                    "after_value": Decimal("8100000"),
                    "unit": "KRW",
                }
            ],
            "comparison_rows": [
                {
                    "metric_code": "MONTHLY_SALES",
                    "label": "월 매출",
                    "target_value": Decimal("7600000"),
                    "break_even_value": Decimal("7500000"),
                    "observed_value": Decimal("8100000"),
                    "unit": "KRW",
                    "status": "ABOVE_EXPECTED",
                }
            ],
            "reevaluation": [
                {
                    "bottleneck_type": "high_cost_ratio",
                    "change_type": "REMAINING",
                    "detail": "원가율 병목이 남아 있습니다.",
                }
            ],
            "new_bottlenecks": [
                {
                    "bottleneck_type": "high_labor_ratio",
                    "title": "인건비 부담 상승",
                    "detail": "인건비 병목이 새로 나타났습니다.",
                }
            ],
            "created_at": datetime(2026, 7, 31, 12, 10, tzinfo=UTC),
        }


class FakeDashboardService:
    def get(self, business_id, session_cookie):
        return {
            "business": {
                "business_id": business_id,
                "name": "청춘카페",
                "region": "서울",
                "industry": "카페",
            },
            "loan_status": {
                "loan_amount": 15_000_000,
                "monthly_repayment_amount": 446_205,
                "paid_amount": 1_338_615,
                "estimated_remaining_principal": 13_932_143,
                "progress_rate": Decimal("0.0833"),
                "repayment_data_type": "ESTIMATED",
            },
            "metric_trends": [],
            "cycle_histories": [],
            "unresolved_bottlenecks": [],
            "next_initial_conditions": {"monthly_revenue": 8_100_000},
        }


@pytest.fixture
def api_client():
    services = SimpleNamespace(
        verification=FakeVerificationService(),
        outcome_data=FakeOutcomeDataService(),
        outcome=FakeOutcomeService(),
        dashboard=FakeDashboardService(),
    )
    app.dependency_overrides[get_verification_service] = lambda: services.verification
    app.dependency_overrides[get_outcome_data_service] = lambda: services.outcome_data
    app.dependency_overrides[get_outcome_service] = lambda: services.outcome
    app.dependency_overrides[get_dashboard_service] = lambda: services.dashboard
    client = TestClient(app)
    client.cookies.set("demo_session_id", SESSION_COOKIE)
    try:
        yield client, services
    finally:
        app.dependency_overrides.clear()


def test_verification_targets_return_camel_case(api_client) -> None:
    client, _ = api_client

    response = client.get("/api/businesses/7/verification-targets")

    assert response.status_code == 200
    assert response.json()["businessId"] == 7
    assert response.json()["targets"][0]["executionRegistered"] is False
    assert response.json()["targets"][0]["planSummaries"][0]["planCode"] == "A"


def test_create_custom_execution_returns_camel_case(api_client) -> None:
    client, services = api_client

    response = client.post(
        "/api/simulations/45/executions",
        json={
            "executionMode": "CUSTOM",
            "executedAt": "2026-07-30",
            "items": [{"name": "저녁 광고", "amount": 14_500_000}],
            "unusedAmount": 500_000,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "executionId": 81,
        "simulationId": 45,
        "executionMode": "CUSTOM",
        "totalExecutedAmount": 14_500_000,
        "savedAt": "2026-07-31T12:00:00Z",
    }
    assert services.verification.execution_command.mode is ExecutionType.CUSTOM


def test_outcome_data_accepts_manual_json(api_client) -> None:
    client, services = api_client

    response = client.post(
        "/api/simulations/45/outcome-data",
        json={
            "sourceType": "MANUAL_INPUT",
            "metrics": {
                "monthlySalesAmount": 32_000_000,
                "operatingProfitAmount": 6_200_000,
                "onlineOrderRatio": 0.31,
                "cashAfterRepaymentAmount": 2_800_000,
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["sourceType"] == "MANUAL_INPUT"
    command = services.outcome_data.commands[-1]
    assert command.metrics.monthly_sales_amount == 32_000_000
    assert command.metrics.online_order_ratio == Decimal("0.31")


def test_outcome_data_accepts_mock_json(api_client) -> None:
    client, services = api_client

    response = client.post(
        "/api/simulations/45/outcome-data",
        json={"sourceType": "MOCK"},
    )

    assert response.status_code == 201
    assert services.outcome_data.commands[-1].source_type is OutcomeDataSourceType.MOCK


def test_outcome_data_accepts_file_multipart(api_client) -> None:
    client, services = api_client

    response = client.post(
        "/api/simulations/45/outcome-data",
        data={"sourceType": "FILE_UPLOAD"},
        files={
            "salesFile": (
                "sales.xlsx",
                b"sales-workbook",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            "costFile": (
                "cost.xlsx",
                b"cost-workbook",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        },
    )

    assert response.status_code == 201
    command = services.outcome_data.commands[-1]
    assert command.sales_file.filename == "sales.xlsx"
    assert command.sales_file.contents == b"sales-workbook"
    assert command.expense_file.filename == "cost.xlsx"


def test_outcome_data_rejects_unsupported_content_type(api_client) -> None:
    client, _ = api_client

    response = client.post(
        "/api/simulations/45/outcome-data",
        content=b"plain",
        headers={"content-type": "text/plain"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_CONTENT_TYPE"


def test_outcome_data_validation_uses_global_422_contract(api_client) -> None:
    client, _ = api_client

    response = client.post(
        "/api/simulations/45/outcome-data",
        json={
            "sourceType": "MANUAL_INPUT",
            "metrics": {
                "monthlySalesAmount": 32_000_000,
                "operatingProfitAmount": 6_200_000,
                "onlineOrderRatio": 2,
                "cashAfterRepaymentAmount": 2_800_000,
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_and_get_outcome_use_distinct_status_fields(api_client) -> None:
    client, services = api_client

    created = client.post(
        "/api/simulations/45/outcomes",
        json={"executionId": 81, "outcomeDataId": 91},
    )
    result = client.get("/api/simulations/45/outcomes")

    assert created.status_code == 201
    assert created.json()["status"] == "COMPLETED"
    assert services.outcome.command.execution_id == 81
    assert result.status_code == 200
    assert result.json()["overallStatus"] == "PARTIALLY_MET"
    assert result.json()["comparisonRows"][0]["status"] == "ABOVE_EXPECTED"
    assert result.json()["newBottlenecks"][0]["bottleneckType"] == "high_labor_ratio"


def test_dashboard_marks_repayment_as_estimated(api_client) -> None:
    client, _ = api_client

    response = client.get("/api/businesses/7/dashboard")

    assert response.status_code == 200
    assert response.json()["loanStatus"]["repaymentDataType"] == "ESTIMATED"
    assert response.json()["nextInitialConditions"]["monthly_revenue"] == 8_100_000


@pytest.mark.parametrize(
    "error",
    [
        ApiError(404, "RESOURCE_NOT_FOUND", "요청한 자원을 찾을 수 없습니다."),
        ApiError(409, "OUTCOME_DATA_ALREADY_EXISTS", "이미 등록됐습니다."),
        ApiError(502, "OUTCOME_CALCULATION_FAILED", "결과 검증 계산에 실패했습니다."),
    ],
)
def test_service_errors_remain_structured(api_client, error: ApiError) -> None:
    client, services = api_client
    services.outcome_data.error = error

    response = client.post(
        "/api/simulations/45/outcome-data",
        json={"sourceType": "MOCK"},
    )

    assert response.status_code == error.status_code
    assert response.json() == {"error": {"code": error.code, "message": error.message}}


def test_openapi_exposes_both_outcome_data_content_types() -> None:
    schema = app.openapi()
    content = schema["paths"]["/api/simulations/{simulation_id}/outcome-data"]["post"][
        "requestBody"
    ]["content"]

    assert {"application/json", "multipart/form-data"} <= set(content)
