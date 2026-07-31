# 시뮬레이션 생성 서비스의 소유권·선행 상태·원자적 영속화를 검증하는 테스트
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.dataset import BusinessSnapshot, Dataset, PublicDataSnapshot
from app.domain.diagnosis import Bottleneck, Diagnosis
from app.domain.enums import (
    BottleneckSeverity,
    DatasetStatus,
    DataSourceType,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
    RepaymentType,
)
from app.domain.simulation import Scenario, ScenarioSelection, Simulation
from app.services.simulation import SimulationCreationCommand, SimulationService
from app.services.simulation_engine import SimulationGenerationError

SESSION_ID = UUID("12345678-1234-5678-1234-567812345678")
SESSION_COOKIE = str(SESSION_ID)


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


class FakeDatabase:
    def __init__(self) -> None:
        business = Business(
            id=7,
            demo_session_id=SESSION_ID,
            name="테스트 카페",
            region="서울",
            industry="카페",
            employee_count=2,
            primary_sales_channels=[],
        )
        dataset = Dataset(
            id=17,
            business_id=7,
            status=DatasetStatus.READY,
            dataset_version="v1",
        )
        snapshot = BusinessSnapshot(
            id=27,
            business_id=7,
            dataset_id=17,
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
            id=37,
            business_id=7,
            reference_date=date(2026, 6, 30),
            source_name="서울시 상권분석서비스",
            snapshot_version="v1",
            reference_area="서울",
            raw_data={},
        )
        bottleneck = Bottleneck(
            id=201,
            diagnosis_id=31,
            bottleneck_type="high_cost_ratio",
            detail="원가율이 업계 참고치보다 높습니다.",
            severity=BottleneckSeverity.SEVERE,
            evidence_source_type=DataSourceType.DOMAIN_ASSUMPTION,
            evidence_description="업계 참고 원가율과 비교했습니다.",
            related_categories=["equipment_interior"],
        )
        diagnosis = Diagnosis(
            id=31,
            business_id=7,
            dataset_id=17,
            business_snapshot_id=27,
            public_data_snapshot_id=37,
            status=DiagnosisStatus.COMPLETED,
            evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
            dataset=dataset,
            business_snapshot=snapshot,
            public_data_snapshot=public_snapshot,
            bottlenecks=[bottleneck],
        )
        self.business = business
        self.dataset = dataset
        self.diagnosis = diagnosis
        self.saved_simulation: Simulation | None = None
        self.selection: ScenarioSelection | None = None
        self.rollback_count = 0

    def get(self, model, object_id):
        if model is Business and object_id == self.business.id:
            return self.business
        if model is Diagnosis and object_id == self.diagnosis.id:
            return self.diagnosis
        if model is Simulation and self.saved_simulation is not None:
            if object_id == self.saved_simulation.id:
                return self.saved_simulation
        if model is Scenario and self.saved_simulation is not None:
            return next(
                (
                    scenario
                    for scenario in self.saved_simulation.scenarios
                    if scenario.id == object_id
                ),
                None,
            )
        return None

    def rollback(self) -> None:
        self.rollback_count += 1

    @contextmanager
    def begin(self):
        yield

    def add(self, value) -> None:
        if isinstance(value, Simulation):
            value.id = 45
            value.created_at = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
            for scenario_id, scenario in enumerate(value.scenarios, start=101):
                scenario.id = scenario_id
                scenario.simulation_id = value.id
            self.saved_simulation = value
        if isinstance(value, ScenarioSelection):
            value.id = 501
            self.selection = value

    def flush(self) -> None:
        pass


class FakeEngine:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database
        self.request = None
        self.run_count = 0

    def run(self, request):
        assert self.database.rollback_count == 1
        self.request = request
        self.run_count += 1
        return engine_result()


class FailingEngine:
    def run(self, request):
        raise SimulationGenerationError("내부 AI 오류")


@pytest.fixture
def service() -> SimulationService:
    database = FakeDatabase()
    return SimulationService(database, FakeEngine(database))


def valid_command(
    *,
    business_id: int = 7,
    diagnosis_id: int = 31,
) -> SimulationCreationCommand:
    return SimulationCreationCommand(
        business_id=business_id,
        diagnosis_id=diagnosis_id,
        loan_amount=15_000_000,
        annual_interest_rate=Decimal("0.045"),
        term_months=36,
        grace_months=0,
        repayment_type=RepaymentType.EQUAL_PAYMENT,
    )


def test_create_rejects_diagnosis_owned_by_another_business(
    service: SimulationService,
) -> None:
    service.database.diagnosis.business_id = 8

    with pytest.raises(ApiError) as caught:
        service.create(valid_command(), SESSION_COOKIE)

    assert caught.value.status_code == 404


def test_create_rejects_running_diagnosis(service: SimulationService) -> None:
    service.database.diagnosis.status = DiagnosisStatus.RUNNING

    with pytest.raises(ApiError) as caught:
        service.create(valid_command(), SESSION_COOKIE)

    assert caught.value.code == "DIAGNOSIS_NOT_COMPLETED"
    assert caught.value.status_code == 409


