# 저장된 검증 사이클과 추정 상환 현황을 투영하는 대시보드 테스트
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.business import Business
from app.domain.dataset import BusinessSnapshot
from app.domain.demo_session import DemoSession
from app.domain.enums import (
    BottleneckChangeType,
    DemoSessionStatus,
    ExecutionType,
    OutcomeDataSourceType,
    OutcomeDataStatus,
    OutcomeMetricStatus,
    OutcomeStatus,
    RepaymentType,
    RiskLevel,
    ScenarioCode,
)
from app.domain.execution import Execution
from app.domain.outcome import (
    BottleneckChange,
    OutcomeComparison,
    OutcomeComparisonMetric,
    OutcomeData,
    ReassessmentSnapshot,
)
from app.domain.simulation import Scenario, ScenarioSelection, Simulation
from app.services.dashboard import DashboardService, estimate_loan_status

SESSION_ID = UUID("12345678-1234-5678-1234-567812345678")
SESSION_COOKIE = str(SESSION_ID)
NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


class FakeScalarResult:
    def __init__(self, values) -> None:
        self.values = list(values)

    def unique(self):
        return self

    def all(self):
        return list(self.values)


def make_simulation(
    repayment_type: RepaymentType = RepaymentType.EQUAL_PAYMENT,
    *,
    grace_months: int = 0,
    term_months: int = 36,
) -> Simulation:
    scenario = Scenario(
        id=101,
        simulation_id=45,
        code=ScenarioCode.A,
        strategy_type="BOTTLENECK_FOCUSED",
        title="병목 집중형",
        total_amount=15_000_000,
        monthly_loan_payment=446_205,
        monthly_recurring_cost=100_000,
        cash_after_payment=200_000,
        break_even_additional_revenue=0,
        risk_level=RiskLevel.LOW,
        target_metrics=[],
        risk_reasons=[],
    )
    selection = ScenarioSelection(
        id=501,
        simulation_id=45,
        scenario_id=101,
        selected_at=datetime(2026, 4, 30, tzinfo=UTC),
        locked=True,
        scenario=scenario,
    )
    simulation = Simulation(
        id=45,
        business_id=7,
        diagnosis_id=31,
        business_snapshot_id=27,
        loan_amount=15_000_000,
        loan_interest_rate=Decimal("0.045"),
        loan_term_months=term_months,
        loan_grace_months=grace_months,
        loan_repayment_type=repayment_type,
        status="completed",
        scenarios=[scenario],
        selection=selection,
    )
    simulation.created_at = datetime(2026, 4, 30, tzinfo=UTC)
    return simulation


