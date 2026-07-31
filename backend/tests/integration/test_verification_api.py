# PostgreSQL에서 결과 검증 전체 사이클과 다음 시뮬레이션 선순환을 검증하는 통합 테스트
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
    AllocationCategory,
    BottleneckSeverity,
    DatasetStatus,
    DataSourceType,
    DemoSessionStatus,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
    OutcomeStatus,
    RepaymentType,
    RiskLevel,
    ScenarioCode,
)
from app.domain.execution import Execution, ExecutionAllocation
from app.domain.outcome import (
    BottleneckChange,
    OutcomeComparison,
    OutcomeComparisonMetric,
    OutcomeData,
    ReassessmentSnapshot,
)
from app.domain.simulation import (
    Scenario,
    ScenarioAllocation,
    ScenarioSelection,
    Simulation,
)
from app.main import app
from app.services.outcome_engine import get_outcome_engine
from app.services.simulation_engine import get_simulation_engine

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="격리된 PostgreSQL TEST_DATABASE_URL이 필요합니다.",
)


def simulation_engine_result() -> dict:
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
    for code, label in (
        ("A", "병목 집중형"),
        ("B", "진단 비례 대응형"),
        ("C", "균등 분산형 (기준선)"),
    ):
        scenarios.append(
            {
                "scenario_id": code,
                "label": label,
                "allocation": allocations,
                "allocation_amounts_won": amounts,
                "loan_amount": 15_000_000,
                "target_metrics": ["COGS_RATIO"],
                "financial_result": financial_result(),
                "allocation_rationale": f"{code}안의 저장 이력 반영 근거",
            }
        )
    return {
        "scenario_results": scenarios,
        "versions": {
            "allocation_generator_version": "2.0",
            "calculation_version": "1.1",
            "prompt_version": "1.1",
        },
    }


def financial_result() -> dict:
    return {
        "monthly_loan_payment": 446_205,
        "additional_fixed_cost_per_month": 100_000,
        "remaining_cash_after_payment": 203_795,
        "break_even_additional_revenue": 0,
        "required_additional_orders": None,
        "payback_period": {"months": None},
        "risk_level": "낮음",
        "risk_level_basis": "현재 매출 기준으로 판정했습니다.",
        "loan_scale_warning": {"is_warning": False, "message": None},
    }


def mock_pos_data() -> dict:
    return {
        "monthly_revenue": 8_200_000,
        "monthly_cogs": 4_800_000,
        "monthly_labor_cost": 2_100_000,
        "avg_daily_customers": 100,
        "repeat_customer_rate": 0.3,
        "peak_hour_seat_utilization": 0.7,
        "avg_wait_time_minutes": 5,
        "time_of_day_sales": {
            "TMZON_00_06_SELNG_AMT": 0,
            "TMZON_06_11_SELNG_AMT": 1_500_000,
            "TMZON_11_14_SELNG_AMT": 2_000_000,
            "TMZON_14_17_SELNG_AMT": 1_500_000,
            "TMZON_17_21_SELNG_AMT": 2_700_000,
            "TMZON_21_24_SELNG_AMT": 500_000,
        },
        "online_data": {
            "online_order_count": 750,
            "online_gross_order_amount": 2_050_000,
            "online_sales_amount": 2_000_000,
            "platform_cost_amount": 200_000,
            "online_refund_amount": 50_000,
            "online_settlement_amount": 1_800_000,
        },
    }


class FakeOutcomeEngine:
    def generate_mock(self, monthly_revenue: int) -> dict:
        return mock_pos_data()

    def project_financial(self, request) -> dict:
        return financial_result()

    def compare(self, request) -> dict:
        return {
            "resolved_bottlenecks": [],
            "persisted_bottlenecks": ["high_cost_ratio"],
            "new_bottlenecks": ["high_labor_ratio"],
            "not_comparable_bottlenecks": [],
            "post_execution_findings": [
                {
                    "bottleneck_type": "high_cost_ratio",
                    "detail": "원가율 병목이 남아 있습니다.",
                },
                {
                    "bottleneck_type": "high_labor_ratio",
                    "detail": "인건비 병목이 새로 나타났습니다.",
                },
            ],
            "post_execution_financial_result": financial_result(),
            "breakeven_status": {"status": "일부 충족", "reason": "신규 병목 발생"},
            "next_round_pos_data_snapshot": dict(request.post_pos_data),
        }


class CapturingSimulationEngine:
    def __init__(self) -> None:
        self.requests = []

    def run(self, request) -> dict:
        self.requests.append(request)
        return simulation_engine_result()


def reset_schema() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


