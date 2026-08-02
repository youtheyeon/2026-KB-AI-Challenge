# 실제 지표와 관측 가능한 병목만 결과 비교로 저장하는 서비스 테스트
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.dataset import (
    BusinessSnapshot,
    Dataset,
    NormalizedExpense,
    NormalizedSale,
)
from app.domain.demo_session import DemoSession
from app.domain.diagnosis import Bottleneck, Diagnosis
from app.domain.enums import (
    AllocationCategory,
    BottleneckSeverity,
    DataSourceType,
    DemoSessionStatus,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
    ExecutionType,
    ExpenseCategory,
    OutcomeDataSourceType,
    OutcomeDataStatus,
    OutcomeMetricStatus,
    OutcomeStatus,
    RepaymentType,
)
from app.domain.execution import Execution, ExecutionAllocation
from app.domain.outcome import OutcomeComparison, OutcomeData
from app.domain.simulation import Simulation
from app.services.outcome import OutcomeCreationCommand, OutcomeService, classify_metric

SESSION_ID = UUID("12345678-1234-5678-1234-567812345678")
SESSION_COOKIE = str(SESSION_ID)
NOW = datetime(2026, 7, 31, 12, 10, tzinfo=UTC)


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
            expires_at=NOW + timedelta(days=1),
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
            source_type=DataSourceType.CALCULATED,
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
            source_type=DataSourceType.USER_INPUT,
        )
        self.bottleneck = Bottleneck(
            id=201,
            diagnosis_id=31,
            bottleneck_type="HIGH_MATERIAL_COST",
            detail="재료비 부담이 높습니다.",
            severity=BottleneckSeverity.SEVERE,
            evidence_source_type=DataSourceType.DOMAIN_ASSUMPTION,
            evidence_description="업계 참고치와 비교했습니다.",
            related_categories=["inventory"],
        )
        self.diagnosis = Diagnosis(
            id=31,
            business_id=7,
            dataset_id=17,
            business_snapshot_id=27,
            public_data_snapshot_id=37,
            status=DiagnosisStatus.COMPLETED,
            evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
            bottlenecks=[self.bottleneck],
        )
        self.simulation = Simulation(
            id=45,
            business_id=7,
            diagnosis_id=31,
            business_snapshot_id=27,
            loan_amount=15_000_000,
            loan_interest_rate=Decimal("0.045"),
            loan_term_months=36,
            loan_grace_months=0,
            loan_repayment_type=RepaymentType.EQUAL_PAYMENT,
            status="completed",
        )
        self.execution = Execution(
            id=81,
            simulation_id=45,
            selection_id=501,
            execution_type=ExecutionType.CUSTOM,
            total_amount=14_500_000,
            unused_amount=500_000,
            allocations=[
                ExecutionAllocation(
                    id=811,
                    name="재고 개선",
                    category=AllocationCategory.INVENTORY,
                    amount=10_000_000,
                ),
                ExecutionAllocation(
                    id=812,
                    name="기타 개선",
                    category=None,
                    amount=4_500_000,
                ),
            ],
        )
        self.dataset = Dataset(
            id=18,
            business_id=7,
            status=None,
            dataset_version="outcome-v1",
            sales=[],
            expenses=[],
            online_sales=[],
        )
        self.outcome_data = OutcomeData(
            id=91,
            simulation_id=45,
            dataset_id=18,
            observed_business_snapshot_id=28,
            source_type=OutcomeDataSourceType.MANUAL_INPUT,
            status=OutcomeDataStatus.READY,
            observed_at=date(2026, 7, 31),
            monthly_sales_amount=8_100_000,
            operating_profit_amount=1_500_000,
            online_order_ratio=Decimal("0.25"),
            cash_after_repayment_amount=300_000,
            dataset=self.dataset,
            observed_business_snapshot=self.observed,
        )
        self.comparisons: list[OutcomeComparison] = []
        self.rollback_count = 0

    def get(self, model, object_id, **kwargs):
        values = {
            DemoSession: self.session,
            Business: self.business,
            Simulation: self.simulation,
            Diagnosis: self.diagnosis,
            BusinessSnapshot: (self.baseline if object_id == self.baseline.id else self.observed),
            Execution: self.execution,
            OutcomeData: self.outcome_data,
        }
        value = values.get(model)
        return value if value is not None and value.id == object_id else None

    def scalars(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        values = {
            Execution: [self.execution],
            OutcomeData: [self.outcome_data],
            OutcomeComparison: self.comparisons,
        }
        return FakeScalarResult(values.get(entity, []))

    @contextmanager
    def begin(self):
        yield

    def rollback(self) -> None:
        self.rollback_count += 1

    def add(self, value) -> None:
        if isinstance(value, OutcomeComparison):
            value.id = 101
            value.created_at = NOW
            value.reassessment_snapshot.id = 111
            value.reassessment_snapshot_id = 111
            for index, metric in enumerate(value.metrics, start=1):
                metric.id = 1000 + index
                metric.comparison_id = value.id
            for index, change in enumerate(
                value.reassessment_snapshot.changes,
                start=1,
            ):
                change.id = 2000 + index
                change.reassessment_id = value.reassessment_snapshot_id
            self.comparisons.append(value)

    def flush(self) -> None:
        pass


class FakeEngine:
    def __init__(self) -> None:
        self.compare_count = 0
        self.project_count = 0
        self.last_compare_request = None

    def compare(self, request) -> dict:
        self.compare_count += 1
        self.last_compare_request = request
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
            "next_round_pos_data_snapshot": {
                "monthly_revenue": 8_100_000,
                "monthly_cogs": 4_700_000,
            },
        }

    def project_financial(self, request) -> dict:
        self.project_count += 1
        return financial_result()


