# 90일 검증 대상과 실제 집행의 소유권·합계·잠금 규칙을 검증하는 테스트
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.demo_session import DemoSession
from app.domain.enums import (
    AllocationCategory,
    DemoSessionStatus,
    ExecutionType,
    OutcomeStatus,
    RepaymentType,
    ScenarioCode,
)
from app.domain.execution import Execution
from app.domain.outcome import OutcomeComparison
from app.domain.simulation import Scenario, ScenarioAllocation, ScenarioSelection, Simulation
from app.services.verification import (
    ExecutionCreationCommand,
    ExecutionItemCommand,
    VerificationService,
)

SESSION_ID = UUID("12345678-1234-5678-1234-567812345678")
SESSION_COOKIE = str(SESSION_ID)
TODAY = date(2026, 7, 31)
NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


class FakeScalarResult:
    def __init__(self, values) -> None:
        self.values = list(values)

    def unique(self):
        return self

    def all(self):
        return list(self.values)


class FakeDatabase:
    def __init__(self) -> None:
        self.session = DemoSession(
            id=SESSION_ID,
            last_accessed_at=NOW,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            status=DemoSessionStatus.ACTIVE,
        )
        self.business = Business(
            id=7,
            demo_session_id=SESSION_ID,
            name="청춘카페",
            region="서울특별시 강남구",
            industry="카페",
            employee_count=2,
            primary_sales_channels=[],
        )
        self.simulations = [
            make_simulation(44, 89),
            make_simulation(45, 90),
            make_simulation(46, 90),
            make_simulation(47, 90),
            make_simulation(48, 90, with_selection=False),
        ]
        self.executions = [
            Execution(
                id=81,
                simulation_id=46,
                selection_id=546,
                execution_type=ExecutionType.SAME_AS_A,
                total_amount=15_000_000,
                unused_amount=0,
            )
        ]
        self.comparisons = [
            OutcomeComparison(
                id=91,
                simulation_id=47,
                execution_id=82,
                outcome_data_id=83,
                status=OutcomeStatus.MET,
            )
        ]
        self.added_execution: Execution | None = None

    def get(self, model, object_id, **kwargs):
        if model is DemoSession and object_id == self.session.id:
            return self.session
        if model is Business and object_id == self.business.id:
            return self.business
        if model is Simulation:
            return next(
                (simulation for simulation in self.simulations if simulation.id == object_id),
                None,
            )
        if model is ScenarioSelection:
            return next(
                (
                    simulation.selection
                    for simulation in self.simulations
                    if simulation.selection is not None and simulation.selection.id == object_id
                ),
                None,
            )
        return None

    def scalars(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        if entity is Simulation:
            return FakeScalarResult(self.simulations)
        if entity is Execution:
            return FakeScalarResult(self.executions)
        if entity is OutcomeComparison:
            return FakeScalarResult(self.comparisons)
        return FakeScalarResult([])

    @contextmanager
    def begin(self):
        yield

    def add(self, value) -> None:
        if isinstance(value, Execution):
            value.id = 100
            value.created_at = NOW
            self.executions.append(value)
            self.added_execution = value

    def flush(self) -> None:
        pass


def make_simulation(
    simulation_id: int,
    days_elapsed: int,
    *,
    with_selection: bool = True,
) -> Simulation:
    scenarios = []
    for index, code in enumerate(ScenarioCode, start=1):
        allocations = [
            ScenarioAllocation(
                id=simulation_id * 100 + category_index,
                category=category,
                ratio=Decimal("0.25"),
                amount=3_750_000,
            )
            for category_index, category in enumerate(AllocationCategory, start=1)
        ]
        scenario = Scenario(
            id=simulation_id * 10 + index,
            simulation_id=simulation_id,
            code=code,
            strategy_type="TEST",
            title=f"{code.value}안",
            total_amount=15_000_000,
            allocations=allocations,
            target_metrics=[],
            risk_reasons=[],
        )
        scenarios.append(scenario)
    selection = None
    if with_selection:
        selection = ScenarioSelection(
            id=500 + simulation_id,
            simulation_id=simulation_id,
            scenario_id=scenarios[0].id,
            scenario=scenarios[0],
            locked=False,
        )
    simulation = Simulation(
        id=simulation_id,
        business_id=7,
        loan_amount=15_000_000,
        loan_interest_rate=Decimal("0.045"),
        loan_term_months=36,
        loan_grace_months=0,
        loan_repayment_type=RepaymentType.EQUAL_PAYMENT,
        status="completed",
        scenarios=scenarios,
        selection=selection,
    )
    simulation.created_at = datetime.combine(
        TODAY - timedelta(days=days_elapsed),
        datetime.min.time(),
        UTC,
    )
    return simulation


@pytest.fixture
def service() -> VerificationService:
    return VerificationService(FakeDatabase())


def custom_command(
    *,
    simulation_id: int = 45,
    executed_at: date = date(2026, 7, 30),
    items: tuple[ExecutionItemCommand, ...] = (ExecutionItemCommand("저녁 광고", 14_500_000),),
    unused_amount: int = 500_000,
) -> ExecutionCreationCommand:
    return ExecutionCreationCommand(
        simulation_id=simulation_id,
        mode=ExecutionType.CUSTOM,
        executed_at=executed_at,
        items=items,
        unused_amount=unused_amount,
    )


def test_targets_start_on_day_90_and_keep_execution_only_cycle(
    service: VerificationService,
) -> None:
    targets = service.list_targets(
        business_id=7,
        include_completed=False,
        session_cookie=SESSION_COOKIE,
        today=TODAY,
    )

    assert [target.simulation_id for target in targets.targets] == [45, 46]
    assert targets.targets[1].execution_registered is True


def test_targets_include_completed_only_when_requested(service: VerificationService) -> None:
    targets = service.list_targets(7, True, SESSION_COOKIE, today=TODAY)

    assert [target.simulation_id for target in targets.targets] == [45, 46, 47]


def test_custom_execution_locks_selection_and_preserves_free_names(
    service: VerificationService,
) -> None:
    created = service.create_execution(custom_command(), SESSION_COOKIE, now=NOW)

    assert created.total_executed_amount == 14_500_000
    assert service.database.simulations[1].selection.locked is True
    assert service.database.added_execution.allocations[0].name == "저녁 광고"
    assert service.database.added_execution.allocations[0].category is None


def test_same_as_scenario_copies_categories_and_names(service: VerificationService) -> None:
    created = service.create_execution(
        ExecutionCreationCommand(
            simulation_id=45,
            mode=ExecutionType.SAME_AS_B,
            executed_at=date(2026, 7, 30),
            items=(),
            unused_amount=0,
        ),
        SESSION_COOKIE,
        now=NOW,
    )

    assert created.total_executed_amount == 15_000_000
    assert {item.category for item in service.database.added_execution.allocations} == set(
        AllocationCategory
    )
    assert all(item.name.strip() for item in service.database.added_execution.allocations)


@pytest.mark.parametrize(
    ("command", "code"),
    [
        (custom_command(simulation_id=44), "VERIFICATION_NOT_READY"),
        (custom_command(simulation_id=48), "SELECTION_REQUIRED"),
        (custom_command(executed_at=date(2026, 8, 1)), "INVALID_EXECUTION_DATE"),
        (custom_command(unused_amount=0), "INVALID_EXECUTION_TOTAL"),
        (
            custom_command(items=(ExecutionItemCommand(" ", 14_500_000),)),
            "INVALID_EXECUTION_ITEM",
        ),
    ],
)
def test_execution_rejects_invalid_state_or_input(
    service: VerificationService,
    command: ExecutionCreationCommand,
    code: str,
) -> None:
    with pytest.raises(ApiError) as caught:
        service.create_execution(command, SESSION_COOKIE, now=NOW)

    assert caught.value.code == code


def test_execution_rejects_wrong_session(service: VerificationService) -> None:
    with pytest.raises(ApiError) as caught:
        service.create_execution(custom_command(), str(UUID(int=9)), now=NOW)

    assert caught.value.status_code == 404


def test_execution_rejects_duplicate(service: VerificationService) -> None:
    service.create_execution(custom_command(), SESSION_COOKIE, now=NOW)

    with pytest.raises(ApiError) as caught:
        service.create_execution(custom_command(), SESSION_COOKIE, now=NOW)

    assert caught.value.code == "EXECUTION_ALREADY_EXISTS"
