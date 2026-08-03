# 기존 AI 결과 추적과 재무 계산을 같은 프로세스에서 호출하는 어댑터
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol

from requests import RequestException

from app.domain.enums import RepaymentType

ResultRunner = Callable[..., dict[str, Any]]
RunnerLoader = Callable[[], ResultRunner]

REQUIRED_RESULT_KEYS = {
    "resolved_bottlenecks",
    "persisted_bottlenecks",
    "new_bottlenecks",
    "not_comparable_bottlenecks",
    "post_execution_findings",
    "post_execution_financial_result",
    "breakeven_status",
    "next_round_pos_data_snapshot",
}
LIST_RESULT_KEYS = {
    "resolved_bottlenecks",
    "persisted_bottlenecks",
    "new_bottlenecks",
    "not_comparable_bottlenecks",
    "post_execution_findings",
}
DICT_RESULT_KEYS = {
    "post_execution_financial_result",
    "breakeven_status",
    "next_round_pos_data_snapshot",
}


class OutcomeCalculationError(RuntimeError):
    pass


@dataclass(frozen=True)
class FinancialProjectionRequest:
    allocation: dict[str, float]
    loan_amount: int
    monthly_revenue: int
    annual_interest_rate: Decimal
    term_months: int
    grace_months: int
    repayment_type: RepaymentType


@dataclass(frozen=True)
class OutcomeEngineRequest(FinancialProjectionRequest):
    pre_findings: Sequence[dict[str, Any]]
    post_pos_data: dict[str, Any]
    comparable_bottleneck_types: frozenset[str] | None
    break_even_additional_revenue_target: int | None


class OutcomeEngine(Protocol):
    def generate_mock(self, monthly_revenue: int) -> dict[str, Any]: ...

    def compare(self, request: OutcomeEngineRequest) -> dict[str, Any]: ...

    def project_financial(self, request: FinancialProjectionRequest) -> dict[str, Any]: ...


class InProcessOutcomeEngine:
    def __init__(
        self,
        compare_loader: RunnerLoader | None = None,
        mock_loader: RunnerLoader | None = None,
        benchmark_loader: RunnerLoader | None = None,
        financial_loader: RunnerLoader | None = None,
    ) -> None:
        self._compare_loader = compare_loader or _load_compare_runner
        self._mock_loader = mock_loader or _load_mock_runner
        self._benchmark_loader = benchmark_loader or _load_benchmark_runner
        self._financial_loader = financial_loader or _load_financial_runner

    def generate_mock(self, monthly_revenue: int) -> dict[str, Any]:
        try:
            result = self._mock_loader()(
                scenario="normal",
                monthly_revenue=monthly_revenue,
            )
            if not isinstance(result, dict):
                raise ValueError("invalid mock result")
            return result
        except (
            ImportError,
            KeyError,
            RequestException,
            RuntimeError,
            TypeError,
            ValueError,
        ) as error:
            raise OutcomeCalculationError("결과 검증 계산에 실패했습니다.") from error

    def compare(self, request: OutcomeEngineRequest) -> dict[str, Any]:
        try:
            time_benchmark, sample_size = self._benchmark_loader()()
            result = self._compare_loader()(
                pre_findings=[dict(finding) for finding in request.pre_findings],
                pre_pos_data={},
                post_pos_data=dict(request.post_pos_data),
                time_benchmark=time_benchmark,
                time_benchmark_sample_size=sample_size,
                selected_allocation=dict(request.allocation),
                loan_amount=request.loan_amount,
                breakeven_additional_revenue_target=(request.break_even_additional_revenue_target),
                comparable_bottleneck_types=(
                    None
                    if request.comparable_bottleneck_types is None
                    else set(request.comparable_bottleneck_types)
                ),
                annual_interest_rate=float(request.annual_interest_rate),
                loan_term_months=request.term_months,
                grace_months=request.grace_months,
                repayment_type=request.repayment_type.value,
            )
            _validate_comparison_result(result)
            return result
        except (
            ImportError,
            KeyError,
            RequestException,
            RuntimeError,
            TypeError,
            ValueError,
        ) as error:
            raise OutcomeCalculationError("결과 검증 계산에 실패했습니다.") from error

    def project_financial(self, request: FinancialProjectionRequest) -> dict[str, Any]:
        try:
            result = self._financial_loader()(
                allocation=dict(request.allocation),
                loan_amount=request.loan_amount,
                baseline_monthly_revenue=request.monthly_revenue,
                annual_interest_rate=float(request.annual_interest_rate),
                loan_term_months=request.term_months,
                grace_months=request.grace_months,
                repayment_type=request.repayment_type.value,
            )
            if not isinstance(result, dict):
                raise ValueError("invalid financial result")
            return result
        except (
            ImportError,
            KeyError,
            RequestException,
            RuntimeError,
            TypeError,
            ValueError,
        ) as error:
            raise OutcomeCalculationError("결과 검증 계산에 실패했습니다.") from error


def get_outcome_engine() -> OutcomeEngine:
    return InProcessOutcomeEngine()


def _validate_comparison_result(result: object) -> None:
    if not isinstance(result, dict) or not REQUIRED_RESULT_KEYS <= result.keys():
        raise ValueError("invalid comparison result")
    if any(not isinstance(result[key], list) for key in LIST_RESULT_KEYS):
        raise ValueError("invalid comparison list")
    if any(not isinstance(result[key], dict) for key in DICT_RESULT_KEYS):
        raise ValueError("invalid comparison object")


def _ensure_ai_path() -> None:
    ai_path_text = str(_resolve_ai_path())
    if ai_path_text not in sys.path:
        sys.path.insert(0, ai_path_text)


def _resolve_ai_path() -> Path:
    current_file = Path(__file__).resolve()
    candidates = (
        # Vercel: includeFiles로 함수 번들에 포함된 경우 /var/task/ai
        current_file.parents[2] / "ai",
        # 로컬 개발: repo_root/backend/app/services/... → repo_root/ai
        current_file.parents[3] / "ai",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise ImportError(f"AI 모듈 디렉터리를 찾을 수 없습니다: {searched}")


def _load_compare_runner() -> ResultRunner:
    _ensure_ai_path()
    return import_module("outcome_tracker").compare_outcomes


def _load_mock_runner() -> ResultRunner:
    _ensure_ai_path()
    return import_module("mock_pos_data").generate_mock_pos_data


def _load_benchmark_runner() -> ResultRunner:
    _ensure_ai_path()
    return import_module("bottleneck_detector").compute_time_of_day_benchmark_with_sample_size


def _load_financial_runner() -> ResultRunner:
    _ensure_ai_path()
    return import_module("financial_calculator").calculate_financial_projection