def financial_result() -> dict:
    return {
        "monthly_loan_payment": 500_000,
        "additional_fixed_cost_per_month": 100_000,
        "remaining_cash_after_payment": 200_000,
        "break_even_additional_revenue": 100_000,
    }


@pytest.fixture
def service() -> OutcomeService:
    return OutcomeService(FakeDatabase(), FakeEngine())


def valid_command(
    *,
    simulation_id: int = 45,
    execution_id: int = 81,
    outcome_data_id: int = 91,
) -> OutcomeCreationCommand:
    return OutcomeCreationCommand(
        simulation_id=simulation_id,
        execution_id=execution_id,
        outcome_data_id=outcome_data_id,
    )


def set_file_mode(service: OutcomeService, *, timed: bool) -> None:
    transaction_time = datetime(2026, 7, 1, 12, 0, tzinfo=UTC) if timed else None
    service.database.dataset.sales = [
        NormalizedSale(
            business_date=date(2026, 7, 1),
            transaction_time=transaction_time,
            net_sales=8_100_000,
            gross_sales=8_100_000,
            discount_amount=0,
            refund_amount=0,
        )
    ]
    service.database.dataset.expenses = [
        NormalizedExpense(
            transaction_date=date(2026, 7, 1),
            expense_category=ExpenseCategory.MATERIAL,
            total_amount=4_000_000,
            supply_amount=4_000_000,
            vat_amount=0,
            tax_exempt_amount=0,
        ),
        NormalizedExpense(
            transaction_date=date(2026, 7, 1),
            expense_category=ExpenseCategory.LABOR,
            total_amount=2_000_000,
            supply_amount=2_000_000,
            vat_amount=0,
            tax_exempt_amount=0,
        ),
    ]
    service.database.outcome_data.source_type = OutcomeDataSourceType.FILE_UPLOAD
    service.database.outcome_data.status = OutcomeDataStatus.MAPPING_READY
    service.database.outcome_data.raw_pos_data = None


def set_mock_mode(service: OutcomeService) -> None:
    service.database.outcome_data.source_type = OutcomeDataSourceType.MOCK
    service.database.outcome_data.status = OutcomeDataStatus.READY
    service.database.outcome_data.raw_pos_data = {
        "monthly_revenue": 8_100_000,
        "monthly_cogs": 4_000_000,
        "monthly_labor_cost": 2_000_000,
        "avg_daily_customers": 100,
        "online_data": {"online_order_count": 750},
    }