def execution_on(executed_on: date) -> Execution:
    execution = Execution(
        id=81,
        simulation_id=45,
        selection_id=501,
        execution_type=ExecutionType.SAME_AS_A,
        total_amount=15_000_000,
        unused_amount=0,
        executed_at=datetime.combine(executed_on, datetime.min.time(), tzinfo=UTC),
        allocations=[],
    )
    execution.created_at = execution.executed_at
    return execution


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
            region="서울",
            industry="카페",
            employee_count=2,
            primary_sales_channels=[],
        )
        self.baseline = BusinessSnapshot(
            id=27,
            business_id=7,
            dataset_id=17,
            reference_date=date(2026, 4, 30),
            snapshot_version="v1",
            monthly_net_sales_amount=7_500_000,
            monthly_expense_amount=6_000_000,
            existing_monthly_repayment_amount=0,
            contribution_margin_rate=Decimal("0.55"),
            average_order_amount=8_000,
            monthly_order_count=2_700,
            online_sales_ratio=Decimal("0.20"),
            employee_count=2,
            source_type="calculated",
        )
        self.observed = BusinessSnapshot(
            id=28,
            business_id=7,
            dataset_id=18,
            reference_date=date(2026, 7, 31),
            snapshot_version="outcome-v1",
            monthly_net_sales_amount=8_100_000,
            monthly_expense_amount=6_600_000,
            existing_monthly_repayment_amount=0,
            contribution_margin_rate=Decimal("0.55"),
            average_order_amount=8_500,
            monthly_order_count=2_850,
            online_sales_ratio=None,
            employee_count=2,
            source_type="user_input",
        )
        self.simulation = make_simulation()
        self.execution = execution_on(date(2026, 7, 30))
        self.outcome_data = OutcomeData(
            id=91,
            simulation_id=45,
            dataset_id=18,
            observed_business_snapshot_id=28,
            source_type=OutcomeDataSourceType.MANUAL_INPUT,
            status=OutcomeDataStatus.READY,
            monthly_sales_amount=8_100_000,
            operating_profit_amount=1_500_000,
            online_order_ratio=Decimal("0.25"),
            cash_after_repayment_amount=300_000,
            observed_business_snapshot=self.observed,
        )
        self.comparison = OutcomeComparison(
            id=101,
            simulation_id=45,
            execution_id=81,
            outcome_data_id=91,
            status=OutcomeStatus.PARTIALLY_MET,
            next_round_pos_data_snapshot={
                "monthly_revenue": 8_100_000,
                "monthly_cogs": 4_700_000,
            },
            metrics=[
                OutcomeComparisonMetric(
                    metric_code="MONTHLY_SALES",
                    target_value=7_600_000,
                    break_even_value=7_500_000,
                    observed_value=8_100_000,
                    unit="KRW",
                    status=OutcomeMetricStatus.ABOVE_EXPECTED,
                ),
                OutcomeComparisonMetric(
                    metric_code="ONLINE_ORDER_RATIO",
                    target_value=Decimal("0.20"),
                    break_even_value=Decimal("0.20"),
                    observed_value=Decimal("0.25"),
                    unit="RATIO",
                    status=OutcomeMetricStatus.ABOVE_EXPECTED,
                ),
            ],
            reassessment_snapshot=ReassessmentSnapshot(
                latest_business_snapshot_id=28,
                previous_diagnosis_id=31,
                changes=[
                    BottleneckChange(
                        bottleneck_type="high_cost_ratio",
                        change_type=BottleneckChangeType.REMAINING,
                        detail="원가율 병목이 남아 있습니다.",
                    ),
                    BottleneckChange(
                        bottleneck_type="time_of_day_weakness",
                        change_type=BottleneckChangeType.RESOLVED,
                        detail="시간대 병목은 해결됐습니다.",
                    ),
                ],
            ),
        )
        self.comparison.created_at = datetime(2026, 7, 31, tzinfo=UTC)

    def get(self, model, object_id, **kwargs):
        values = {
            DemoSession: self.session,
            Business: self.business,
            BusinessSnapshot: self.baseline if object_id == 27 else self.observed,
        }
        value = values.get(model)
        return value if value is not None and value.id == object_id else None

    def scalars(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        values = {
            Simulation: [self.simulation],
            Execution: [self.execution] if self.execution is not None else [],
            OutcomeData: [self.outcome_data] if self.outcome_data is not None else [],
            OutcomeComparison: [self.comparison] if self.comparison is not None else [],
        }
        return FakeScalarResult(values.get(entity, []))


@pytest.fixture
def service() -> DashboardService:
    return DashboardService(FakeDatabase())


def test_dashboard_labels_scheduled_repayment_as_estimated(
    service: DashboardService,
) -> None:
    result = service.get(7, SESSION_COOKIE, as_of=date(2026, 10, 30))

    assert result.loan_status.repayment_data_type == "ESTIMATED"
    assert result.loan_status.progress_rate == Decimal("0.0833")
    assert result.loan_status.estimated_remaining_principal < result.loan_status.loan_amount


def test_bullet_loan_keeps_principal_until_maturity() -> None:
    simulation = make_simulation(RepaymentType.BULLET_PAYMENT)
    simulation.selection.scenario.monthly_loan_payment = 56_250

    result = estimate_loan_status(
        simulation,
        execution_on(date(2026, 7, 30)),
        date(2026, 10, 30),
    )

    assert result.estimated_remaining_principal == 15_000_000
    assert result.paid_amount == result.monthly_repayment_amount * 3


def test_equal_principal_reduces_fixed_principal_each_month() -> None:
    simulation = make_simulation(RepaymentType.EQUAL_PRINCIPAL)
    simulation.selection.scenario.monthly_loan_payment = None

    result = estimate_loan_status(
        simulation,
        execution_on(date(2026, 7, 30)),
        date(2026, 10, 30),
    )

    assert result.estimated_remaining_principal == 13_750_000


def test_grace_period_does_not_reduce_principal() -> None:
    simulation = make_simulation(grace_months=3)
    simulation.selection.scenario.monthly_loan_payment = None

    result = estimate_loan_status(
        simulation,
        execution_on(date(2026, 7, 30)),
        date(2026, 10, 30),
    )

    assert result.estimated_remaining_principal == 15_000_000
    assert result.paid_amount == 56_250 * 3


def test_repayment_is_capped_at_maturity() -> None:
    result = estimate_loan_status(
        make_simulation(term_months=12),
        execution_on(date(2026, 7, 30)),
        date(2028, 7, 30),
    )

    assert result.progress_rate == Decimal("1.0000")
    assert result.estimated_remaining_principal == 0


def test_dashboard_projects_only_stored_cycle_data(service: DashboardService) -> None:
    result = service.get(7, SESSION_COOKIE, as_of=date(2026, 10, 30))

    assert result.business.name == "청춘카페"
    assert len(result.metric_trends) == 2
    assert result.metric_trends[0].before_value == Decimal("7500000")
    assert result.cycle_histories[0].selected_plan.scenario_code == "A"
    assert result.cycle_histories[0].execution.execution_mode == "SAME_AS_A"
    assert result.cycle_histories[0].outcome.overall_status == "PARTIALLY_MET"
    assert [item.bottleneck_type for item in result.unresolved_bottlenecks] == ["high_cost_ratio"]
    assert result.next_initial_conditions["monthly_revenue"] == 8_100_000


def test_dashboard_without_execution_has_no_loan_status(
    service: DashboardService,
) -> None:
    service.database.execution = None

    result = service.get(7, SESSION_COOKIE, as_of=date(2026, 10, 30))

    assert result.loan_status is None


def test_dashboard_without_outcome_returns_empty_cycle_sections(
    service: DashboardService,
) -> None:
    service.database.outcome_data = None
    service.database.comparison = None

    result = service.get(7, SESSION_COOKIE, as_of=date(2026, 10, 30))

    assert result.metric_trends == ()
    assert result.cycle_histories == ()
    assert result.unresolved_bottlenecks == ()
    assert result.next_initial_conditions is None
