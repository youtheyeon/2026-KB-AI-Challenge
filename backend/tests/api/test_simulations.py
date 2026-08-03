# 자금 배분 시뮬레이션 네 API의 요청·응답과 구조화 오류 계약을 검증하는 테스트
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.routes.simulations import get_simulation_service
from app.core.errors import ApiError
from app.domain.enums import RepaymentType
from app.main import app

SESSION_COOKIE = "12345678-1234-5678-1234-567812345678"


def scenario_payload(code: str, scenario_id: int) -> dict:
    return {
        "scenario_id": scenario_id,
        "scenario_code": code,
        "strategy_type": "BOTTLENECK_FOCUSED",
        "title": f"{code}안",
        "allocations": [
            {"category": "MARKETING_ONLINE", "ratio": 0.4, "amount": 6_000_000},
            {"category": "EQUIPMENT_INTERIOR", "ratio": 0.2, "amount": 3_000_000},
            {"category": "LABOR", "ratio": 0.2, "amount": 3_000_000},
            {"category": "INVENTORY", "ratio": 0.2, "amount": 3_000_000},
        ],
        "reasons": [
            {
                "bottleneck_id": 201,
                "category": "EQUIPMENT_INTERIOR",
                "description": "원가율 병목에 대응하는 배분입니다.",
                "source_type": "CALCULATED",
            }
        ],
        "financial_result": {
            "monthly_loan_payment": 446_205,
            "monthly_recurring_cost": 100_000,
            "cash_after_payment": 203_795,
            "break_even_additional_revenue": 0,
            "required_additional_orders": None,
            "payback_period_months": None,
            "risk_level": "LOW",
        },
        "target_metrics": ["COGS_RATIO"],
        "risk_reasons": ["현재 매출 기준으로 판정했습니다."],
        "allocation_rationale": "원가율 병목이 가장 뚜렷해 설비 개선에 배분을 집중했습니다.",
        "scb_growth_outlook": "설비 개선이 자리 잡으면 원가 구조 지표가 개선될 수 있습니다.",
    }


def result_payload() -> dict:
    return {
        "simulation_id": 45,
        "business_id": 7,
        "diagnosis_id": 31,
        "status": "COMPLETED",
        "loan_condition": {
            "amount": 15_000_000,
            "annual_interest_rate": 0.045,
            "term_months": 36,
            "grace_months": 0,
            "repayment_type": "EQUAL_PAYMENT",
        },
        "scenarios": [
            scenario_payload("A", 101),
            scenario_payload("B", 102),
            scenario_payload("C", 103),
        ],
        "selected_scenario_id": None,
        "created_at": datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    }


class FakeSimulationService:
    def __init__(self) -> None:
        self.error: ApiError | None = None
        self.creation_command = None
        self.calls: list[str] = []

    def _raise_if_needed(self) -> None:
        if self.error is not None:
            raise self.error

    def create(self, command, session_cookie):
        self._raise_if_needed()
        self.calls.append("create")
        self.creation_command = command
        return {"simulation_id": 45, "status": "COMPLETED"}

    def get_result(self, simulation_id, session_cookie):
        self._raise_if_needed()
        self.calls.append("get_result")
        return result_payload()

    def get_comparison(self, simulation_id, session_cookie):
        self._raise_if_needed()
        self.calls.append("get_comparison")
        result = result_payload()
        scenarios = [
            {key: value for key, value in scenario.items() if key != "reasons"}
            for scenario in result["scenarios"]
        ]
        return {
            "simulation_id": simulation_id,
            "scenarios": scenarios,
            "recommendation_provided": False,
            "disclaimer": "AI는 특정 시나리오를 추천하거나 성과를 보장하지 않습니다.",
        }

    def select_scenario(self, simulation_id, scenario_id, session_cookie):
        self._raise_if_needed()
        self.calls.append("select_scenario")
        return {
            "simulation_id": simulation_id,
            "selected_scenario_id": scenario_id,
            "selected_at": datetime(2026, 7, 31, 12, 30, tzinfo=UTC),
            "locked": False,
        }


