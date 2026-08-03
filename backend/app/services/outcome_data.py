# MOCK·파일·수동 사후 성과 데이터를 스냅샷과 함께 원자적으로 저장하는 서비스
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.domain.dataset import BusinessSnapshot, Dataset, DatasetFile
from app.domain.enums import (
    DatasetFileType,
    DatasetStatus,
    DataSourceType,
    OutcomeDataSourceType,
    OutcomeDataStatus,
)
from app.domain.execution import Execution
from app.domain.outcome import OutcomeComparison, OutcomeData
from app.services.dataset_import import (
    ParsedWorkbook,
    WorkbookProcessingError,
    analyze_workbook,
    normalize_rows,
)
from app.services.diagnosis_analysis import AnalysisInput, DiagnosisAnalysisError
from app.services.diagnosis_service import collect_analysis_input
from app.services.outcome_engine import OutcomeCalculationError, OutcomeEngine
from app.services.verification import require_owned_business, require_owned_simulation

WorkbookAnalyzer = Callable[[bytes, DatasetFileType], ParsedWorkbook]
RowNormalizer = Callable[[ParsedWorkbook, int, int], list]
AnalysisCollector = Callable[[object, Dataset], AnalysisInput]


@dataclass(frozen=True)
class ManualOutcomeMetrics:
    monthly_sales_amount: int
    operating_profit_amount: int
    online_order_ratio: Decimal
    cash_after_repayment_amount: int


@dataclass(frozen=True)
class OutcomeFile:
    filename: str
    contents: bytes


@dataclass(frozen=True)
class OutcomeDataCreationCommand:
    simulation_id: int
    source_type: OutcomeDataSourceType
    metrics: ManualOutcomeMetrics | None = None
    sales_file: OutcomeFile | None = None
    expense_file: OutcomeFile | None = None


@dataclass(frozen=True)
class OutcomeDataCreated:
    outcome_data_id: int
    simulation_id: int
    source_type: str
    status: str
    dataset_id: int
    observed_at: date


@dataclass(frozen=True)
class _PreparedOutcomeData:
    simulation_id: int
    business_id: int
    baseline_monthly_revenue: int
    baseline_contribution_margin_rate: Decimal
    baseline_average_order_amount: int | None
    baseline_monthly_order_count: int | None
    baseline_employee_count: int


@dataclass(frozen=True)
class _ParsedOutcomeFiles:
    sales: ParsedWorkbook
    expense: ParsedWorkbook
    sales_filename: str
    expense_filename: str


