# 도메인 모델에서 문자열로 저장하는 고정 상태와 분류를 정의하는 모듈
from enum import StrEnum


class DataSourceType(StrEnum):
    PUBLIC_DATA = "public_data"
    SYNTHETIC_SALES = "synthetic_sales"
    SYNTHETIC_EXPENSE = "synthetic_expense"
    SYNTHETIC_ONLINE_SALES = "synthetic_online_sales"
    USER_INPUT = "user_input"
    BENCHMARK = "benchmark"
    DOMAIN_ASSUMPTION = "domain_assumption"
    CALCULATED = "calculated"
    AI_GENERATED_TEXT = "ai_generated_text"


class DatasetStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    NORMALIZING = "normalizing"
    READY = "ready"
    NEEDS_REUPLOAD = "needs_reupload"
    FAILED = "failed"


class DatasetFileType(StrEnum):
    SALE = "sale"
    EXPENSE = "expense"
    ONLINE_SALE = "online_sale"


class DatasetFormat(StrEnum):
    EASYPOS_SALES = "easypos_sales"
    EASYSHOP_EXPENSE_LEDGER = "easyshop_expense_ledger"
    EASYSHOP_ONLINE_SALES = "easyshop_online_sales"
    UNKNOWN = "unknown"


class ExpenseCategory(StrEnum):
    MATERIAL = "material"
    LABOR = "labor"
    RENT = "rent"
    UTILITY = "utility"
    MARKETING = "marketing"
    COMMISSION = "commission"
    PLATFORM_FEE = "platform_fee"
    SUPPLIES = "supplies"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class OnlineSalesReconciliationType(StrEnum):
    INCLUDED_IN_POS_TOTAL = "included_in_pos_total"
    SEPARATE_FROM_POS_TOTAL = "separate_from_pos_total"


class DiagnosisStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DiagnosisEvidenceSource(StrEnum):
    BUSINESS_AND_PUBLIC_DATA = "business_and_public_data"


class BottleneckSeverity(StrEnum):
    MILD = "mild"
    CLEAR = "clear"
    SEVERE = "severe"


class AllocationCategory(StrEnum):
    MARKETING_ONLINE = "marketing_online"
    EQUIPMENT_INTERIOR = "equipment_interior"
    LABOR = "labor"
    INVENTORY = "inventory"


class ScenarioCode(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class RepaymentType(StrEnum):
    EQUAL_PAYMENT = "equal_payment"
    EQUAL_PRINCIPAL = "equal_principal"
    BULLET_PAYMENT = "bullet_payment"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExecutionType(StrEnum):
    EXACT_SELECTED = "exact_selected"
    MODIFIED = "modified"
    MIXED = "mixed"
    CUSTOM = "custom"
    MOCK = "mock"


class OutcomeStatus(StrEnum):
    MET = "met"
    PARTIALLY_MET = "partially_met"
    NOT_MET = "not_met"
    NOT_COMPARABLE = "not_comparable"


class BottleneckChangeType(StrEnum):
    RESOLVED = "resolved"
    REMAINING = "remaining"
    NEW = "new"
