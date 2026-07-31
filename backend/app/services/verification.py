# 결과 검증 대상 조회와 실제 집행 등록의 소유권·상태 규칙을 처리하는 서비스
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.demo_session import DemoSession
from app.domain.enums import (
    AllocationCategory,
    DemoSessionStatus,
    ExecutionType,
    ScenarioCode,
)
from app.domain.execution import Execution, ExecutionAllocation
from app.domain.outcome import OutcomeComparison
from app.domain.simulation import ScenarioSelection, Simulation

SCENARIO_MODE = {
    ExecutionType.SAME_AS_A: ScenarioCode.A,
    ExecutionType.SAME_AS_B: ScenarioCode.B,
    ExecutionType.SAME_AS_C: ScenarioCode.C,
}
CATEGORY_NAME = {
    AllocationCategory.MARKETING_ONLINE: "마케팅·온라인",
    AllocationCategory.EQUIPMENT_INTERIOR: "설비·인테리어",
    AllocationCategory.LABOR: "인력",
    AllocationCategory.INVENTORY: "재고",
}
MIN_VERIFICATION_DAYS = 90


@dataclass(frozen=True)
class PlanSummary:
    plan_code: str
    title: str


@dataclass(frozen=True)
class VerificationTarget:
    simulation_id: int
    saved_at: datetime
    days_elapsed: int
    execution_registered: bool
    business_name: str
    region: str
    loan_amount: int
    plan_summaries: tuple[PlanSummary, ...]


@dataclass(frozen=True)
class VerificationTargets:
    business_id: int
    targets: tuple[VerificationTarget, ...]


@dataclass(frozen=True)
class ExecutionItemCommand:
    name: str
    amount: int


@dataclass(frozen=True)
class ExecutionCreationCommand:
    simulation_id: int
    mode: ExecutionType
    executed_at: date
    items: tuple[ExecutionItemCommand, ...]
    unused_amount: int
    note: str | None = None


@dataclass(frozen=True)
class ExecutionCreated:
    execution_id: int
    simulation_id: int
    execution_mode: str
    total_executed_amount: int
    saved_at: datetime


def require_owned_business(
    database: Session,
    business_id: int,
    session_cookie: str | None,
) -> Business:
    session_id = _parse_session_id(session_cookie)
    session = database.get(DemoSession, session_id) if session_id is not None else None
    business = database.get(Business, business_id)
    now = datetime.now(UTC)
    if (
        session is None
        or business is None
        or business.demo_session_id != session_id
        or session.status is not DemoSessionStatus.ACTIVE
        or session.expires_at <= now
    ):
        raise _resource_not_found()
    return business


def require_owned_simulation(
    database: Session,
    simulation_id: int,
    session_cookie: str | None,
    *,
    with_for_update: bool = False,
) -> Simulation:
    simulation = database.get(
        Simulation,
        simulation_id,
        with_for_update=with_for_update,
    )
    if simulation is None or simulation.business_id is None:
        raise _resource_not_found()
    require_owned_business(database, simulation.business_id, session_cookie)
    return simulation


