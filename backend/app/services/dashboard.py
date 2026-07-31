# 저장된 검증 사이클과 대출 상환 추정치를 읽기 전용으로 투영하는 서비스
import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.dataset import BusinessSnapshot
from app.domain.enums import BottleneckChangeType, RepaymentType
from app.domain.execution import Execution
from app.domain.outcome import OutcomeComparison, OutcomeData, ReassessmentSnapshot
from app.domain.simulation import ScenarioSelection, Simulation
from app.services.verification import require_owned_business

FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class DashboardBusiness:
    business_id: int
    name: str
    region: str
    industry: str


@dataclass(frozen=True)
class LoanStatusResult:
    loan_amount: int
    monthly_repayment_amount: int
    paid_amount: int
    estimated_remaining_principal: int
    progress_rate: Decimal
    repayment_data_type: str


@dataclass(frozen=True)
class DashboardMetricTrend:
    simulation_id: int
    metric_code: str
    before_value: Decimal | None
    after_value: Decimal | None
    unit: str
    status: str
    recorded_at: datetime


@dataclass(frozen=True)
class SelectedPlanSummary:
    scenario_id: int
    scenario_code: str
    title: str


@dataclass(frozen=True)
class ExecutionCycleSummary:
    execution_id: int
    execution_mode: str
    executed_at: datetime | None
    total_executed_amount: int
    unused_amount: int


@dataclass(frozen=True)
class OutcomeCycleSummary:
    outcome_id: int
    overall_status: str
    completed_at: datetime


@dataclass(frozen=True)
class CycleHistory:
    simulation_id: int
    simulated_at: datetime
    selected_plan: SelectedPlanSummary | None
    execution: ExecutionCycleSummary | None
    outcome: OutcomeCycleSummary


@dataclass(frozen=True)
class UnresolvedBottleneck:
    bottleneck_type: str
    change_type: str
    detail: str | None


@dataclass(frozen=True)
class DashboardResult:
    business: DashboardBusiness
    loan_status: LoanStatusResult | None
    metric_trends: tuple[DashboardMetricTrend, ...]
    cycle_histories: tuple[CycleHistory, ...]
    unresolved_bottlenecks: tuple[UnresolvedBottleneck, ...]
    next_initial_conditions: dict | None


def estimate_loan_status(
    simulation: Simulation,
    execution: Execution,
    as_of: date,
) -> LoanStatusResult:
    executed_at = execution.executed_at or execution.created_at
    executed_on = executed_at.date()
    elapsed_months = min(
        max(_complete_months(executed_on, as_of), 0),
        simulation.loan_term_months,
    )
    principal = Decimal(simulation.loan_amount)
    monthly_rate = Decimal(simulation.loan_interest_rate) / Decimal(12)
    grace_elapsed = min(elapsed_months, simulation.loan_grace_months)
    amortizing_elapsed = max(elapsed_months - simulation.loan_grace_months, 0)
    amortizing_months = simulation.loan_term_months - simulation.loan_grace_months
    monthly_payment = _representative_monthly_payment(simulation)
    grace_interest = _round_won(principal * monthly_rate)
    paid_amount = grace_interest * grace_elapsed

    if simulation.loan_repayment_type is RepaymentType.BULLET_PAYMENT:
        paid_amount += monthly_payment * amortizing_elapsed
        remaining_principal = simulation.loan_amount
        if elapsed_months == simulation.loan_term_months:
            paid_amount += simulation.loan_amount
            remaining_principal = 0
    elif simulation.loan_repayment_type is RepaymentType.EQUAL_PRINCIPAL:
        principal_portion = principal / Decimal(amortizing_months)
        interest_paid = Decimal()
        for month in range(amortizing_elapsed):
            balance_before_payment = principal - principal_portion * month
            interest_paid += Decimal(_round_won(balance_before_payment * monthly_rate))
        principal_paid = principal_portion * amortizing_elapsed
        paid_amount += _round_won(principal_paid + interest_paid)
        remaining_principal = _round_won(principal - principal_paid)
    else:
        paid_amount += monthly_payment * amortizing_elapsed
        remaining_principal = _equal_payment_balance(
            principal,
            monthly_rate,
            monthly_payment,
            amortizing_elapsed,
            amortizing_months,
        )

    if elapsed_months == simulation.loan_term_months:
        remaining_principal = 0
    progress = (Decimal(elapsed_months) / Decimal(simulation.loan_term_months)).quantize(
        FOUR_PLACES,
        rounding=ROUND_HALF_UP,
    )
    return LoanStatusResult(
        loan_amount=simulation.loan_amount,
        monthly_repayment_amount=monthly_payment,
        paid_amount=paid_amount,
        estimated_remaining_principal=remaining_principal,
        progress_rate=progress,
        repayment_data_type="ESTIMATED",
    )


