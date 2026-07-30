# 사업 진단 실행·조회 API 계약과 익명 세션 격리를 검증하는 테스트
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.routes import diagnoses as diagnosis_routes
from app.db import session as db_session
from app.domain.business import Business
from app.domain.dataset import BusinessSnapshot, Dataset, PublicDataSnapshot
from app.domain.diagnosis import Bottleneck, Diagnosis, DiagnosisMetric
from app.domain.enums import (
    BottleneckSeverity,
    DatasetStatus,
    DataSourceType,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
)
from app.main import app

SESSION_ID = UUID("21ee64f2-0c95-4b55-a8c0-3943d36ef8f1")
OTHER_SESSION_ID = UUID("15e72615-d9e0-46d0-a4fa-33f5154d4447")
CREATED_AT = datetime(2026, 7, 29, 3, 26, tzinfo=UTC)


def metric(code: str, value: str, unit: str) -> DiagnosisMetric:
    return DiagnosisMetric(
        metric_code=code,
        current_value=Decimal(value),
        current_source_type=DataSourceType.CALCULATED,
        comparison_value=Decimal("0"),
        comparison_source_type=DataSourceType.BENCHMARK,
        difference_value=Decimal(value),
        unit=unit,
    )


def build_diagnosis(
    *,
    dataset_status: DatasetStatus = DatasetStatus.READY,
    diagnosis_status: DiagnosisStatus = DiagnosisStatus.COMPLETED,
) -> tuple[Business, Dataset, Diagnosis]:
    business = Business(
        id=1,
        demo_session_id=SESSION_ID,
        name="Y카페",
        region="서울 마포구",
        industry="카페",
        employee_count=2,
    )
    dataset = Dataset(id=10, business=business, status=dataset_status)
    business_snapshot = BusinessSnapshot(
        id=30,
        business=business,
        dataset=dataset,
        reference_date=CREATED_AT.date(),
        snapshot_version="v1",
        monthly_net_sales_amount=30_000_000,
        monthly_expense_amount=26_700_000,
        existing_monthly_repayment_amount=1_500_000,
        contribution_margin_rate=Decimal("0.6"),
        monthly_order_count=420,
        online_sales_ratio=Decimal("0.09"),
        employee_count=2,
        source_type=DataSourceType.CALCULATED,
    )
    public_snapshot = PublicDataSnapshot(
        id=40,
        business=business,
        reference_date=CREATED_AT.date(),
        source_name="서울시 상권분석서비스 추정매출-상권",
        snapshot_version="20242-cafe-v1",
        reference_area="서울 전체 커피-음료 상권",
        raw_data={},
    )
    diagnosis = Diagnosis(
        id=20,
        business=business,
        dataset=dataset,
        business_snapshot=business_snapshot,
        public_data_snapshot=public_snapshot,
        status=diagnosis_status,
        evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )
    diagnosis.metrics = [
        metric("MONTHLY_SALES_AMOUNT", "30000000", "KRW"),
        metric("OPERATING_PROFIT_RATE", "11.0", "PERCENT"),
        metric("MATERIAL_COST_RATE", "40.0", "PERCENT"),
        metric("CASH_SURPLUS_AMOUNT", "1800000", "KRW"),
        metric("MONTHLY_ORDER_COUNT", "420", "COUNT"),
        metric("ONLINE_SALES_RATIO", "9.0", "PERCENT"),
        metric("EMPLOYEE_COUNT", "2", "COUNT"),
        metric("SALES_COMPARED_TO_PEER_RATE", "-8.0", "PERCENT"),
    ]
    diagnosis.bottlenecks = [
        Bottleneck(
            bottleneck_type="CHANNEL_CONCENTRATION",
            detail="온라인 주문 비중 9%, 비교군 28%.",
            severity=BottleneckSeverity.SEVERE,
            evidence_source_type=DataSourceType.DOMAIN_ASSUMPTION,
            evidence_description="업로드 자료를 업계 참고치와 비교했습니다.",
            related_categories=["marketing_online"],
        )
    ]
    return business, dataset, diagnosis


