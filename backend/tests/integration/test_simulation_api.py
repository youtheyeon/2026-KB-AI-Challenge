# PostgreSQL에서 시뮬레이션 전체 그래프의 저장·롤백·선택 제약을 검증하는 통합 테스트
import os
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
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
from app.domain.dataset import BusinessSnapshot, Dataset, PublicDataSnapshot
from app.domain.demo_session import DemoSession
from app.domain.diagnosis import Bottleneck, Diagnosis
from app.domain.enums import (
    BottleneckSeverity,
    DatasetStatus,
    DataSourceType,
    DemoSessionStatus,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
)
from app.domain.simulation import (
    Scenario,
    ScenarioAllocation,
    ScenarioReason,
    ScenarioSelection,
    Simulation,
)
from app.main import app
from app.services.simulation_engine import get_simulation_engine

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="격리된 PostgreSQL TEST_DATABASE_URL이 필요합니다.",
)


def engine_result() -> dict:
    allocations = {
        "marketing_online": 0.4,
        "equipment_interior": 0.2,
        "labor": 0.2,
        "inventory": 0.2,
    }
    amounts = {
        "marketing_online": 6_000_000,
        "equipment_interior": 3_000_000,
        "labor": 3_000_000,
        "inventory": 3_000_000,
    }
    scenarios = []
    for code, label in [
        ("A", "병목 집중형"),
        ("B", "진단 비례 대응형"),
        ("C", "균등 분산형 (기준선)"),
    ]:
        scenarios.append(
            {
                "scenario_id": code,
                "label": label,
                "allocation": allocations,
                "allocation_amounts_won": amounts,
                "loan_amount": 15_000_000,
                "target_metrics": ["COGS_RATIO"],
                "financial_result": {
                    "monthly_loan_payment": 446_205,
                    "additional_fixed_cost_per_month": 100_000,
                    "remaining_cash_after_payment": 203_795,
                    "break_even_additional_revenue": 0,
                    "required_additional_orders": None,
                    "payback_period": {"months": None},
                    "risk_level": "낮음",
                    "risk_level_basis": "현재 매출 기준으로 판정했습니다.",
                    "loan_scale_warning": {
                        "is_warning": False,
                        "message": None,
                    },
                },
                "allocation_rationale": f"{code}안의 AI 배분 근거",
            }
        )
    return {
        "scenario_results": scenarios,
        "versions": {
            "allocation_generator_version": "2.0",
            "calculation_version": "1.1",
            "prompt_version": "1.0",
        },
    }


class FakeEngine:
    def run(self, request):
        return engine_result()


def reset_schema() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


@pytest.fixture
def postgres_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    reset_schema()
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=engine, autoflush=False, autocommit=False),
    )
    app.dependency_overrides[get_simulation_engine] = lambda: FakeEngine()
    try:
        yield engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def seed_completed_diagnosis(engine: Engine) -> tuple[int, int, str]:
    now = datetime.now(UTC)
    session_id = uuid4()
    with Session(engine) as database, database.begin():
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
            primary_sales_channels=[],
        )
        dataset = Dataset(
            business=business,
            status=DatasetStatus.READY,
            dataset_version="v1",
        )
        business_snapshot = BusinessSnapshot(
            business=business,
            dataset=dataset,
            reference_date=date(2026, 7, 1),
            snapshot_version="v1",
            monthly_net_sales_amount=7_500_000,
            monthly_expense_amount=5_000_000,
            existing_monthly_repayment_amount=0,
            contribution_margin_rate=Decimal("0.55"),
            average_order_amount=8_000,
            monthly_order_count=2_700,
            employee_count=2,
            source_type=DataSourceType.CALCULATED,
        )
        public_snapshot = PublicDataSnapshot(
            business=business,
            reference_date=date(2026, 6, 30),
            source_name="서울시 상권분석서비스",
            snapshot_version="v1",
            reference_area="서울",
            raw_data={},
        )
        diagnosis = Diagnosis(
            business=business,
            dataset=dataset,
            business_snapshot=business_snapshot,
            public_data_snapshot=public_snapshot,
            status=DiagnosisStatus.COMPLETED,
            evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
            diagnosis_version="v1",
            benchmark_version="v1",
            bottlenecks=[
                Bottleneck(
                    bottleneck_type="high_cost_ratio",
                    detail="원가율이 업계 참고치보다 높습니다.",
                    severity=BottleneckSeverity.SEVERE,
                    evidence_source_type=DataSourceType.DOMAIN_ASSUMPTION,
                    evidence_description="업계 참고 원가율과 비교했습니다.",
                    related_categories=["equipment_interior"],
                )
            ],
        )
        database.add(diagnosis)
        database.flush()
        business_id = business.id
        diagnosis_id = diagnosis.id
    return business_id, diagnosis_id, str(session_id)