class DashboardService:
    def __init__(self, database: Session) -> None:
        self.database = database

    def get(
        self,
        business_id: int,
        session_cookie: str | None,
        *,
        as_of: date | None = None,
    ) -> DashboardResult:
        business = require_owned_business(self.database, business_id, session_cookie)
        simulations = (
            self.database.scalars(
                select(Simulation)
                .where(Simulation.business_id == business_id)
                .options(
                    selectinload(Simulation.scenarios),
                    selectinload(Simulation.selection).selectinload(ScenarioSelection.scenario),
                )
            )
            .unique()
            .all()
        )
        simulations = sorted(
            (item for item in simulations if item.business_id == business_id),
            key=lambda item: (item.created_at, item.id),
        )
        simulation_by_id = {item.id: item for item in simulations if item.id is not None}
        simulation_ids = list(simulation_by_id)
        executions = self._executions(simulation_ids)
        outcome_data = self._outcome_data(simulation_ids)
        comparisons = self._comparisons(simulation_ids)
        execution_by_simulation = {item.simulation_id: item for item in executions}
        outcome_by_simulation = {item.simulation_id: item for item in outcome_data}
        comparison_by_simulation = {item.simulation_id: item for item in comparisons}

        loan_status = None
        if executions:
            latest_execution = max(executions, key=_execution_sort_key)
            simulation = simulation_by_id.get(latest_execution.simulation_id)
            if simulation is not None:
                loan_status = estimate_loan_status(
                    simulation,
                    latest_execution,
                    as_of or datetime.now(UTC).date(),
                )

        metric_trends = self._metric_trends(simulation_by_id, comparisons)
        cycle_histories = tuple(
            self._cycle_history(
                simulation,
                execution_by_simulation.get(simulation.id),
                comparison,
            )
            for simulation in simulations
            if (comparison := comparison_by_simulation.get(simulation.id)) is not None
            and simulation.id in outcome_by_simulation
        )
        latest_comparison = max(comparisons, key=_comparison_sort_key) if comparisons else None
        unresolved = _unresolved_bottlenecks(latest_comparison)
        next_initial_conditions = _next_initial_conditions(
            latest_comparison,
            outcome_by_simulation,
        )
        return DashboardResult(
            business=DashboardBusiness(
                business_id=business.id,
                name=business.name,
                region=business.region,
                industry=business.industry,
            ),
            loan_status=loan_status,
            metric_trends=metric_trends,
            cycle_histories=cycle_histories,
            unresolved_bottlenecks=unresolved,
            next_initial_conditions=next_initial_conditions,
        )

    def _executions(self, simulation_ids: list[int]) -> list[Execution]:
        if not simulation_ids:
            return []
        return self.database.scalars(
            select(Execution).where(Execution.simulation_id.in_(simulation_ids))
        ).all()

    def _outcome_data(self, simulation_ids: list[int]) -> list[OutcomeData]:
        if not simulation_ids:
            return []
        return (
            self.database.scalars(
                select(OutcomeData)
                .where(OutcomeData.simulation_id.in_(simulation_ids))
                .options(selectinload(OutcomeData.observed_business_snapshot))
            )
            .unique()
            .all()
        )

    def _comparisons(self, simulation_ids: list[int]) -> list[OutcomeComparison]:
        if not simulation_ids:
            return []
        return (
            self.database.scalars(
                select(OutcomeComparison)
                .where(OutcomeComparison.simulation_id.in_(simulation_ids))
                .options(
                    selectinload(OutcomeComparison.metrics),
                    selectinload(OutcomeComparison.reassessment_snapshot).selectinload(
                        ReassessmentSnapshot.changes
                    ),
                )
            )
            .unique()
            .all()
        )

    def _metric_trends(
        self,
        simulation_by_id: dict[int, Simulation],
        comparisons: list[OutcomeComparison],
    ) -> tuple[DashboardMetricTrend, ...]:
        trends = []
        for comparison in sorted(comparisons, key=_comparison_sort_key):
            simulation = simulation_by_id.get(comparison.simulation_id)
            if simulation is None or simulation.business_snapshot_id is None:
                continue
            baseline = self.database.get(
                BusinessSnapshot,
                simulation.business_snapshot_id,
            )
            if baseline is None:
                continue
            before_values = {
                "MONTHLY_SALES": Decimal(baseline.monthly_net_sales_amount),
                "OPERATING_PROFIT": Decimal(
                    baseline.monthly_net_sales_amount - baseline.monthly_expense_amount
                ),
                "ONLINE_ORDER_RATIO": baseline.online_sales_ratio,
                "CASH_AFTER_REPAYMENT": None,
            }
            for metric in sorted(
                comparison.metrics,
                key=lambda item: _metric_order(item.metric_code),
            ):
                trends.append(
                    DashboardMetricTrend(
                        simulation_id=comparison.simulation_id,
                        metric_code=metric.metric_code,
                        before_value=before_values.get(metric.metric_code),
                        after_value=metric.observed_value,
                        unit=metric.unit,
                        status=metric.status.name,
                        recorded_at=comparison.created_at,
                    )
                )
        return tuple(trends)

    def _cycle_history(
        self,
        simulation: Simulation,
        execution: Execution | None,
        comparison: OutcomeComparison,
    ) -> CycleHistory:
        selected_plan = None
        if simulation.selection is not None and simulation.selection.scenario is not None:
            scenario = simulation.selection.scenario
            selected_plan = SelectedPlanSummary(
                scenario_id=scenario.id,
                scenario_code=scenario.code.name,
                title=scenario.title,
            )
        execution_summary = None
        if execution is not None:
            execution_summary = ExecutionCycleSummary(
                execution_id=execution.id,
                execution_mode=execution.execution_type.name,
                executed_at=execution.executed_at,
                total_executed_amount=execution.total_amount,
                unused_amount=execution.unused_amount,
            )
        return CycleHistory(
            simulation_id=simulation.id,
            simulated_at=simulation.created_at,
            selected_plan=selected_plan,
            execution=execution_summary,
            outcome=OutcomeCycleSummary(
                outcome_id=comparison.id,
                overall_status=comparison.status.name,
                completed_at=comparison.created_at,
            ),
        )


