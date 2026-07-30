# 사업 데이터 스냅샷을 만들고 백그라운드 진단 결과를 영속화하는 서비스
import logging
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.db import session as db_session
from app.domain.business import Business
from app.domain.dataset import (
    BusinessSnapshot,
    Dataset,
    NormalizedExpense,
    NormalizedOnlineSale,
    PublicDataSnapshot,
)
from app.domain.diagnosis import Bottleneck, Diagnosis, DiagnosisMetric
from app.domain.enums import (
    DataSourceType,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
    ExpenseCategory,
)
from app.services.diagnosis_analysis import (
    AnalysisInput,
    DiagnosisAnalysisError,
    analyze,
    benchmark_from_raw_data,
    load_benchmark,
)

logger = logging.getLogger(__name__)


def collect_analysis_input(
    business: Business,
    dataset: Dataset,
) -> AnalysisInput:
    if not dataset.sales:
        raise DiagnosisAnalysisError("진단할 매출 데이터가 없습니다.")

    reference_date = max(sale.business_date for sale in dataset.sales)
    sales = [sale for sale in dataset.sales if _same_month(sale.business_date, reference_date)]
    expenses = [
        expense
        for expense in dataset.expenses
        if _same_month(expense.transaction_date, reference_date)
    ]
    online_sales = [
        sale
        for sale in dataset.online_sales
        if sale.business_date is not None and _same_month(sale.business_date, reference_date)
    ]

    monthly_sales_amount = sum(sale.net_sales for sale in sales)
    monthly_expense_amount = sum(expense.total_amount for expense in expenses)
    material_cost_amount = _expense_total(expenses, ExpenseCategory.MATERIAL)
    labor_cost_amount = _expense_total(expenses, ExpenseCategory.LABOR)
    receipt_numbers = {sale.receipt_number for sale in sales if sale.receipt_number is not None}
    monthly_order_count = len(receipt_numbers) if receipt_numbers else len(sales)

    timed_sales_by_bucket: dict[str, int] = defaultdict(int)
    timed_sales_amount = 0
    for sale in sales:
        if sale.transaction_time is None:
            continue
        timed_sales_amount += sale.net_sales
        timed_sales_by_bucket[_time_bucket(sale.transaction_time.hour)] += sale.net_sales

    online_values = _online_values(online_sales)
    timed_sales_coverage = (
        Decimal(timed_sales_amount) / Decimal(monthly_sales_amount)
        if monthly_sales_amount > 0
        else Decimal("0")
    )
    return AnalysisInput(
        reference_date=reference_date,
        monthly_sales_amount=monthly_sales_amount,
        monthly_expense_amount=monthly_expense_amount,
        material_cost_amount=material_cost_amount,
        labor_cost_amount=labor_cost_amount,
        existing_monthly_repayment_amount=0,
        monthly_order_count=monthly_order_count,
        employee_count=business.employee_count,
        online_sales_amount=online_values["sales_amount"],
        online_gross_order_amount=online_values["gross_order_amount"],
        online_platform_cost_amount=online_values["platform_cost_amount"],
        online_refund_amount=online_values["refund_amount"],
        online_settlement_amount=online_values["settlement_amount"],
        timed_sales_by_bucket=dict(timed_sales_by_bucket),
        timed_sales_coverage=timed_sales_coverage,
    )


def create_running_diagnosis(
    database: Session,
    business: Business,
    dataset: Dataset,
) -> Diagnosis:
    benchmark = load_benchmark()
    input_data = collect_analysis_input(business, dataset)
    business_snapshot = _get_or_create_business_snapshot(
        database,
        business,
        dataset,
        input_data,
    )
    public_snapshot = PublicDataSnapshot(
        business=business,
        reference_date=benchmark.reference_date,
        source_name=benchmark.source_name,
        snapshot_version=benchmark.snapshot_version,
        reference_area=benchmark.reference_area,
        raw_data=benchmark.to_raw_data(),
    )
    diagnosis = Diagnosis(
        business=business,
        dataset=dataset,
        business_snapshot=business_snapshot,
        public_data_snapshot=public_snapshot,
        status=DiagnosisStatus.RUNNING,
        evidence_source=DiagnosisEvidenceSource.BUSINESS_AND_PUBLIC_DATA,
        diagnosis_version="v1",
        benchmark_version=benchmark.snapshot_version,
    )
    database.add(public_snapshot)
    database.add(diagnosis)
    database.flush()
    if diagnosis.id is None:
        raise RuntimeError("진단 ID가 생성되지 않았습니다.")
    return diagnosis