def create_simulation(client: TestClient, business_id: int, diagnosis_id: int):
    return client.post(
        f"/api/businesses/{business_id}/simulations",
        json={
            "diagnosisId": diagnosis_id,
            "loanAmount": 15_000_000,
            "annualInterestRate": 0.045,
            "termMonths": 36,
            "graceMonths": 0,
            "repaymentType": "EQUAL_PAYMENT",
        },
    )


def test_simulation_api_persists_graph_and_single_selection(
    postgres_engine: Engine,
) -> None:
    business_id, diagnosis_id, session_id = seed_completed_diagnosis(postgres_engine)
    client = TestClient(app)
    client.cookies.set("demo_session_id", session_id)

    response = create_simulation(client, business_id, diagnosis_id)

    assert response.status_code == 201
    simulation_id = response.json()["simulationId"]
    detail = client.get(f"/api/simulations/{simulation_id}")
    first_scenario_id = detail.json()["scenarios"][0]["scenarioId"]
    second_scenario_id = detail.json()["scenarios"][1]["scenarioId"]
    assert (
        client.post(
            f"/api/simulations/{simulation_id}/selection",
            json={"scenarioId": first_scenario_id},
        ).status_code
        == 200
    )
    changed = client.post(
        f"/api/simulations/{simulation_id}/selection",
        json={"scenarioId": second_scenario_id},
    )

    assert changed.status_code == 200
    assert changed.json()["selectedScenarioId"] == second_scenario_id
    with Session(postgres_engine) as database:
        assert database.scalar(select(func.count()).select_from(Simulation)) == 1
        assert database.scalar(select(func.count()).select_from(Scenario)) == 3
        assert database.scalar(select(func.count()).select_from(ScenarioAllocation)) == 12
        assert database.scalar(select(func.count()).select_from(ScenarioReason)) == 6
        assert database.scalar(select(func.count()).select_from(ScenarioSelection)) == 1


def test_simulation_api_rolls_back_graph_when_allocation_insert_fails(
    postgres_engine: Engine,
) -> None:
    business_id, diagnosis_id, session_id = seed_completed_diagnosis(postgres_engine)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("demo_session_id", session_id)

    def fail_allocation_insert(*_: object) -> None:
        raise RuntimeError("의도적인 scenario allocation insert 실패")

    event.listen(ScenarioAllocation, "before_insert", fail_allocation_insert)
    try:
        response = create_simulation(client, business_id, diagnosis_id)
    finally:
        event.remove(ScenarioAllocation, "before_insert", fail_allocation_insert)

    assert response.status_code == 500
    with Session(postgres_engine) as database:
        assert database.scalar(select(func.count()).select_from(Simulation)) == 0
        assert database.scalar(select(func.count()).select_from(Scenario)) == 0
        assert database.scalar(select(func.count()).select_from(ScenarioAllocation)) == 0
        assert database.scalar(select(func.count()).select_from(ScenarioReason)) == 0
