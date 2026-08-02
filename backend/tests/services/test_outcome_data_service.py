# MOCK·파일·수동 사후 데이터의 정규화와 원자적 저장을 검증하는 테스트
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import UUID

import pytest
from openpyxl import Workbook

from app.core.errors import ApiError
from app.domain.business import Business
from app.domain.dataset import BusinessSnapshot, Dataset
from app.domain.demo_session import DemoSession
from app.domain.enums import (
    DataSourceType,
    DemoSessionStatus,
    ExecutionType,
    OutcomeDataSourceType,
    RepaymentType,
)
from app.domain.execution import Execution
from app.domain.outcome import OutcomeData
from app.domain.simulation import Simulation
from app.services.outcome_data import (
    ManualOutcomeMetrics,
    OutcomeDataCreationCommand,
    OutcomeDataService,
    OutcomeFile,
)

SESSION_ID = UUID("12345678-1234-5678-1234-567812345678")
SESSION_COOKIE = str(SESSION_ID)
OBSERVED_ON = date(2026, 7, 31)


class FakeScalarResult:
    def __init__(self, values) -> None:
        self.values = list(values)

    def all(self):
        return list(self.values)


class FakeDatabase:
    def __init__(self) -> None:
        now = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
        self.session = DemoSession(
            id=SESSION_ID,
            last_accessed_at=now,
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
        self.baseline_snapshot = BusinessSnapshot(
            id=27,
            business_id=7,
            dataset_id=17,
            reference_date=date(2026, 4, 30),
            snapshot_version="v1",
            monthly_net_sales_amount=7_500_000,
            monthly_expense_amount=5_000_000,
            existing_monthly_repayment_amount=0,
            contribution_margin_rate=Decimal("0.55"),
            average_order_amount=8_000,
            monthly_order_count=2_700,
            online_sales_ratio=Decimal("0.20"),
            employee_count=2,
            source_type=DataSourceType.CALCULATED,
        )
        self.simulation = Simulation(
            id=45,
            business_id=7,
            business_snapshot_id=27,
            loan_amount=15_000_000,
            loan_interest_rate=Decimal("0.045"),
            loan_term_months=36,
            loan_grace_months=0,
            loan_repayment_type=RepaymentType.EQUAL_PAYMENT,
            status="completed",
        )
        self.executions = [
            Execution(
                id=81,
                simulation_id=45,
                selection_id=501,
                execution_type=ExecutionType.CUSTOM,
                total_amount=14_500_000,
                unused_amount=500_000,
            )
        ]
        self.outcome_rows: list[OutcomeData] = []
        self.datasets: list[Dataset] = []
        self.snapshots: list[BusinessSnapshot] = []
        self.next_file_id = 1
        self.rollback_count = 0

    def get(self, model, object_id, **kwargs):
        if model is DemoSession and object_id == self.session.id:
            return self.session
        if model is Business and object_id == self.business.id:
            return self.business
        if model is Simulation and object_id == self.simulation.id:
            return self.simulation
        if model is BusinessSnapshot and object_id == self.baseline_snapshot.id:
            return self.baseline_snapshot
        return None

    def scalars(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        if entity is Execution:
            return FakeScalarResult(self.executions)
        if entity is OutcomeData:
            return FakeScalarResult(self.outcome_rows)
        return FakeScalarResult([])

    @contextmanager
    def begin(self):
        yield

    def rollback(self) -> None:
        self.rollback_count += 1

    def add(self, value) -> None:
        if isinstance(value, Dataset):
            value.id = 100 + len(self.datasets)
            self.datasets.append(value)
        elif isinstance(value, BusinessSnapshot):
            value.id = 200 + len(self.snapshots)
            self.snapshots.append(value)
        elif isinstance(value, OutcomeData):
            value.simulation_id = value.simulation.id
            value.dataset_id = value.dataset.id
            value.observed_business_snapshot_id = value.observed_business_snapshot.id
            value.id = 300 + len(self.outcome_rows)
            self.outcome_rows.append(value)

    def flush(self) -> None:
        for dataset in self.datasets:
            for dataset_file in dataset.files:
                if dataset_file.id is None:
                    dataset_file.id = self.next_file_id
                    self.next_file_id += 1

    @property
    def outcome_data(self) -> OutcomeData | None:
        return self.outcome_rows[-1] if self.outcome_rows else None

    @property
    def dataset(self) -> Dataset | None:
        return self.datasets[-1] if self.datasets else None


class FakeEngine:
    def generate_mock(self, monthly_revenue: int) -> dict:
        return {
            "monthly_revenue": monthly_revenue,
            "monthly_cogs": 3_375_000,
            "monthly_labor_cost": 1_350_000,
            "avg_daily_customers": 90,
            "online_data": {"online_gross_order_amount": 1_500_000},
        }


@pytest.fixture
def service() -> OutcomeDataService:
    return OutcomeDataService(FakeDatabase(), FakeEngine())


def create_xlsx(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def sales_xlsx() -> bytes:
    return create_xlsx(
        ["영업일자", "거래시간", "순매출"],
        [["2026-07-01", "2026-07-01 12:30:00", 32_000_000]],
    )


def expense_xlsx() -> bytes:
    return create_xlsx(
        ["거래일자", "비용항목", "합계금액"],
        [["2026-07-01", "재료비", 12_000_000]],
    )


def manual_command(
    *,
    monthly_sales_amount: int = 32_000_000,
    online_order_ratio: Decimal = Decimal("0.31"),
) -> OutcomeDataCreationCommand:
    return OutcomeDataCreationCommand(
        simulation_id=45,
        source_type=OutcomeDataSourceType.MANUAL_INPUT,
        metrics=ManualOutcomeMetrics(
            monthly_sales_amount=monthly_sales_amount,
            operating_profit_amount=6_200_000,
            online_order_ratio=online_order_ratio,
            cash_after_repayment_amount=2_800_000,
        ),
    )


def file_command(
    *,
    sales: bytes | None = None,
    expense: bytes | None = None,
) -> OutcomeDataCreationCommand:
    return OutcomeDataCreationCommand(
        simulation_id=45,
        source_type=OutcomeDataSourceType.FILE_UPLOAD,
        sales_file=OutcomeFile("sales.xlsx", sales if sales is not None else sales_xlsx()),
        expense_file=OutcomeFile(
            "expenses.xlsx",
            expense if expense is not None else expense_xlsx(),
        ),
    )


def mock_command() -> OutcomeDataCreationCommand:
    return OutcomeDataCreationCommand(
        simulation_id=45,
        source_type=OutcomeDataSourceType.MOCK,
    )


def test_manual_input_stores_original_metrics_without_ratio_aliasing(
    service: OutcomeDataService,
) -> None:
    created = service.create(manual_command(), SESSION_COOKIE, observed_on=OBSERVED_ON)
    stored = service.database.outcome_data

    assert created.status == "READY"
    assert created.dataset_id == service.database.dataset.id
    assert stored.online_order_ratio == Decimal("0.31")
    assert stored.observed_business_snapshot.online_sales_ratio is None
    assert stored.observed_business_snapshot.monthly_expense_amount == 25_800_000


def test_file_upload_is_mapping_ready_and_persists_normalized_rows(
    service: OutcomeDataService,
) -> None:
    created = service.create(file_command(), SESSION_COOKIE, observed_on=OBSERVED_ON)

    assert created.status == "MAPPING_READY"
    assert len(service.database.dataset.sales) == 1
    assert len(service.database.dataset.expenses) == 1
    assert service.database.dataset.sales[0].net_sales == 32_000_000


def test_mock_input_keeps_raw_pos_payload(service: OutcomeDataService) -> None:
    created = service.create(mock_command(), SESSION_COOKIE, observed_on=OBSERVED_ON)

    assert created.status == "READY"
    assert service.database.outcome_data.raw_pos_data["monthly_revenue"] == 7_500_000
    assert service.database.outcome_data.observed_business_snapshot.monthly_expense_amount == (
        4_725_000
    )


def test_outcome_data_requires_execution(service: OutcomeDataService) -> None:
    service.database.executions = []

    with pytest.raises(ApiError) as caught:
        service.create(manual_command(), SESSION_COOKIE, observed_on=OBSERVED_ON)

    assert caught.value.code == "EXECUTION_REQUIRED"


def test_duplicate_outcome_data_is_rejected(service: OutcomeDataService) -> None:
    service.create(manual_command(), SESSION_COOKIE, observed_on=OBSERVED_ON)

    with pytest.raises(ApiError) as caught:
        service.create(manual_command(), SESSION_COOKIE, observed_on=OBSERVED_ON)

    assert caught.value.code == "OUTCOME_DATA_ALREADY_EXISTS"


@pytest.mark.parametrize(
    ("command", "code"),
    [
        (file_command(sales=b"not-an-xlsx"), "OUTCOME_FILE_INVALID"),
        (
            file_command(sales=create_xlsx(["영업일자", "총매출"], [["2026-07-01", 10_000]])),
            "OUTCOME_FILE_MAPPING_FAILED",
        ),
        (manual_command(monthly_sales_amount=-1), "INVALID_OUTCOME_METRIC"),
        (manual_command(online_order_ratio=Decimal("1.1")), "INVALID_OUTCOME_METRIC"),
    ],
)
def test_invalid_input_does_not_consume_outcome_slot(
    service: OutcomeDataService,
    command: OutcomeDataCreationCommand,
    code: str,
) -> None:
    with pytest.raises(ApiError) as caught:
        service.create(command, SESSION_COOKIE, observed_on=OBSERVED_ON)

    assert caught.value.code == code
    assert service.database.outcome_rows == []
    assert service.database.datasets == []
    assert service.database.snapshots == []