class OutcomeDataService:
    def __init__(
        self,
        database: Session,
        engine: OutcomeEngine,
        *,
        workbook_analyzer: WorkbookAnalyzer = analyze_workbook,
        row_normalizer: RowNormalizer = normalize_rows,
        analysis_collector: AnalysisCollector = collect_analysis_input,
    ) -> None:
        self.database = database
        self.engine = engine
        self.workbook_analyzer = workbook_analyzer
        self.row_normalizer = row_normalizer
        self.analysis_collector = analysis_collector

    def create(
        self,
        command: OutcomeDataCreationCommand,
        session_cookie: str | None,
        *,
        observed_on: date | None = None,
    ) -> OutcomeDataCreated:
        observation_date = observed_on or datetime.now(UTC).date()
        try:
            prepared = self._prepare(command.simulation_id, session_cookie)
        except ApiError:
            self.database.rollback()
            raise
        self.database.rollback()

        parsed_files = None
        raw_pos_data = None
        if command.source_type is OutcomeDataSourceType.FILE_UPLOAD:
            parsed_files = self._parse_files(command)
        elif command.source_type is OutcomeDataSourceType.MOCK:
            _require_mock_contract(command)
            try:
                raw_pos_data = deepcopy(
                    self.engine.generate_mock(prepared.baseline_monthly_revenue)
                )
            except OutcomeCalculationError as error:
                raise ApiError(
                    502,
                    "OUTCOME_CALCULATION_FAILED",
                    "결과 검증 계산에 실패했습니다.",
                ) from error
            _validate_mock_data(raw_pos_data)
        elif command.source_type is OutcomeDataSourceType.MANUAL_INPUT:
            _validate_manual_contract(command)
        else:
            raise ApiError(400, "INVALID_OUTCOME_SOURCE", "지원하지 않는 사후 데이터 형식입니다.")

        try:
            with self.database.begin():
                simulation = require_owned_simulation(
                    self.database,
                    prepared.simulation_id,
                    session_cookie,
                    with_for_update=True,
                )
                self._require_prerequisites(simulation.id)
                business = require_owned_business(
                    self.database,
                    prepared.business_id,
                    session_cookie,
                )
                dataset = Dataset(
                    business=business,
                    status=DatasetStatus.READY,
                    dataset_version="outcome-v1",
                    files=[],
                )
                self.database.add(dataset)

                if parsed_files is not None:
                    snapshot = self._build_file_snapshot(
                        dataset,
                        business,
                        parsed_files,
                    )
                    status = OutcomeDataStatus.MAPPING_READY
                elif raw_pos_data is not None:
                    self.database.flush()
                    snapshot = _build_mock_snapshot(
                        dataset,
                        business,
                        prepared,
                        raw_pos_data,
                        observation_date,
                    )
                    status = OutcomeDataStatus.READY
                else:
                    self.database.flush()
                    snapshot = _build_manual_snapshot(
                        dataset,
                        business,
                        prepared,
                        command.metrics,
                        observation_date,
                    )
                    status = OutcomeDataStatus.READY

                outcome = OutcomeData(
                    simulation=simulation,
                    dataset=dataset,
                    observed_business_snapshot=snapshot,
                    source_type=command.source_type,
                    observed_at=observation_date,
                    status=status,
                    raw_pos_data=raw_pos_data,
                    monthly_sales_amount=(
                        command.metrics.monthly_sales_amount if command.metrics else None
                    ),
                    operating_profit_amount=(
                        command.metrics.operating_profit_amount if command.metrics else None
                    ),
                    online_order_ratio=(
                        command.metrics.online_order_ratio if command.metrics else None
                    ),
                    cash_after_repayment_amount=(
                        command.metrics.cash_after_repayment_amount if command.metrics else None
                    ),
                )
                self.database.add(snapshot)
                self.database.add(outcome)
                self.database.flush()
                if outcome.id is None:
                    raise RuntimeError("사후 데이터 식별자가 생성되지 않았습니다.")
        except IntegrityError as error:
            raise ApiError(
                409,
                "OUTCOME_DATA_ALREADY_EXISTS",
                "이미 사후 데이터가 등록된 시뮬레이션입니다.",
            ) from error

        return OutcomeDataCreated(
            outcome_data_id=outcome.id,
            simulation_id=prepared.simulation_id,
            source_type=command.source_type.name,
            status=status.name,
            dataset_id=dataset.id,
            observed_at=observation_date,
        )

    def _prepare(
        self,
        simulation_id: int,
        session_cookie: str | None,
    ) -> _PreparedOutcomeData:
        simulation = require_owned_simulation(self.database, simulation_id, session_cookie)
        self._require_prerequisites(simulation_id)
        if simulation.business_id is None or simulation.business_snapshot_id is None:
            raise ApiError(409, "BASELINE_NOT_READY", "기준 사업 스냅샷이 필요합니다.")
        baseline = self.database.get(BusinessSnapshot, simulation.business_snapshot_id)
        if baseline is None:
            raise ApiError(409, "BASELINE_NOT_READY", "기준 사업 스냅샷이 필요합니다.")
        return _PreparedOutcomeData(
            simulation_id=simulation_id,
            business_id=simulation.business_id,
            baseline_monthly_revenue=baseline.monthly_net_sales_amount,
            baseline_contribution_margin_rate=baseline.contribution_margin_rate,
            baseline_average_order_amount=baseline.average_order_amount,
            baseline_monthly_order_count=baseline.monthly_order_count,
            baseline_employee_count=baseline.employee_count,
        )

    def _require_prerequisites(self, simulation_id: int) -> None:
        executions = self.database.scalars(
            select(Execution).where(Execution.simulation_id == simulation_id)
        ).all()
        if not any(item.simulation_id == simulation_id for item in executions):
            raise ApiError(
                409,
                "EXECUTION_REQUIRED",
                "실제 집행을 먼저 등록해야 합니다.",
            )
        outcomes = self.database.scalars(
            select(OutcomeData).where(OutcomeData.simulation_id == simulation_id)
        ).all()
        for outcome_data in outcomes:
            comparisons = self.database.scalars(
                select(OutcomeComparison).where(
                    OutcomeComparison.outcome_data_id == outcome_data.id
                )
            ).all()
            if comparisons:
                raise ApiError(
                    409,
                    "OUTCOME_DATA_ALREADY_EXISTS",
                    "이미 사후 데이터가 등록된 시뮬레이션입니다.",
                )
            # 비교로 이어지지 못한 이전 시도(중간 오류로 끊긴 등록)는 재시도를 위해 정리한다.
            self.database.delete(outcome_data)

    def _parse_files(self, command: OutcomeDataCreationCommand) -> _ParsedOutcomeFiles:
        if (
            command.metrics is not None
            or command.sales_file is None
            or command.expense_file is None
            or not command.sales_file.filename.lower().endswith(".xlsx")
            or not command.expense_file.filename.lower().endswith(".xlsx")
        ):
            raise ApiError(400, "OUTCOME_FILE_INVALID", "매출·비용 xlsx 파일이 필요합니다.")
        try:
            sales = self.workbook_analyzer(command.sales_file.contents, DatasetFileType.SALE)
            expense = self.workbook_analyzer(
                command.expense_file.contents,
                DatasetFileType.EXPENSE,
            )
        except WorkbookProcessingError as error:
            raise ApiError(400, "OUTCOME_FILE_INVALID", "xlsx 파일을 읽을 수 없습니다.") from error
        if sales.missing_columns or expense.missing_columns:
            raise ApiError(
                400,
                "OUTCOME_FILE_MAPPING_FAILED",
                "업로드 파일의 필수 컬럼을 자동 매핑할 수 없습니다.",
            )
        return _ParsedOutcomeFiles(
            sales=sales,
            expense=expense,
            sales_filename=command.sales_file.filename,
            expense_filename=command.expense_file.filename,
        )

    def _build_file_snapshot(
        self,
        dataset: Dataset,
        business,
        parsed_files: _ParsedOutcomeFiles,
    ) -> BusinessSnapshot:
        files = [
            _dataset_file(parsed_files.sales_filename, parsed_files.sales),
            _dataset_file(parsed_files.expense_filename, parsed_files.expense),
        ]
        dataset.files.extend(files)
        self.database.flush()
        if dataset.id is None or any(item.id is None for item in files):
            raise RuntimeError("사후 데이터셋 식별자가 생성되지 않았습니다.")
        try:
            sales = self.row_normalizer(parsed_files.sales, dataset.id, files[0].id)
            expenses = self.row_normalizer(parsed_files.expense, dataset.id, files[1].id)
        except WorkbookProcessingError as error:
            raise ApiError(
                400, "OUTCOME_FILE_INVALID", "xlsx 행을 정규화할 수 없습니다."
            ) from error
        dataset.sales.extend(sales)
        dataset.expenses.extend(expenses)
        for row in [*sales, *expenses]:
            self.database.add(row)
        dataset.validate_ready()
        try:
            input_data = self.analysis_collector(business, dataset)
        except DiagnosisAnalysisError as error:
            raise ApiError(
                400, "OUTCOME_FILE_INVALID", "사후 데이터를 집계할 수 없습니다."
            ) from error
        return _build_snapshot_from_analysis(dataset, business, input_data)