def test_create_rejects_dataset_that_is_not_ready(service: SimulationService) -> None:
    service.database.dataset.status = DatasetStatus.PARSING

    with pytest.raises(ApiError) as caught:
        service.create(valid_command(), SESSION_COOKIE)

    assert caught.value.code == "DATASET_NOT_READY"
    assert caught.value.status_code == 409


def test_create_maps_stored_diagnosis_to_immutable_engine_request(
    service: SimulationService,
) -> None:
    service.create(valid_command(), SESSION_COOKIE)

    request = service.engine.request
    assert request.baseline_monthly_revenue == 7_500_000
    assert request.average_daily_customers == 90
    assert request.findings == (
        {
            "bottleneck_type": "high_cost_ratio",
            "title": "원가율 상승",
            "detail": "원가율이 업계 참고치보다 높습니다.",
            "comparison_chip": "원가율이 업계 참고치보다 높습니다.",
            "evidence_source": "업계 참고 원가율과 비교했습니다.",
            "methodology": "업계 참고 원가율과 비교했습니다.",
            "severity": "심각",
            "confidence_badge": "보통",
            "suggested_category": "equipment_interior",
        },
    )


def test_create_does_not_persist_when_engine_fails() -> None:
    database = FakeDatabase()
    service = SimulationService(database, FailingEngine())

    with pytest.raises(ApiError) as caught:
        service.create(valid_command(), SESSION_COOKIE)

    assert caught.value.code == "SIMULATION_GENERATION_FAILED"
    assert caught.value.status_code == 502
    assert database.saved_simulation is None


def test_create_persists_complete_scenario_graph(service: SimulationService) -> None:
    created = service.create(valid_command(), SESSION_COOKIE)
    simulation = service.database.saved_simulation

    assert created.simulation_id == 45
    assert created.status == "COMPLETED"
    assert simulation is not None
    assert simulation.status == "completed"
    assert simulation.public_data_reference_date == date(2026, 6, 30)
    assert [scenario.code.value for scenario in simulation.scenarios] == ["A", "B", "C"]
    assert sum(len(scenario.allocations) for scenario in simulation.scenarios) == 12
    assert all(
        {reason.source_type for reason in scenario.reasons}
        == {DataSourceType.CALCULATED, DataSourceType.AI_GENERATED_TEXT}
        for scenario in simulation.scenarios
    )


def test_get_result_orders_scenarios_and_allocations(
    service: SimulationService,
) -> None:
    service.create(valid_command(), SESSION_COOKIE)

    result = service.get_result(45, SESSION_COOKIE)

    assert result.status == "COMPLETED"
    assert result.selected_scenario_id is None
    assert [scenario.scenario_code for scenario in result.scenarios] == ["A", "B", "C"]
    assert [item.category for item in result.scenarios[0].allocations] == [
        "MARKETING_ONLINE",
        "EQUIPMENT_INTERIOR",
        "LABOR",
        "INVENTORY",
    ]
    assert result.scenarios[0].reasons[0].source_type == "CALCULATED"


def test_comparison_never_returns_a_recommendation(
    service: SimulationService,
) -> None:
    service.create(valid_command(), SESSION_COOKIE)
    engine_calls = service.engine.run_count

    comparison = service.get_comparison(45, SESSION_COOKIE)

    assert comparison.recommendation_provided is False
    assert comparison.scenarios[0].financial_result.risk_level in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }
    assert "추천" in comparison.disclaimer
    assert service.engine.run_count == engine_calls


def test_selection_rejects_scenario_from_another_simulation(
    service: SimulationService,
) -> None:
    service.create(valid_command(), SESSION_COOKIE)

    with pytest.raises(ApiError) as caught:
        service.select_scenario(45, 999, SESSION_COOKIE)

    assert caught.value.code == "SCENARIO_NOT_IN_SIMULATION"
    assert caught.value.status_code == 400


def test_selection_can_be_created_and_changed_before_lock(
    service: SimulationService,
) -> None:
    service.create(valid_command(), SESSION_COOKIE)

    selected = service.select_scenario(45, 101, SESSION_COOKIE)
    changed = service.select_scenario(45, 102, SESSION_COOKIE)

    assert selected.selected_scenario_id == 101
    assert changed.selected_scenario_id == 102
    assert changed.locked is False
    assert changed.selected_at.tzinfo is not None


def test_selection_cannot_change_after_lock(service: SimulationService) -> None:
    service.create(valid_command(), SESSION_COOKIE)
    service.select_scenario(45, 101, SESSION_COOKIE)
    service.database.selection.lock()

    with pytest.raises(ApiError) as caught:
        service.select_scenario(45, 102, SESSION_COOKIE)

    assert caught.value.code == "SELECTION_LOCKED"
    assert caught.value.status_code == 409