def test_metric_uses_target_and_break_even_ranges() -> None:
    assert (
        classify_metric(Decimal("120"), Decimal("100"), Decimal("125"))
        is OutcomeMetricStatus.ABOVE_EXPECTED
    )
    assert (
        classify_metric(Decimal("120"), Decimal("100"), Decimal("110"))
        is OutcomeMetricStatus.WITHIN_RANGE
    )
    assert (
        classify_metric(Decimal("120"), Decimal("100"), Decimal("90"))
        is OutcomeMetricStatus.BELOW_EXPECTED
    )
    assert (
        classify_metric(None, Decimal("100"), Decimal("90")) is OutcomeMetricStatus.NOT_COMPARABLE
    )


def test_manual_input_projects_financials_without_bottleneck_comparison(
    service: OutcomeService,
) -> None:
    created = service.create(valid_command(), SESSION_COOKIE, now=NOW)

    assert created.status == "COMPLETED"
    assert created.summary.sales_growth_status == "ABOVE_EXPECTED"
    assert service.engine.project_count == 1
    assert service.engine.compare_count == 0
    assert service.database.comparisons[0].status is OutcomeStatus.MET
    assert service.database.comparisons[0].next_round_pos_data_snapshot == {
        "monthly_revenue": 8_100_000,
        "operating_profit_amount": 1_500_000,
        "online_order_ratio": 0.25,
        "cash_after_repayment_amount": 300_000,
    }


def test_mock_uses_full_ai_comparison_and_stores_next_snapshot(
    service: OutcomeService,
) -> None:
    set_mock_mode(service)

    service.create(valid_command(), SESSION_COOKIE, now=NOW)

    assert service.engine.compare_count == 1
    assert service.engine.last_compare_request.comparable_bottleneck_types is None
    comparison = service.database.comparisons[0]
    assert comparison.status is OutcomeStatus.PARTIALLY_MET
    assert comparison.next_round_pos_data_snapshot["monthly_cogs"] == 4_700_000


@pytest.mark.parametrize(("timed", "has_time"), [(True, True), (False, False)])
def test_file_comparison_only_enables_time_bottleneck_with_full_coverage(
    service: OutcomeService,
    timed: bool,
    has_time: bool,
) -> None:
    set_file_mode(service, timed=timed)

    service.create(valid_command(), SESSION_COOKIE, now=NOW)

    comparable = service.engine.last_compare_request.comparable_bottleneck_types
    assert ("time_of_day_weakness" in comparable) is has_time
    assert {"high_cost_ratio", "high_labor_ratio"} <= comparable


def test_failed_outcome_data_is_rejected(service: OutcomeService) -> None:
    service.database.outcome_data.status = OutcomeDataStatus.FAILED

    with pytest.raises(ApiError) as caught:
        service.create(valid_command(), SESSION_COOKIE, now=NOW)

    assert caught.value.code == "OUTCOME_DATA_NOT_READY"


def test_mismatched_source_ids_are_hidden(service: OutcomeService) -> None:
    with pytest.raises(ApiError) as caught:
        service.create(valid_command(execution_id=999), SESSION_COOKIE, now=NOW)

    assert caught.value.status_code == 404


def test_duplicate_outcome_is_rejected(service: OutcomeService) -> None:
    service.create(valid_command(), SESSION_COOKIE, now=NOW)

    with pytest.raises(ApiError) as caught:
        service.create(valid_command(), SESSION_COOKIE, now=NOW)

    assert caught.value.code == "OUTCOME_ALREADY_EXISTS"


def test_get_result_reads_saved_graph_without_engine_call(service: OutcomeService) -> None:
    set_mock_mode(service)
    service.create(valid_command(), SESSION_COOKIE, now=NOW)
    compare_count = service.engine.compare_count
    project_count = service.engine.project_count

    result = service.get_result(45, SESSION_COOKIE)

    assert result.overall_status == "PARTIALLY_MET"
    assert len(result.comparison_rows) == 4
    assert result.new_bottlenecks[0].bottleneck_type == "high_labor_ratio"
    assert service.engine.compare_count == compare_count
    assert service.engine.project_count == project_count