def _complete_months(start: date, end: date) -> int:
    if end < start:
        return 0
    months = (end.year - start.year) * 12 + end.month - start.month
    if end < _add_months(start, months):
        months -= 1
    return max(months, 0)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _representative_monthly_payment(simulation: Simulation) -> int:
    if (
        simulation.selection is not None
        and simulation.selection.scenario is not None
        and simulation.selection.scenario.monthly_loan_payment is not None
    ):
        return simulation.selection.scenario.monthly_loan_payment
    principal = Decimal(simulation.loan_amount)
    monthly_rate = Decimal(simulation.loan_interest_rate) / Decimal(12)
    amortizing_months = simulation.loan_term_months - simulation.loan_grace_months
    if simulation.loan_repayment_type is RepaymentType.BULLET_PAYMENT:
        return _round_won(principal * monthly_rate)
    if simulation.loan_repayment_type is RepaymentType.EQUAL_PRINCIPAL:
        return _round_won(principal / amortizing_months + principal * monthly_rate)
    if monthly_rate == 0:
        return _round_won(principal / amortizing_months)
    payment = (
        principal * monthly_rate / (Decimal(1) - (Decimal(1) + monthly_rate) ** -amortizing_months)
    )
    return _round_won(payment)


def _equal_payment_balance(
    principal: Decimal,
    monthly_rate: Decimal,
    monthly_payment: int,
    elapsed: int,
    term: int,
) -> int:
    if elapsed >= term:
        return 0
    if monthly_rate == 0:
        return max(_round_won(principal - Decimal(monthly_payment) * elapsed), 0)
    factor = (Decimal(1) + monthly_rate) ** elapsed
    balance = principal * factor - Decimal(monthly_payment) * ((factor - Decimal(1)) / monthly_rate)
    return max(_round_won(balance), 0)