@pytest.fixture
def api_client() -> tuple[TestClient, FakeSimulationService]:
    service = FakeSimulationService()
    app.dependency_overrides[get_simulation_service] = lambda: service
    client = TestClient(app)
    client.cookies.set("demo_session_id", SESSION_COOKIE)
    try:
        yield client, service
    finally:
        app.dependency_overrides.clear()


def creation_payload() -> dict:
    return {
        "diagnosisId": 31,
        "loanAmount": 15_000_000,
        "annualInterestRate": 0.045,
        "termMonths": 36,
        "graceMonths": 0,
        "repaymentType": "EQUAL_PAYMENT",
    }


def test_create_simulation_returns_identifier_only(
    api_client: tuple[TestClient, FakeSimulationService],
) -> None:
    client, service = api_client

    response = client.post("/api/businesses/7/simulations", json=creation_payload())

    assert response.status_code == 201
    assert response.json() == {"simulationId": 45, "status": "COMPLETED"}
    assert service.creation_command.repayment_type == RepaymentType.EQUAL_PAYMENT


def test_create_simulation_rejects_grace_equal_to_term(
    api_client: tuple[TestClient, FakeSimulationService],
) -> None:
    client, service = api_client
    payload = creation_payload()
    payload["graceMonths"] = payload["termMonths"]

    response = client.post("/api/businesses/7/simulations", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert service.calls == []


@pytest.mark.parametrize(
    "error",
    [
        ApiError(404, "RESOURCE_NOT_FOUND", "요청한 자원을 찾을 수 없습니다."),
        ApiError(
            409,
            "DIAGNOSIS_NOT_COMPLETED",
            "완료된 진단만 시뮬레이션에 사용할 수 있습니다.",
        ),
        ApiError(
            502,
            "SIMULATION_GENERATION_FAILED",
            "시뮬레이션 결과 생성에 실패했습니다.",
        ),
    ],
)
def test_create_simulation_returns_structured_service_error(
    api_client: tuple[TestClient, FakeSimulationService],
    error: ApiError,
) -> None:
    client, service = api_client
    service.error = error

    response = client.post("/api/businesses/7/simulations", json=creation_payload())

    assert response.status_code == error.status_code
    assert response.json() == {
        "error": {
            "code": error.code,
            "message": error.message,
        }
    }


def test_get_simulation_returns_camel_case_stored_result(
    api_client: tuple[TestClient, FakeSimulationService],
) -> None:
    client, service = api_client

    response = client.get("/api/simulations/45")

    assert response.status_code == 200
    body = response.json()
    assert body["simulationId"] == 45
    assert body["loanCondition"]["repaymentType"] == "EQUAL_PAYMENT"
    assert [scenario["scenarioCode"] for scenario in body["scenarios"]] == ["A", "B", "C"]
    assert body["scenarios"][0]["allocations"][0]["category"] == "MARKETING_ONLINE"
    assert service.calls == ["get_result"]


def test_get_comparison_is_neutral_and_does_not_create_result(
    api_client: tuple[TestClient, FakeSimulationService],
) -> None:
    client, service = api_client

    response = client.get("/api/simulations/45/comparison")

    assert response.status_code == 200
    assert response.json()["recommendationProvided"] is False
    assert "추천" in response.json()["disclaimer"]
    assert service.calls == ["get_comparison"]


def test_select_scenario_returns_current_selection(
    api_client: tuple[TestClient, FakeSimulationService],
) -> None:
    client, service = api_client

    response = client.post(
        "/api/simulations/45/selection",
        json={"scenarioId": 102},
    )

    assert response.status_code == 200
    assert response.json() == {
        "simulationId": 45,
        "selectedScenarioId": 102,
        "selectedAt": "2026-07-31T12:30:00Z",
        "locked": False,
    }
    assert service.calls == ["select_scenario"]
