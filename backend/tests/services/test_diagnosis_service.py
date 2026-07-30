# 최신 월 데이터 집계와 진단 백그라운드 상태 전이를 검증하는 테스트
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.db import session as db_session
from app.domain.business import Business
from app.domain.dataset import (
    BusinessSnapshot,
    Dataset,
    NormalizedExpense,
    NormalizedOnlineSale,
    NormalizedSale,
    PublicDataSnapshot,
)
from app.domain.diagnosis import Diagnosis
from app.domain.enums import (
    DatasetStatus,
    DataSourceType,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
    ExpenseCategory,
)
from app.services import diagnosis_service
from app.services.diagnosis_analysis import DiagnosisAnalysisError, load_benchmark
from app.services.diagnosis_service import (
    collect_analysis_input,
    create_running_diagnosis,
    run_diagnosis,
)


def build_business_and_dataset() -> tuple[Business, Dataset]:
    business = Business(
        id=1,
        name="Y카페",
        region="서울 마포구",
        industry="카페",
        employee_count=2,
    )
    dataset = Dataset(id=10, business=business, status=DatasetStatus.READY)
    dataset.sales = [
        NormalizedSale(
            business_date=date(2026, 6, 30),
            net_sales=99_000_000,
            receipt_number="OLD",
        ),
        NormalizedSale(
            business_date=date(2026, 7, 1),
            transaction_time=datetime(2026, 7, 1, 12, 0),
            net_sales=18_000_000,
            receipt_number="A",
        ),
        NormalizedSale(
            business_date=date(2026, 7, 31),
            transaction_time=datetime(2026, 7, 31, 18, 0),
            net_sales=12_000_000,
            receipt_number="B",
        ),
    ]
    dataset.expenses = [
        NormalizedExpense(
            transaction_date=date(2026, 7, 5),
            expense_category=ExpenseCategory.MATERIAL,
            total_amount=12_000_000,
        ),
        NormalizedExpense(
            transaction_date=date(2026, 7, 20),
            expense_category=ExpenseCategory.LABOR,
            total_amount=6_000_000,
        ),
    ]
    dataset.online_sales = [
        NormalizedOnlineSale(
            business_date=date(2026, 7, 10),
            sales_amount=2_700_000,
            gross_order_amount=3_000_000,
            platform_fee_amount=300_000,
            payment_fee_amount=90_000,
            merchant_delivery_fee=60_000,
            refund_amount=150_000,
            settlement_amount=2_760_000,
        )
    ]
    return business, dataset


def build_running_diagnosis() -> Diagnosis:
    business, dataset = build_business_and_dataset()
    benchmark = load_benchmark()
    business_snapshot = BusinessSnapshot(
        id=30,
        business=business,
        dataset=dataset,
        reference_date=date(2026, 7, 31),
        snapshot_version="v1",
        monthly_net_sales_amount=30_000_000,
        monthly_expense_amount=18_000_000,
        existing_monthly_repayment_amount=0,
        contribution_margin_rate=Decimal("0.6"),
        average_order_amount=15_000_000,
        monthly_order_count=2,
        online_sales_ratio=Decimal("0.09"),
        employee_count=2,
        source_type=DataSourceType.CALCULATED,
    )
    public_snapshot = PublicDataSnapshot(
        id=40,
        business=business,
        reference_date=benchmark.reference_date,
        source_name=benchmark.source_name,
        snapshot_version=benchmark.snapshot_version,
        reference_area=benchmark.reference_area,
        raw_data=benchmark.to_raw_data(),
    )
    return Diagnosis(
        id=20,
        business=business,
        dataset=dataset,
        business_snapshot=business_snapshot,
        public_data_snapshot=public_snapshot,
        status=DiagnosisStatus.RUNNING,
        evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
    )


class FakeDatabaseSession:
    def __init__(
        self,
        diagnosis: Diagnosis,
        *,
        require_diagnosis_lock: bool = False,
    ) -> None:
        self.diagnosis = diagnosis
        self.require_diagnosis_lock = require_diagnosis_lock
        self.rollback_called = False
        self.closed = False

    @contextmanager
    def begin(self) -> Iterator[None]:
        yield

    def get(
        self,
        model: type,
        identifier: int,
        **kwargs: object,
    ) -> Diagnosis | None:
        if model is Diagnosis and identifier == self.diagnosis.id:
            if self.require_diagnosis_lock:
                assert kwargs.get("with_for_update") is True
            return self.diagnosis
        return None

    def rollback(self) -> None:
        self.rollback_called = True

    def close(self) -> None:
        self.closed = True


class FakeCreateDatabaseSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        diagnosis = next(
            (item for item in self.added if isinstance(item, Diagnosis)),
            None,
        )
        if diagnosis is not None:
            diagnosis.id = 20