class FakeDatabaseSession:
    def __init__(self, business: Business, dataset: Dataset, diagnosis: Diagnosis) -> None:
        self.business = business
        self.dataset = dataset
        self.diagnosis = diagnosis

    @contextmanager
    def begin(self) -> Iterator[None]:
        yield

    def get(self, model: type, identifier: int):
        if model is Business and identifier == self.business.id:
            return self.business
        if model is Dataset and identifier == self.dataset.id:
            return self.dataset
        if model is Diagnosis and identifier == self.diagnosis.id:
            return self.diagnosis
        return None

    def close(self) -> None:
        pass


def create_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    dataset_status: DatasetStatus = DatasetStatus.READY,
    diagnosis_status: DiagnosisStatus = DiagnosisStatus.COMPLETED,
    session_id: UUID = SESSION_ID,
) -> tuple[TestClient, Diagnosis, list[int]]:
    business, dataset, diagnosis = build_diagnosis(
        dataset_status=dataset_status,
        diagnosis_status=diagnosis_status,
    )
    database = FakeDatabaseSession(business, dataset, diagnosis)
    scheduled: list[int] = []
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    monkeypatch.setattr(
        diagnosis_routes,
        "create_running_diagnosis",
        lambda *_: diagnosis,
    )
    monkeypatch.setattr(
        diagnosis_routes,
        "run_diagnosis",
        lambda diagnosis_id: scheduled.append(diagnosis_id),
    )
    client = TestClient(app)
    client.cookies.set("demo_session_id", str(session_id))
    return client, diagnosis, scheduled


def test_create_diagnosis_returns_running_and_schedules_background_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, scheduled = create_client(monkeypatch)

    response = client.post("/api/businesses/1/diagnoses", json={"datasetId": 10})

    assert response.status_code == 202
    assert response.json() == {
        "diagnosisId": 20,
        "businessId": 1,
        "status": "RUNNING",
        "createdAt": "2026-07-29T03:26:00Z",
    }
    assert scheduled == [20]


def test_create_diagnosis_returns_bad_request_for_invalid_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = create_client(monkeypatch)

    response = client.post("/api/businesses/1/diagnoses", json={})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_diagnosis_validation_does_not_change_existing_api_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = create_client(monkeypatch)

    response = client.post("/api/businesses", json={})

    assert response.status_code == 422


def test_create_diagnosis_returns_conflict_when_dataset_is_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, scheduled = create_client(
        monkeypatch,
        dataset_status=DatasetStatus.NORMALIZING,
    )

    response = client.post("/api/businesses/1/diagnoses", json={"datasetId": 10})

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "DATASET_NOT_READY",
            "message": "컬럼 매핑이 확정된 데이터셋만 진단할 수 있습니다.",
        }
    }
    assert scheduled == []


def test_get_completed_diagnosis_returns_metrics_and_bottlenecks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = create_client(monkeypatch)

    response = client.get("/api/diagnoses/20")

    assert response.status_code == 200
    body = response.json()
    assert body["diagnosisId"] == 20
    assert body["status"] == "COMPLETED"
    assert body["financialMetrics"] == {
        "monthlySalesAmount": 30_000_000,
        "operatingProfitRate": 11.0,
        "materialCostRate": 40.0,
        "cashSurplusAmount": 1_800_000,
    }
    assert body["activityMetrics"] == {
        "monthlyOrderCount": 420,
        "onlineSalesRatio": 9.0,
        "employeeCount": 2,
    }
    assert body["commercialMetrics"] == {
        "floatingPopulationGrowthRate": None,
        "salesComparedToPeerRate": -8.0,
    }
    assert body["bottlenecks"] == [
        {
            "code": "CHANNEL_CONCENTRATION",
            "title": "판매 채널 편중",
            "priority": "HIGH",
            "confidence": "MEDIUM",
            "evidence": "온라인 주문 비중 9%, 비교군 28%.",
        }
    ]


def test_get_running_diagnosis_returns_null_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = create_client(
        monkeypatch,
        diagnosis_status=DiagnosisStatus.RUNNING,
    )

    response = client.get("/api/diagnoses/20")

    assert response.status_code == 200
    assert response.json() == {
        "diagnosisId": 20,
        "status": "RUNNING",
        "financialMetrics": None,
        "activityMetrics": None,
        "commercialMetrics": None,
        "bottlenecks": None,
    }


def test_get_diagnosis_hides_another_session_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = create_client(monkeypatch, session_id=OTHER_SESSION_ID)

    response = client.get("/api/diagnoses/20")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "DIAGNOSIS_NOT_FOUND",
            "message": "진단 결과를 찾을 수 없습니다.",
        }
    }