def _dataset_file(filename: str, parsed: ParsedWorkbook) -> DatasetFile:
    return DatasetFile(
        file_type=parsed.file_type,
        original_filename=filename,
        storage_path=None,
        detected_format=parsed.detected_format,
        source_type=DataSourceType.USER_INPUT,
        file_metadata={
            "columnMapping": parsed.column_mapping,
            "missingColumns": parsed.missing_columns,
            "mappingConfidence": parsed.mapping_confidence,
            "rowCount": len(parsed.rows),
        },
    )


def _build_snapshot_from_analysis(
    dataset: Dataset,
    business,
    input_data: AnalysisInput,
) -> BusinessSnapshot:
    sales = input_data.monthly_sales_amount
    margin = (
        Decimal(sales - input_data.material_cost_amount) / Decimal(sales)
        if sales > 0
        else Decimal("0")
    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    online_ratio = (
        Decimal(input_data.online_sales_amount) / Decimal(sales)
        if input_data.online_sales_amount is not None and sales > 0
        else None
    )
    return BusinessSnapshot(
        business=business,
        dataset=dataset,
        reference_date=input_data.reference_date,
        snapshot_version="outcome-v1",
        monthly_net_sales_amount=sales,
        monthly_expense_amount=input_data.monthly_expense_amount,
        existing_monthly_repayment_amount=0,
        contribution_margin_rate=margin,
        average_order_amount=(
            round(sales / input_data.monthly_order_count)
            if input_data.monthly_order_count > 0
            else None
        ),
        monthly_order_count=input_data.monthly_order_count,
        online_sales_ratio=online_ratio,
        employee_count=input_data.employee_count,
        source_type=DataSourceType.CALCULATED,
    )


def _build_manual_snapshot(
    dataset: Dataset,
    business,
    prepared: _PreparedOutcomeData,
    metrics: ManualOutcomeMetrics | None,
    observed_on: date,
) -> BusinessSnapshot:
    if metrics is None:
        raise ApiError(400, "INVALID_OUTCOME_METRIC", "수동 성과 지표가 필요합니다.")
    monthly_expense = metrics.monthly_sales_amount - metrics.operating_profit_amount
    if monthly_expense < 0:
        raise ApiError(
            400,
            "INVALID_OUTCOME_METRIC",
            "영업이익은 월 매출보다 클 수 없습니다.",
        )
    return BusinessSnapshot(
        business=business,
        dataset=dataset,
        reference_date=observed_on,
        snapshot_version="outcome-v1",
        monthly_net_sales_amount=metrics.monthly_sales_amount,
        monthly_expense_amount=monthly_expense,
        existing_monthly_repayment_amount=0,
        contribution_margin_rate=prepared.baseline_contribution_margin_rate,
        average_order_amount=prepared.baseline_average_order_amount,
        monthly_order_count=prepared.baseline_monthly_order_count,
        online_sales_ratio=None,
        employee_count=prepared.baseline_employee_count,
        source_type=DataSourceType.USER_INPUT,
    )


def _build_mock_snapshot(
    dataset: Dataset,
    business,
    prepared: _PreparedOutcomeData,
    raw_pos_data: dict,
    observed_on: date,
) -> BusinessSnapshot:
    revenue = raw_pos_data["monthly_revenue"]
    cogs = raw_pos_data["monthly_cogs"]
    labor = raw_pos_data["monthly_labor_cost"]
    daily_customers = raw_pos_data.get("avg_daily_customers")
    monthly_orders = round(daily_customers * 30) if daily_customers is not None else None
    online = raw_pos_data.get("online_data")
    online_ratio = (
        Decimal(online["online_gross_order_amount"]) / Decimal(revenue)
        if online and revenue > 0
        else None
    )
    return BusinessSnapshot(
        business=business,
        dataset=dataset,
        reference_date=observed_on,
        snapshot_version="outcome-v1",
        monthly_net_sales_amount=revenue,
        monthly_expense_amount=cogs + labor,
        existing_monthly_repayment_amount=0,
        contribution_margin_rate=(Decimal(revenue - cogs) / Decimal(revenue)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        ),
        average_order_amount=(
            round(revenue / monthly_orders) if monthly_orders and monthly_orders > 0 else None
        ),
        monthly_order_count=monthly_orders,
        online_sales_ratio=online_ratio,
        employee_count=prepared.baseline_employee_count,
        source_type=DataSourceType.SYNTHETIC_SALES,
    )


def _validate_manual_contract(command: OutcomeDataCreationCommand) -> None:
    metrics = command.metrics
    if command.sales_file is not None or command.expense_file is not None or metrics is None:
        raise ApiError(400, "INVALID_OUTCOME_METRIC", "수동 성과 지표만 입력해야 합니다.")
    if metrics.monthly_sales_amount <= 0 or not Decimal(
        "0"
    ) <= metrics.online_order_ratio <= Decimal("1"):
        raise ApiError(400, "INVALID_OUTCOME_METRIC", "수동 성과 지표 범위가 올바르지 않습니다.")
    if metrics.monthly_sales_amount - metrics.operating_profit_amount < 0:
        raise ApiError(400, "INVALID_OUTCOME_METRIC", "영업이익은 월 매출보다 클 수 없습니다.")


def _require_mock_contract(command: OutcomeDataCreationCommand) -> None:
    if (
        command.metrics is not None
        or command.sales_file is not None
        or command.expense_file is not None
    ):
        raise ApiError(
            400, "INVALID_OUTCOME_SOURCE", "Mock 요청에는 추가 데이터를 입력할 수 없습니다."
        )


def _validate_mock_data(raw_pos_data: dict) -> None:
    try:
        revenue = raw_pos_data["monthly_revenue"]
        cogs = raw_pos_data["monthly_cogs"]
        labor = raw_pos_data["monthly_labor_cost"]
    except (KeyError, TypeError) as error:
        raise ApiError(
            502, "OUTCOME_CALCULATION_FAILED", "결과 검증 계산에 실패했습니다."
        ) from error
    if revenue <= 0 or cogs < 0 or labor < 0:
        raise ApiError(502, "OUTCOME_CALCULATION_FAILED", "결과 검증 계산에 실패했습니다.")
