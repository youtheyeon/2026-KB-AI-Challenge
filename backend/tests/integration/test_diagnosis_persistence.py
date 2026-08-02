# PostgreSQL에서 진단 백그라운드 작업의 스냅샷·지표·병목 영속화를 검증하는 통합 테스트
import os
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.domain  # noqa: F401
from app.db import session as db_session
from app.db.base import Base
from app.domain.business import Business
from app.domain.dataset import (
    BusinessSnapshot,
    Dataset,
    NormalizedExpense,
    NormalizedOnlineSale,
    NormalizedSale,
    PublicDataSnapshot,
)
from app.domain.demo_session import DemoSession
from app.domain.diagnosis import Bottleneck, Diagnosis, DiagnosisMetric
from app.domain.enums import (
    DatasetStatus,
    DemoSessionStatus,
    DiagnosisStatus,
    ExpenseCategory,
)
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="격리된 PostgreSQL TEST_DATABASE_URL이 필요합니다.",
)


def reset_schema() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    reset_schema()
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def create_ready_dataset(postgres_engine: Engine) -> tuple[int, int, str]:
    now = datetime.now(UTC)
    session_id = uuid4()
    with Session(postgres_engine) as database, database.begin():
        demo_session = DemoSession(
            id=session_id,
            last_accessed_at=now,
            expires_at=now + timedelta(hours=24),
            status=DemoSessionStatus.ACTIVE,
        )
        business = Business(
            demo_session=demo_session,
            name="Y카페",
            region="서울 마포구",
            industry="카페",
            employee_count=2,
        )
        dataset = Dataset(
            business=business,
            status=DatasetStatus.READY,
            dataset_version="integration-v1",
        )
        dataset.sales = [
            NormalizedSale(
                business_date=date(2026, 7, 1),
                receipt_number="R-1",
                gross_sales=100_000,
                net_sales=100_000,
            )
        ]
        dataset.expenses = [
            NormalizedExpense(
                transaction_date=date(2026, 7, 1),
                expense_category=ExpenseCategory.MATERIAL,
                total_amount=60_000,
            ),
            NormalizedExpense(
                transaction_date=date(2026, 7, 1),
                expense_category=ExpenseCategory.LABOR,
                total_amount=20_000,
            ),
        ]
        dataset.online_sales = [
            NormalizedOnlineSale(
                business_date=date(2026, 7, 1),
                order_count=1,
                gross_order_amount=5_000,
                sales_amount=5_000,
                settlement_amount=4_000,
            )
        ]
        database.add(dataset)
        database.flush()
        business_id = business.id
        dataset_id = dataset.id
    return business_id, dataset_id, str(session_id)


def test_diagnosis_background_task_persists_snapshots_metrics_and_bottlenecks(
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
) -> None:
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False),
    )
    business_id, dataset_id, session_id = create_ready_dataset(postgres_engine)
    client = TestClient(app)
    client.cookies.set("demo_session_id", session_id)

    response = client.post(
        f"/api/businesses/{business_id}/diagnoses",
        json={"datasetId": dataset_id},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
    with Session(postgres_engine) as database:
        diagnosis = database.scalar(select(Diagnosis))
        assert diagnosis is not None
        assert diagnosis.status is DiagnosisStatus.COMPLETED
        assert diagnosis.metrics
        assert diagnosis.bottlenecks
        assert diagnosis.public_data_snapshot.raw_data["sampleSize"] == 326
        assert database.scalar(select(BusinessSnapshot)) is not None
        assert database.scalar(select(PublicDataSnapshot)) is not None

    result_response = client.get(f"/api/diagnoses/{diagnosis.id}")
    assert result_response.status_code == 200
    assert result_response.json()["status"] == "COMPLETED"


def test_diagnosis_failure_rolls_back_partial_results_and_marks_failed(
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
) -> None:
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False),
    )
    business_id, dataset_id, session_id = create_ready_dataset(postgres_engine)
    client = TestClient(app)
    client.cookies.set("demo_session_id", session_id)

    def fail_metric_insert(*_: object) -> None:
        raise RuntimeError("의도적인 진단 지표 저장 실패")

    event.listen(DiagnosisMetric, "before_insert", fail_metric_insert)
    try:
        response = client.post(
            f"/api/businesses/{business_id}/diagnoses",
            json={"datasetId": dataset_id},
        )
    finally:
        event.remove(DiagnosisMetric, "before_insert", fail_metric_insert)

    assert response.status_code == 202
    with Session(postgres_engine) as database:
        diagnosis = database.scalar(select(Diagnosis))
        metric_count = database.scalar(select(func.count()).select_from(DiagnosisMetric))
        bottleneck_count = database.scalar(select(func.count()).select_from(Bottleneck))

    assert diagnosis is not None
    assert diagnosis.status is DiagnosisStatus.FAILED
    assert metric_count == 0
    assert bottleneck_count == 0