class VerificationService:
    def __init__(self, database: Session) -> None:
        self.database = database

    def list_targets(
        self,
        business_id: int,
        include_completed: bool,
        session_cookie: str | None,
        *,
        today: date | None = None,
    ) -> VerificationTargets:
        business = require_owned_business(self.database, business_id, session_cookie)
        as_of = today or datetime.now(UTC).date()
        simulations = (
            self.database.scalars(
                select(Simulation)
                .where(Simulation.business_id == business_id)
                .options(
                    selectinload(Simulation.selection),
                    selectinload(Simulation.scenarios),
                )
            )
            .unique()
            .all()
        )
        simulation_ids = [simulation.id for simulation in simulations if simulation.id is not None]
        executions = (
            self.database.scalars(
                select(Execution).where(Execution.simulation_id.in_(simulation_ids))
            ).all()
            if simulation_ids
            else []
        )
        comparisons = (
            self.database.scalars(
                select(OutcomeComparison).where(OutcomeComparison.simulation_id.in_(simulation_ids))
            ).all()
            if simulation_ids
            else []
        )
        execution_ids = {execution.simulation_id for execution in executions}
        completed_ids = {comparison.simulation_id for comparison in comparisons}

        targets = []
        for simulation in sorted(
            simulations,
            key=lambda item: (item.created_at, item.id),
        ):
            if (
                simulation.id is None
                or simulation.business_id != business_id
                or simulation.status.upper() != "COMPLETED"
                or simulation.selection is None
            ):
                continue
            days_elapsed = _days_elapsed(simulation, as_of)
            if days_elapsed < MIN_VERIFICATION_DAYS:
                continue
            if not include_completed and simulation.id in completed_ids:
                continue
            targets.append(
                VerificationTarget(
                    simulation_id=simulation.id,
                    saved_at=simulation.created_at,
                    days_elapsed=days_elapsed,
                    execution_registered=simulation.id in execution_ids,
                    business_name=business.name,
                    region=business.region,
                    loan_amount=simulation.loan_amount,
                    plan_summaries=tuple(
                        PlanSummary(plan_code=scenario.code.name, title=scenario.title)
                        for scenario in sorted(
                            simulation.scenarios,
                            key=lambda item: item.code.value,
                        )
                    ),
                )
            )
        return VerificationTargets(business_id=business_id, targets=tuple(targets))

    def create_execution(
        self,
        command: ExecutionCreationCommand,
        session_cookie: str | None,
        *,
        now: datetime | None = None,
    ) -> ExecutionCreated:
        saved_at = now or datetime.now(UTC)
        with self.database.begin():
            simulation = require_owned_simulation(
                self.database,
                command.simulation_id,
                session_cookie,
                with_for_update=True,
            )
            _require_verification_ready(simulation, saved_at.date())
            if simulation.selection is None or simulation.selection.id is None:
                raise ApiError(
                    409,
                    "SELECTION_REQUIRED",
                    "최종 선택이 있는 시뮬레이션만 집행을 등록할 수 있습니다.",
                )
            selection = self.database.get(
                ScenarioSelection,
                simulation.selection.id,
                with_for_update=True,
            )
            if selection is None:
                raise ApiError(
                    409,
                    "SELECTION_REQUIRED",
                    "최종 선택이 있는 시뮬레이션만 집행을 등록할 수 있습니다.",
                )
            existing = self.database.scalars(
                select(Execution).where(Execution.simulation_id == simulation.id)
            ).all()
            if any(item.simulation_id == simulation.id for item in existing):
                raise ApiError(
                    409,
                    "EXECUTION_ALREADY_EXISTS",
                    "이미 실제 집행이 등록된 시뮬레이션입니다.",
                )
            if command.executed_at > saved_at.date():
                raise ApiError(
                    400,
                    "INVALID_EXECUTION_DATE",
                    "집행일은 미래 날짜일 수 없습니다.",
                )

            allocations = _build_allocations(command, simulation)
            total_amount = sum(item.amount for item in allocations)
            if (
                command.unused_amount < 0
                or total_amount + command.unused_amount != simulation.loan_amount
            ):
                raise ApiError(
                    400,
                    "INVALID_EXECUTION_TOTAL",
                    "집행금액과 미집행금액의 합은 대출금액과 같아야 합니다.",
                )
            execution = Execution(
                simulation_id=simulation.id,
                selection_id=selection.id,
                execution_type=command.mode,
                total_amount=total_amount,
                unused_amount=command.unused_amount,
                executed_at=datetime.combine(command.executed_at, time.min, UTC),
                note=command.note,
                selection=selection,
                allocations=allocations,
            )
            execution.validate_amounts(simulation.loan_amount)
            selection.lock()
            self.database.add(execution)
            self.database.flush()
            if execution.id is None:
                raise RuntimeError("집행 식별자가 생성되지 않았습니다.")

        return ExecutionCreated(
            execution_id=execution.id,
            simulation_id=simulation.id,
            execution_mode=execution.execution_type.name,
            total_executed_amount=execution.total_amount,
            saved_at=saved_at,
        )


def _build_allocations(
    command: ExecutionCreationCommand,
    simulation: Simulation,
) -> list[ExecutionAllocation]:
    scenario_code = SCENARIO_MODE.get(command.mode)
    if scenario_code is not None:
        if command.items or command.unused_amount != 0:
            raise ApiError(
                400,
                "INVALID_EXECUTION_ITEM",
                "시나리오 복사 모드에는 자유 집행 항목이나 미집행금액을 입력할 수 없습니다.",
            )
        scenario = next(
            (item for item in simulation.scenarios if item.code is scenario_code),
            None,
        )
        if scenario is None:
            raise ApiError(409, "SCENARIO_NOT_FOUND", "복사할 시나리오를 찾을 수 없습니다.")
        return [
            ExecutionAllocation(
                name=CATEGORY_NAME[item.category],
                category=item.category,
                amount=item.amount,
            )
            for item in sorted(scenario.allocations, key=lambda value: value.category.value)
        ]

    if command.mode not in {ExecutionType.MIXED, ExecutionType.CUSTOM} or not command.items:
        raise ApiError(
            400,
            "INVALID_EXECUTION_ITEM",
            "자유 집행 모드에는 하나 이상의 항목이 필요합니다.",
        )
    allocations = []
    for item in command.items:
        name = item.name.strip()
        if not name or item.amount <= 0:
            raise ApiError(
                400,
                "INVALID_EXECUTION_ITEM",
                "집행 항목 이름과 0보다 큰 금액이 필요합니다.",
            )
        allocations.append(ExecutionAllocation(name=name, category=None, amount=item.amount))
    return allocations


def _require_verification_ready(simulation: Simulation, today: date) -> None:
    if simulation.status.upper() != "COMPLETED":
        raise ApiError(
            409,
            "SIMULATION_NOT_COMPLETED",
            "완료된 시뮬레이션만 결과를 검증할 수 있습니다.",
        )
    if _days_elapsed(simulation, today) < MIN_VERIFICATION_DAYS:
        raise ApiError(
            409,
            "VERIFICATION_NOT_READY",
            "시뮬레이션 저장 후 90일부터 결과를 검증할 수 있습니다.",
        )


def _days_elapsed(simulation: Simulation, today: date) -> int:
    if simulation.created_at is None:
        raise RuntimeError("시뮬레이션 저장 시각이 없습니다.")
    return (today - simulation.created_at.astimezone(UTC).date()).days


def _parse_session_id(value: str | None) -> UUID | None:
    try:
        return UUID(value) if value else None
    except ValueError:
        return None


def _resource_not_found() -> ApiError:
    return ApiError(404, "RESOURCE_NOT_FOUND", "요청한 자원을 찾을 수 없습니다.")