def _round_won(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _execution_sort_key(execution: Execution) -> tuple[datetime, int]:
    return (
        execution.executed_at or execution.created_at or datetime.min.replace(tzinfo=UTC),
        execution.id or 0,
    )


def _comparison_sort_key(comparison: OutcomeComparison) -> tuple[datetime, int]:
    return (
        comparison.created_at or datetime.min.replace(tzinfo=UTC),
        comparison.id or 0,
    )


def _metric_order(metric_code: str) -> tuple[int, str]:
    order = {
        "MONTHLY_SALES": 0,
        "OPERATING_PROFIT": 1,
        "ONLINE_ORDER_RATIO": 2,
        "CASH_AFTER_REPAYMENT": 3,
    }
    return order.get(metric_code, 99), metric_code


def _unresolved_bottlenecks(
    comparison: OutcomeComparison | None,
) -> tuple[UnresolvedBottleneck, ...]:
    if comparison is None or comparison.reassessment_snapshot is None:
        return ()
    active_types = {
        BottleneckChangeType.REMAINING,
        BottleneckChangeType.NEW,
        BottleneckChangeType.NOT_COMPARABLE,
    }
    return tuple(
        UnresolvedBottleneck(
            bottleneck_type=change.bottleneck_type,
            change_type=change.change_type.name,
            detail=change.detail,
        )
        for change in comparison.reassessment_snapshot.changes
        if change.change_type in active_types
    )


def _next_initial_conditions(
    comparison: OutcomeComparison | None,
    outcome_by_simulation: dict[int, OutcomeData],
) -> dict | None:
    if comparison is None:
        return None
    if isinstance(comparison.next_round_pos_data_snapshot, dict):
        return dict(comparison.next_round_pos_data_snapshot)
    outcome = outcome_by_simulation.get(comparison.simulation_id)
    if outcome is None:
        return None
    if isinstance(outcome.raw_pos_data, dict):
        return dict(outcome.raw_pos_data)
    if outcome.monthly_sales_amount is not None:
        return {
            "monthly_revenue": outcome.monthly_sales_amount,
            "operating_profit_amount": outcome.operating_profit_amount,
            "online_order_ratio": (
                float(outcome.online_order_ratio)
                if outcome.online_order_ratio is not None
                else None
            ),
            "cash_after_repayment_amount": outcome.cash_after_repayment_amount,
        }
    snapshot = outcome.observed_business_snapshot
    if snapshot is None:
        return None
    return {
        "monthly_revenue": snapshot.monthly_net_sales_amount,
        "monthly_expense_amount": snapshot.monthly_expense_amount,
        "online_sales_ratio": (
            float(snapshot.online_sales_ratio) if snapshot.online_sales_ratio is not None else None
        ),
    }