class FailureRaceDatabaseSession(FakeDatabaseSession):
    def __init__(self, diagnosis: Diagnosis) -> None:
        super().__init__(diagnosis)
        self.get_count = 0

    def get(
        self,
        model: type,
        identifier: int,
        **kwargs: object,
    ) -> Diagnosis | None:
        stored = super().get(model, identifier, **kwargs)
        if stored is not None:
            self.get_count += 1
            if self.get_count == 2:
                stored.status = DiagnosisStatus.COMPLETED
        return stored


def test_collect_analysis_input_uses_latest_sales_month() -> None:
    business, dataset = build_business_and_dataset()

    input_data = collect_analysis_input(business, dataset)

    assert input_data.reference_date == date(2026, 7, 31)
    assert input_data.monthly_sales_amount == 30_000_000
    assert input_data.monthly_expense_amount == 18_000_000
    assert input_data.material_cost_amount == 12_000_000
    assert input_data.labor_cost_amount == 6_000_000
    assert input_data.monthly_order_count == 2
    assert input_data.online_sales_amount == 2_700_000
    assert input_data.online_platform_cost_amount == 450_000
    assert input_data.timed_sales_coverage == Decimal("1")


def test_collect_analysis_input_rejects_dataset_without_sales() -> None:
    business, dataset = build_business_and_dataset()
    dataset.sales = []

    with pytest.raises(DiagnosisAnalysisError, match="매출 데이터"):
        collect_analysis_input(business, dataset)


def test_collect_analysis_input_omits_partial_online_settlement() -> None:
    business, dataset = build_business_and_dataset()
    dataset.online_sales.append(
        NormalizedOnlineSale(
            business_date=date(2026, 7, 11),
            sales_amount=1_000_000,
            gross_order_amount=1_200_000,
            platform_fee_amount=0,
            payment_fee_amount=0,
            merchant_delivery_fee=0,
            refund_amount=0,
            settlement_amount=None,
        )
    )

    input_data = collect_analysis_input(business, dataset)

    assert input_data.online_settlement_amount is None


def test_ready_dataset_without_sales_transitions_to_failed_in_background(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    business, dataset = build_business_and_dataset()
    dataset.sales = []
    database = FakeCreateDatabaseSession()

    diagnosis = create_running_diagnosis(database, business, dataset)

    assert diagnosis.id == 20
    assert diagnosis.status is DiagnosisStatus.RUNNING
    assert diagnosis.business_snapshot.monthly_net_sales_amount == 0

    background_database = FakeDatabaseSession(diagnosis)
    monkeypatch.setattr(db_session, "SessionFactory", lambda: background_database)

    run_diagnosis(20)

    assert diagnosis.status is DiagnosisStatus.FAILED


def test_run_diagnosis_persists_results_and_marks_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnosis = build_running_diagnosis()
    database = FakeDatabaseSession(diagnosis)
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    run_diagnosis(20)

    assert diagnosis.status is DiagnosisStatus.COMPLETED
    assert diagnosis.metrics
    assert diagnosis.bottlenecks
    assert database.closed is True


def test_run_diagnosis_marks_failed_when_analysis_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnosis = build_running_diagnosis()
    database = FakeDatabaseSession(diagnosis)
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    def raise_analysis_error(*_: object) -> None:
        raise DiagnosisAnalysisError("의도적인 분석 실패")

    monkeypatch.setattr(diagnosis_service, "analyze", raise_analysis_error)

    run_diagnosis(20)

    assert diagnosis.status is DiagnosisStatus.FAILED
    assert database.rollback_called is True
    assert database.closed is True


def test_run_diagnosis_skips_completed_diagnosis_with_row_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnosis = build_running_diagnosis()
    diagnosis.status = DiagnosisStatus.COMPLETED
    database = FakeDatabaseSession(
        diagnosis,
        require_diagnosis_lock=True,
    )
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    def reject_duplicate_analysis(*_: object) -> None:
        raise AssertionError("완료된 진단을 다시 계산하면 안 됩니다.")

    monkeypatch.setattr(diagnosis_service, "analyze", reject_duplicate_analysis)

    run_diagnosis(20)

    assert diagnosis.status is DiagnosisStatus.COMPLETED
    assert database.closed is True


def test_failed_worker_does_not_overwrite_concurrently_completed_diagnosis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnosis = build_running_diagnosis()
    database = FailureRaceDatabaseSession(diagnosis)
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    def raise_analysis_error(*_: object) -> None:
        raise DiagnosisAnalysisError("의도적인 분석 실패")

    monkeypatch.setattr(diagnosis_service, "analyze", raise_analysis_error)

    run_diagnosis(20)

    assert diagnosis.status is DiagnosisStatus.COMPLETED