@pytest.fixture
def integration_context(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Engine, object]]:
    reset_schema()
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    simulation_engine = CapturingSimulationEngine()
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=engine, autoflush=False, autocommit=False),
    )
    app.dependency_overrides[get_outcome_engine] = lambda: FakeOutcomeEngine()
    app.dependency_overrides[get_simulation_engine] = lambda: simulation_engine
    try:
        yield engine, simulation_engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def seed_verification_cycles(engine: Engine, count: int = 2) -> tuple[int, int, str, list[int]]:
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
        snapshot = BusinessSnapshot(
            business=business,
            dataset=dataset,
            reference_date=date(2026, 4, 1),
            snapshot_version="v1",
            monthly_net_sales_amount=7_500_000,
            monthly_expense_amount=6_000_000,
            existing_monthly_repayment_amount=0,
            contribution_margin_rate=Decimal("0.55"),
            average_order_amount=8_000,
            monthly_order_count=2_700,
            online_sales_ratio=Decimal("0.20"),
            employee_count=2,
            source_type=DataSourceType.CALCULATED,
        )
        public_snapshot = PublicDataSnapshot(
            business=business,
            reference_date=date(2026, 3, 31),
            source_name="서울시 상권분석서비스",
            snapshot_version="v1",
            reference_area="서울",
            raw_data={},
        )
        diagnosis = Diagnosis(
            business=business,
            dataset=dataset,
            business_snapshot=snapshot,
            public_data_snapshot=public_snapshot,
            status=DiagnosisStatus.COMPLETED,
            evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
            bottlenecks=[
                Bottleneck(
                    bottleneck_type="HIGH_MATERIAL_COST",
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
        simulation_ids = []
        for offset in range(count):
            simulation = _completed_simulation(
                business.id,
                dataset.id,
                diagnosis.id,
                snapshot.id,
                now - timedelta(days=100 - offset),
            )
            database.add(simulation)
            database.flush()
            simulation_ids.append(simulation.id)
        business_id = business.id
        diagnosis_id = diagnosis.id
    return business_id, diagnosis_id, str(session_id), simulation_ids


def _completed_simulation(
    business_id: int,
    dataset_id: int,
    diagnosis_id: int,
    snapshot_id: int,
    created_at: datetime,
) -> Simulation:
    scenarios = []
    for code in ScenarioCode:
        scenario = Scenario(
            code=code,
            strategy_type="BOTTLENECK_FOCUSED",
            title=f"{code.name}안",
            total_amount=15_000_000,
            monthly_loan_payment=446_205,
            monthly_recurring_cost=100_000,
            cash_after_payment=203_795,
            break_even_additional_revenue=0,
            risk_level=RiskLevel.LOW,
            target_metrics=["COGS_RATIO"],
            risk_reasons=[],
            allocations=[
                ScenarioAllocation(category=category, ratio=Decimal("0.25"), amount=3_750_000)
                for category in AllocationCategory
            ],
        )
        scenarios.append(scenario)
    simulation = Simulation(
        business_id=business_id,
        dataset_id=dataset_id,
        diagnosis_id=diagnosis_id,
        business_snapshot_id=snapshot_id,
        loan_amount=15_000_000,
        loan_interest_rate=Decimal("0.045"),
        loan_term_months=36,
        loan_grace_months=0,
        loan_repayment_type=RepaymentType.EQUAL_PAYMENT,
        status="completed",
        public_data_reference_date=date(2026, 3, 31),
        created_at=created_at,
        scenarios=scenarios,
    )
    simulation.selection = ScenarioSelection(
        scenario=scenarios[0],
        selected_at=created_at,
        locked=False,
    )
    return simulation


def test_verification_api_closes_two_completed_cycles_into_next_simulation(
    integration_context: tuple[Engine, CapturingSimulationEngine],
) -> None:
    engine, simulation_engine = integration_context
    business_id, diagnosis_id, session_id, simulation_ids = seed_verification_cycles(engine)
    client = TestClient(app)
    client.cookies.set("demo_session_id", session_id)
    today = datetime.now(UTC).date().isoformat()

    targets = client.get(f"/api/businesses/{business_id}/verification-targets")
    first_execution = client.post(
        f"/api/simulations/{simulation_ids[0]}/executions",
        json={
            "executionMode": "CUSTOM",
            "executedAt": today,
            "items": [{"name": "자유 개선", "amount": 14_500_000}],
            "unusedAmount": 500_000,
        },
    )
    second_execution = client.post(
        f"/api/simulations/{simulation_ids[1]}/executions",
        json={
            "executionMode": "SAME_AS_A",
            "executedAt": today,
            "items": [],
            "unusedAmount": 0,
        },
    )
    first_data = client.post(
        f"/api/simulations/{simulation_ids[0]}/outcome-data",
        json={
            "sourceType": "MANUAL_INPUT",
            "metrics": {
                "monthlySalesAmount": 8_100_000,
                "operatingProfitAmount": 1_500_000,
                "onlineOrderRatio": 0.25,
                "cashAfterRepaymentAmount": 300_000,
            },
        },
    )
    second_data = client.post(
        f"/api/simulations/{simulation_ids[1]}/outcome-data",
        json={"sourceType": "MOCK"},
    )
    first_outcome = client.post(
        f"/api/simulations/{simulation_ids[0]}/outcomes",
        json={
            "executionId": first_execution.json()["executionId"],
            "outcomeDataId": first_data.json()["outcomeDataId"],
        },
    )
    second_outcome = client.post(
        f"/api/simulations/{simulation_ids[1]}/outcomes",
        json={
            "executionId": second_execution.json()["executionId"],
            "outcomeDataId": second_data.json()["outcomeDataId"],
        },
    )

    assert targets.status_code == 200
    assert len(targets.json()["targets"]) == 2
    assert first_execution.status_code == second_execution.status_code == 201
    assert first_data.status_code == second_data.status_code == 201
    assert first_outcome.status_code == second_outcome.status_code == 201
    assert client.get(f"/api/simulations/{simulation_ids[1]}/outcomes").status_code == 200
    dashboard = client.get(f"/api/businesses/{business_id}/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["loanStatus"]["repaymentDataType"] == "ESTIMATED"
    assert len(dashboard.json()["cycleHistories"]) == 2
    assert dashboard.json()["nextInitialConditions"]["monthly_revenue"] == 8_200_000

    later = client.post(
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
    assert later.status_code == 201
    history = simulation_engine.requests[-1].business_history
    assert [record["round"] for record in history] == [1, 2]
    assert history[0]["selected_allocation"] == {}
    assert history[1]["selected_allocation"] == {
        "marketing_online": 0.25,
        "equipment_interior": 0.25,
        "labor": 0.25,
        "inventory": 0.25,
    }
    assert [item["bottleneck_type"] for item in history[1]["findings"]] == [
        "high_cost_ratio",
        "high_labor_ratio",
    ]

    with Session(engine) as database:
        assert database.scalar(select(func.count()).select_from(Execution)) == 2
        assert database.scalar(select(func.count()).select_from(OutcomeData)) == 2
        assert database.scalar(select(func.count()).select_from(OutcomeComparison)) == 2
        assert database.scalar(select(func.count()).select_from(OutcomeComparisonMetric)) == 8
        assert database.scalar(select(func.count()).select_from(ReassessmentSnapshot)) == 2
        assert database.scalar(select(func.count()).select_from(BottleneckChange)) == 3
        free_count = database.scalar(
            select(func.count())
            .select_from(ExecutionAllocation)
            .where(ExecutionAllocation.category.is_(None))
        )
        assert free_count == 1
        statuses = database.scalars(select(OutcomeComparison.status)).all()
        assert statuses == [OutcomeStatus.MET, OutcomeStatus.PARTIALLY_MET]

    assert (
        client.post(
            f"/api/simulations/{simulation_ids[1]}/outcomes",
            json={
                "executionId": second_execution.json()["executionId"],
                "outcomeDataId": second_data.json()["outcomeDataId"],
            },
        ).status_code
        == 409
    )


def test_outcome_metric_failure_rolls_back_complete_comparison_graph(
    integration_context: tuple[Engine, CapturingSimulationEngine],
) -> None:
    engine, _ = integration_context
    business_id, _, session_id, simulation_ids = seed_verification_cycles(engine, count=1)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("demo_session_id", session_id)
    today = datetime.now(UTC).date().isoformat()
    execution = client.post(
        f"/api/simulations/{simulation_ids[0]}/executions",
        json={
            "executionMode": "CUSTOM",
            "executedAt": today,
            "items": [{"name": "자유 개선", "amount": 15_000_000}],
            "unusedAmount": 0,
        },
    )
    outcome_data = client.post(
        f"/api/simulations/{simulation_ids[0]}/outcome-data",
        json={
            "sourceType": "MANUAL_INPUT",
            "metrics": {
                "monthlySalesAmount": 8_100_000,
                "operatingProfitAmount": 1_500_000,
                "onlineOrderRatio": 0.25,
                "cashAfterRepaymentAmount": 300_000,
            },
        },
    )

    def fail_metric_insert(*_: object) -> None:
        raise RuntimeError("의도적인 outcome metric insert 실패")

    event.listen(OutcomeComparisonMetric, "before_insert", fail_metric_insert)
    try:
        response = client.post(
            f"/api/simulations/{simulation_ids[0]}/outcomes",
            json={
                "executionId": execution.json()["executionId"],
                "outcomeDataId": outcome_data.json()["outcomeDataId"],
            },
        )
    finally:
        event.remove(OutcomeComparisonMetric, "before_insert", fail_metric_insert)

    assert response.status_code == 500
    with Session(engine) as database:
        assert database.scalar(select(func.count()).select_from(OutcomeComparison)) == 0
        assert database.scalar(select(func.count()).select_from(OutcomeComparisonMetric)) == 0
        assert database.scalar(select(func.count()).select_from(ReassessmentSnapshot)) == 0
        assert database.scalar(select(func.count()).select_from(BottleneckChange)) == 0
        assert database.scalar(select(func.count()).select_from(OutcomeData)) == 1
        assert database.scalar(select(func.count()).select_from(Execution)) == 1