def run_diagnosis(diagnosis_id: int) -> None:
    database = db_session.SessionFactory()
    try:
        try:
            with database.begin():
                _complete_diagnosis(database, diagnosis_id)
        except Exception:
            database.rollback()
            logger.exception(
                "진단 백그라운드 작업이 실패했습니다.", extra={"diagnosis_id": diagnosis_id}
            )
            with database.begin():
                diagnosis = database.get(Diagnosis, diagnosis_id)
                if diagnosis is not None:
                    diagnosis.status = DiagnosisStatus.FAILED
    finally:
        database.close()


def _complete_diagnosis(database: Session, diagnosis_id: int) -> None:
    diagnosis = database.get(Diagnosis, diagnosis_id)
    if (
        diagnosis is None
        or diagnosis.business is None
        or diagnosis.dataset is None
        or diagnosis.public_data_snapshot is None
    ):
        raise RuntimeError("실행할 진단 데이터를 찾을 수 없습니다.")

    input_data = collect_analysis_input(diagnosis.business, diagnosis.dataset)
    benchmark = benchmark_from_raw_data(diagnosis.public_data_snapshot.raw_data)
    result = analyze(input_data, benchmark)
    diagnosis.metrics = [
        DiagnosisMetric(
            metric_code=metric.code,
            current_value=metric.current_value,
            current_source_type=metric.current_source_type,
            comparison_value=metric.comparison_value,
            comparison_source_type=metric.comparison_source_type,
            difference_value=metric.difference_value,
            unit=metric.unit,
            benchmark_version=benchmark.snapshot_version,
        )
        for metric in result.metrics
    ]
    diagnosis.bottlenecks = [
        Bottleneck(
            bottleneck_type=finding.code,
            detail=finding.detail,
            severity=finding.severity,
            evidence_source_type=finding.evidence_source_type,
            evidence_description=finding.evidence_description,
            related_categories=list(finding.related_categories),
        )
        for finding in result.bottlenecks
    ]
    diagnosis.status = DiagnosisStatus.COMPLETED


def _get_or_create_business_snapshot(
    database: Session,
    business: Business,
    dataset: Dataset,
    input_data: AnalysisInput,
) -> BusinessSnapshot:
    existing = next(
        (
            snapshot
            for snapshot in dataset.snapshots
            if snapshot.business_id == business.id and snapshot.dataset_id == dataset.id
        ),
        None,
    )
    if existing is not None:
        return existing

    sales = input_data.monthly_sales_amount
    contribution_margin_rate = (
        Decimal(sales - input_data.material_cost_amount) / Decimal(sales)
        if sales > 0
        else Decimal("0")
    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    online_sales_ratio = (
        Decimal(input_data.online_sales_amount) / Decimal(sales)
        if input_data.online_sales_amount is not None and sales > 0
        else None
    )
    snapshot = BusinessSnapshot(
        business=business,
        dataset=dataset,
        reference_date=input_data.reference_date,
        snapshot_version="v1",
        monthly_net_sales_amount=sales,
        monthly_expense_amount=input_data.monthly_expense_amount,
        existing_monthly_repayment_amount=input_data.existing_monthly_repayment_amount,
        contribution_margin_rate=contribution_margin_rate,
        average_order_amount=(
            round(sales / input_data.monthly_order_count)
            if input_data.monthly_order_count > 0
            else None
        ),
        monthly_order_count=input_data.monthly_order_count,
        online_sales_ratio=online_sales_ratio,
        employee_count=input_data.employee_count,
        source_type=DataSourceType.CALCULATED,
    )
    database.add(snapshot)
    return snapshot


def _online_values(
    online_sales: list[NormalizedOnlineSale],
) -> dict[str, int | None]:
    if not online_sales:
        return {
            "sales_amount": None,
            "gross_order_amount": None,
            "platform_cost_amount": None,
            "refund_amount": None,
            "settlement_amount": None,
        }
    settlement_values = [
        sale.settlement_amount for sale in online_sales if sale.settlement_amount is not None
    ]
    return {
        "sales_amount": sum(sale.sales_amount for sale in online_sales),
        "gross_order_amount": sum(sale.gross_order_amount for sale in online_sales),
        "platform_cost_amount": sum(
            sale.platform_fee_amount + sale.payment_fee_amount + sale.merchant_delivery_fee
            for sale in online_sales
        ),
        "refund_amount": sum(sale.refund_amount for sale in online_sales),
        "settlement_amount": sum(settlement_values) if settlement_values else None,
    }


def _expense_total(
    expenses: list[NormalizedExpense],
    category: ExpenseCategory,
) -> int:
    return sum(expense.total_amount for expense in expenses if expense.expense_category is category)


def _same_month(value: date, reference_date: date) -> bool:
    return value.year == reference_date.year and value.month == reference_date.month


def _time_bucket(hour: int) -> str:
    if hour < 6:
        return "00_06"
    if hour < 11:
        return "06_11"
    if hour < 14:
        return "11_14"
    if hour < 17:
        return "14_17"
    if hour < 21:
        return "17_21"
    return "21_24"
