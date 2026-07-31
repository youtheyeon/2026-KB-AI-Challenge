# 저장 진단을 같은 프로세스의 AI 시뮬레이션 함수에 전달하는 어댑터
import sys
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol

from requests import RequestException

from app.domain.enums import RepaymentType

SimulationRunner = Callable[[list[dict], dict, dict], dict[str, Any]]
SimulationRunnerLoader = Callable[[], SimulationRunner]


class SimulationGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SimulationEngineRequest:
    findings: tuple[dict, ...]
    loan_amount: int
    annual_interest_rate: Decimal
    term_months: int
    grace_months: int
    repayment_type: RepaymentType
    baseline_monthly_revenue: int
    average_daily_customers: int


class SimulationEngine(Protocol):
    def run(self, request: SimulationEngineRequest) -> dict[str, Any]: ...


class InProcessSimulationEngine:
    def __init__(self, loader: SimulationRunnerLoader | None = None) -> None:
        self._loader = loader or _load_simulation_runner

    def run(self, request: SimulationEngineRequest) -> dict[str, Any]:
        try:
            result = self._loader()(
                [dict(finding) for finding in request.findings],
                {
                    "amount": request.loan_amount,
                    "annual_interest_rate": float(request.annual_interest_rate),
                    "term_months": request.term_months,
                    "grace_months": request.grace_months,
                    "repayment_type": request.repayment_type.value,
                },
                {
                    "monthly_revenue": request.baseline_monthly_revenue,
                    "avg_daily_customers": request.average_daily_customers,
                },
            )
        except (ImportError, RequestException, RuntimeError) as error:
            raise SimulationGenerationError("시뮬레이션 결과 생성에 실패했습니다.") from error

        if not isinstance(result, dict) or not isinstance(result.get("scenario_results"), list):
            raise SimulationGenerationError("AI 엔진이 유효하지 않은 결과를 반환했습니다.")
        return result


def get_simulation_engine() -> SimulationEngine:
    return InProcessSimulationEngine()


def _load_simulation_runner() -> SimulationRunner:
    ai_path = Path(__file__).resolve().parents[3] / "ai"
    ai_path_text = str(ai_path)
    if ai_path_text not in sys.path:
        sys.path.insert(0, ai_path_text)

    module = import_module("run_simulation")
    return module.run_allocation_simulation
