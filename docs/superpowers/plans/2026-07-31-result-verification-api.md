# Result Verification API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 저장된 시뮬레이션의 실제 집행과 사후 데이터를 한 번씩 등록하고, 근거가 있는 지표·병목만 비교해 결과 조회와 선순환 대시보드 API를 제공하며 완료 이력을 다음 시뮬레이션에 연결한다.

**Architecture:** 새 검증 라우터는 HTTP 계약과 Content-Type 분기만 담당하고, 집행·사후 데이터·결과 비교·대시보드 서비스를 책임별로 분리한다. `OutcomeEngine`이 기존 `ai/`의 Mock 생성기와 결과 추적 함수를 같은 프로세스에서 호출하며, 파일 파싱과 계산 중에는 데이터베이스 트랜잭션을 열어 두지 않고 저장 직전에 행을 잠가 재검증한다. 결과 비교가 다음 회차 POS 스냅샷을 저장하고 기존 `SimulationService`가 완료 사이클을 `business_history`로 투영해 지속 병목 상향과 부작용 경고를 다음 AI 배분 생성에 전달한다.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, pytest 9, Ruff, openpyxl, 기존 `ai/` Python 엔진.

## Global Constraints

- 구현 범위는 Notion과 GitHub 이슈 #36에 정의된 여섯 API로 한정한다.
- 외부 필드는 camelCase, 상태·분류 enum은 대문자 문자열을 사용한다.
- 집행·성공한 사후 데이터·결과 검증은 시뮬레이션당 하나인 불변 기록이며 중복 POST는 `409`다.
- 검증 가능 시점은 `Simulation.created_at`의 UTC 날짜부터 정확히 90일 이상이다.
- `includeCompleted=false`는 결과 검증이 끝난 시뮬레이션만 제외하고 집행만 등록된 대상은 유지한다.
- MOCK·MANUAL_INPUT은 JSON, FILE_UPLOAD는 같은 URL의 multipart 요청으로 받는다.
- MOCK은 전체 병목, FILE_UPLOAD는 관측 가능한 병목만 재평가하며 MANUAL_INPUT 병목은 `NOT_COMPARABLE`이다.
- 자유 집행 항목은 카테고리를 추측하지 않고 기존 계산기의 미분류 지출 가정만 `DOMAIN_ASSUMPTION`으로 적용한다.
- 대시보드 상환치는 실제 납부 기록이 아니므로 `repaymentDataType=ESTIMATED`를 반드시 반환한다.
- 저장된 완료 진단은 현재 시뮬레이션 병목의 단일 원천으로 유지하고, 결과 이력으로 현재 병목을 다시 진단하지 않는다.
- 결과 이력은 `ai/business_history.py`의 지속 병목 최소 비중과 부작용 경고에 사용하며 개인 기준선은 향후 진단 경로를 위해 POS 스냅샷만 보존한다.
- 백엔드 대문자 병목 코드는 AI 경계에서 명시적으로 정규화하고 자유 집행 항목의 카테고리는 추측하지 않는다.
- 자동 테스트에서는 실제 LLM, 외부 API와 네트워크를 호출하지 않는다.
- 기존 초기 마이그레이션을 수정하지 않고 `20260731_0003` 후속 마이그레이션을 추가한다.
- 새 Python 소스 파일 첫 줄에는 역할을 설명하는 한 줄 한국어 주석을 둔다.
- 사용자 변경인 `.gitignore`와 `docs/project-proposal-plan.md`는 수정하거나 스테이징하지 않는다.

## File Map

- Modify `backend/app/domain/enums.py` — 집행 모드, 사후 데이터 출처·상태, 지표 판정과 미관측 병목 enum.
- Modify `backend/app/domain/execution.py` — 자유 집행 이름과 nullable 카테고리.
- Modify `backend/app/domain/outcome.py` — 수동 지표, 원시 Mock 입력, 다음 회차 POS 스냅샷과 전용 상태 타입.
- Create `backend/alembic/versions/20260731_0003_result_verification_api.py` — 기존 행 변환과 컬럼·제약 변경.
- Modify `backend/tests/domain/test_execution.py`, `backend/tests/domain/test_outcome.py` — 새 도메인 불변조건.
- Modify `backend/tests/integration/test_alembic_migration.py` — 후속 마이그레이션 업·다운 검증.
- Modify `ai/bottleneck_detector.py`, `ai/outcome_tracker.py`, `ai/run_simulation.py` — 관측 가능한 병목 비교와 저장 진단 기반 선순환 이력 입력.
- Create `backend/tests/ai/test_outcome_tracker.py`, `backend/tests/ai/test_business_history.py` — 병목 분류·대출 조건과 이력 신호 테스트.
- Modify `backend/tests/ai/test_run_allocation_simulation.py` — 이력에서 최소 비중과 경고를 적용하는 회귀 테스트.
- Modify `backend/app/services/simulation_engine.py`, `backend/app/services/simulation.py` — 병목 코드 정규화와 완료 결과 이력 전달.
- Modify `backend/tests/services/test_simulation_engine.py`, `backend/tests/services/test_simulation_service.py` — AI 계약 정규화와 후속 회차 입력 테스트.
- Create `backend/app/services/outcome_engine.py` — Mock 생성·AI 결과 비교 프로토콜과 같은 프로세스 어댑터.
- Create `backend/tests/services/test_outcome_engine.py` — 어댑터 변환·형상·예외 테스트.
- Create `backend/app/services/verification.py` — 소유권 공통 검사, 검증 대상 조회와 실제 집행 생성.
- Create `backend/tests/services/test_verification_service.py` — 90일·필터·집행·잠금 테스트.
- Create `backend/app/services/outcome_data.py` — JSON·xlsx 사후 데이터 정규화와 저장.
- Create `backend/tests/services/test_outcome_data_service.py` — 세 입력 방식과 원자성 테스트.
- Create `backend/app/services/outcome.py` — 지표·병목 비교 생성과 저장 결과 조회.
- Create `backend/tests/services/test_outcome_service.py` — 상태 판정, 부분 비교, 중복·재계산 방지 테스트.
- Create `backend/app/services/dashboard.py` — 저장된 사이클과 상환 추정치 투영.
- Create `backend/tests/services/test_dashboard_service.py` — 상환 방식·추세·다음 초기 조건 테스트.
- Create `backend/app/api/routes/verifications.py` — 여섯 API와 두 Content-Type OpenAPI 계약.
- Modify `backend/app/main.py` — 검증 라우터 등록.
- Create `backend/tests/api/test_verifications.py` — camelCase, Content-Type, 상태 코드와 오류 계약.
- Create `backend/tests/integration/test_verification_api.py` — PostgreSQL 전체 그래프·중복·롤백 테스트.
- Modify `checklist.md`, `context-notes.md` — 진행 상태와 실제 검증 결과 기록.

---

### Task 1: Domain model and follow-up migration

**Files:**
- Modify: `backend/app/domain/enums.py`
- Modify: `backend/app/domain/execution.py`
- Modify: `backend/app/domain/outcome.py`
- Create: `backend/alembic/versions/20260731_0003_result_verification_api.py`
- Modify: `backend/tests/domain/test_execution.py`
- Modify: `backend/tests/domain/test_outcome.py`
- Modify: `backend/tests/integration/test_alembic_migration.py`

**Interfaces:**
- Produces: `ExecutionType.SAME_AS_A`, `SAME_AS_B`, `SAME_AS_C`, `MIXED`, `CUSTOM`.
- Produces: `OutcomeDataSourceType`, `OutcomeDataStatus`, `OutcomeMetricStatus`.
- Produces: `ExecutionAllocation(name: str, category: AllocationCategory | None, amount: int)`.
- Produces: `OutcomeData.raw_pos_data`, `OutcomeComparison.next_round_pos_data_snapshot` and four nullable manual metric columns.
- Produces: database revision `20260731_0003` with downgrade to `20260730_0002`.

- [ ] **Step 1: Record the baseline before changing code**

Run:

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
```

Expected: all existing non-PostgreSQL tests pass, PostgreSQL tests skip only when `TEST_DATABASE_URL` is absent, and both Ruff commands exit `0`. Append the exact pass·skip counts to `context-notes.md`.

- [ ] **Step 2: Write failing domain tests**

Add these assertions to the existing domain test files.

```python
def test_execution_allocation_accepts_free_name_without_category() -> None:
    allocation = ExecutionAllocation(name="저녁 시간대 광고", category=None, amount=800_000)
    assert allocation.name == "저녁 시간대 광고"
    assert allocation.category is None


def test_outcome_data_uses_dedicated_source_status_and_manual_metrics() -> None:
    outcome = OutcomeData(
        simulation_id=1,
        observed_business_snapshot_id=2,
        source_type=OutcomeDataSourceType.MANUAL_INPUT,
        status=OutcomeDataStatus.READY,
        monthly_sales_amount=32_000_000,
        operating_profit_amount=6_200_000,
        online_order_ratio=Decimal("0.31"),
        cash_after_repayment_amount=2_800_000,
    )
    assert outcome.source_type is OutcomeDataSourceType.MANUAL_INPUT
    assert outcome.status is OutcomeDataStatus.READY


def test_outcome_metric_status_is_separate_from_overall_status() -> None:
    metric = OutcomeComparisonMetric(
        metric_code="MONTHLY_SALES",
        unit="KRW",
        status=OutcomeMetricStatus.ABOVE_EXPECTED,
    )
    assert metric.status is OutcomeMetricStatus.ABOVE_EXPECTED


def test_outcome_comparison_keeps_next_round_pos_snapshot() -> None:
    comparison = OutcomeComparison(
        simulation_id=1,
        execution_id=2,
        outcome_data_id=3,
        status=OutcomeStatus.MET,
        next_round_pos_data_snapshot={"monthly_revenue": 8_100_000},
    )
    assert comparison.next_round_pos_data_snapshot["monthly_revenue"] == 8_100_000
```

Run: `cd backend && .venv/bin/pytest tests/domain/test_execution.py tests/domain/test_outcome.py -q`

Expected: FAIL because the new enum members and columns do not exist.

- [ ] **Step 3: Add the minimum enum and model changes**

Use lower-case database values while the API later returns enum names.

```python
class ExecutionType(StrEnum):
    SAME_AS_A = "same_as_a"
    SAME_AS_B = "same_as_b"
    SAME_AS_C = "same_as_c"
    MIXED = "mixed"
    CUSTOM = "custom"


class OutcomeDataSourceType(StrEnum):
    MOCK = "mock"
    FILE_UPLOAD = "file_upload"
    MANUAL_INPUT = "manual_input"


class OutcomeDataStatus(StrEnum):
    READY = "ready"
    MAPPING_READY = "mapping_ready"
    FAILED = "failed"


class OutcomeMetricStatus(StrEnum):
    ABOVE_EXPECTED = "above_expected"
    WITHIN_RANGE = "within_range"
    BELOW_EXPECTED = "below_expected"
    NOT_COMPARABLE = "not_comparable"
```

Keep `OutcomeStatus` for the overall comparison. Add `NOT_COMPARABLE = "not_comparable"` to `BottleneckChangeType`. In `ExecutionAllocation`, add `name: Mapped[str] = mapped_column(String(255), nullable=False)`, make `category` nullable, and keep the existing non-negative amount constraint and category uniqueness.

In `OutcomeData`, replace `DataSourceType` and the raw string status with the dedicated enums and add these columns.

```python
raw_pos_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
monthly_sales_amount: Mapped[int | None] = mapped_column(BigInteger)
operating_profit_amount: Mapped[int | None] = mapped_column(BigInteger)
online_order_ratio: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
cash_after_repayment_amount: Mapped[int | None] = mapped_column(BigInteger)
```

Add `next_round_pos_data_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)` to `OutcomeComparison`. Change only `OutcomeComparisonMetric.status` to `OutcomeMetricStatus`; leave `OutcomeComparison.status` as `OutcomeStatus`.

Run: `cd backend && .venv/bin/pytest tests/domain/test_execution.py tests/domain/test_outcome.py -q`

Expected: PASS.

- [ ] **Step 4: Write the migration and migration assertions**

Create revision metadata exactly as follows.

```python
# 결과 검증 API에 필요한 집행·사후 데이터 컬럼과 상태 제약을 추가하는 마이그레이션
revision = "20260731_0003"
down_revision = "20260730_0002"
branch_labels = None
depends_on = None
```

The upgrade must perform these deterministic conversions before replacing check constraints.

```sql
UPDATE executions e
SET execution_type = CASE s.code
    WHEN 'A' THEN 'same_as_a'
    WHEN 'B' THEN 'same_as_b'
    WHEN 'C' THEN 'same_as_c'
END
FROM scenario_selections ss
JOIN scenarios s ON s.id = ss.scenario_id
WHERE e.selection_id = ss.id AND e.execution_type = 'exact_selected';

UPDATE executions SET execution_type = 'mixed' WHERE execution_type = 'modified';
UPDATE executions SET execution_type = 'custom' WHERE execution_type = 'mock';

UPDATE outcome_data
SET source_type = CASE
    WHEN source_type LIKE 'synthetic_%' THEN 'mock'
    WHEN source_type = 'user_input' THEN 'manual_input'
    ELSE 'file_upload'
END;

UPDATE outcome_data
SET status = CASE
    WHEN lower(status) = 'ready' THEN 'ready'
    WHEN lower(status) = 'mapping_ready' THEN 'mapping_ready'
    ELSE 'failed'
END;

UPDATE outcome_comparison_metrics
SET status = CASE status
    WHEN 'met' THEN 'above_expected'
    WHEN 'partially_met' THEN 'within_range'
    WHEN 'not_met' THEN 'below_expected'
    ELSE 'not_comparable'
END;
```

Add `execution_allocations.name`, backfill it from the four category display names, make it non-null, and make `category` nullable. Add the five `OutcomeData` fields and recreate the non-native enum checks for execution type, outcome data source·status, outcome metric status and bottleneck change type. Downgrade must reverse the value mapping before restoring the old constraints and columns. Before restoring non-null category, query for null categories and raise a clear `RuntimeError` if custom allocations exist; do not silently delete or relabel user data.

Extend `test_alembic_migration.py` with exact schema checks.

```python
columns = {column["name"]: column for column in inspect(engine).get_columns("outcome_data")}
assert {
    "raw_pos_data",
    "monthly_sales_amount",
    "operating_profit_amount",
    "online_order_ratio",
    "cash_after_repayment_amount",
} <= set(columns)
comparison_columns = {
    column["name"]: column for column in inspect(engine).get_columns("outcome_comparisons")
}
assert "next_round_pos_data_snapshot" in comparison_columns
execution_columns = {
    column["name"]: column for column in inspect(engine).get_columns("execution_allocations")
}
assert execution_columns["name"]["nullable"] is False
assert execution_columns["category"]["nullable"] is True
```

Run with an isolated database:

```bash
cd backend
ALLOW_DESTRUCTIVE_TEST_DATABASE_RESET=1 TEST_DATABASE_URL=postgresql+psycopg://keemhoeyune@127.0.0.1:55432/kb_domain_test .venv/bin/pytest tests/integration/test_alembic_migration.py -q
```

Expected: PASS when the isolated PostgreSQL database is available; otherwise record the connection blocker and do not use any non-test database.

- [ ] **Step 5: Run the domain regression and commit**

Run:

```bash
cd backend
.venv/bin/pytest tests/domain/test_execution.py tests/domain/test_outcome.py -q
.venv/bin/ruff check app/domain tests/domain tests/integration/test_alembic_migration.py
.venv/bin/ruff format --check app/domain tests/domain tests/integration/test_alembic_migration.py
```

Expected: all commands exit `0`.

Commit:

```bash
git add backend/app/domain/enums.py backend/app/domain/execution.py backend/app/domain/outcome.py backend/alembic/versions/20260731_0003_result_verification_api.py backend/tests/domain/test_execution.py backend/tests/domain/test_outcome.py backend/tests/integration/test_alembic_migration.py context-notes.md
git commit -m "feat: 결과 검증 도메인 계약 확장"
```

---

### Task 2: Partial bottleneck comparison in AI

**Files:**
- Modify: `ai/bottleneck_detector.py`
- Modify: `ai/outcome_tracker.py`
- Modify: `ai/run_simulation.py`
- Create: `backend/tests/ai/test_outcome_tracker.py`
- Create: `backend/tests/ai/test_business_history.py`
- Modify: `backend/tests/ai/test_run_allocation_simulation.py`

**Interfaces:**
- Produces: `detect_bottlenecks(user_data: dict, time_benchmark: dict, assumptions: dict = INDUSTRY_ASSUMPTIONS, time_benchmark_sample_size: int | None = None, comparable_bottleneck_types: set[str] | None = None) -> list`.
- Produces: `compare_outcomes(pre_findings: list, pre_pos_data: dict, post_pos_data: dict, time_benchmark: dict, time_benchmark_sample_size: int, selected_allocation: dict, loan_amount: int, breakeven_additional_revenue_target: float | None = None, comparable_bottleneck_types: set[str] | None = None, annual_interest_rate: float = 0.045, loan_term_months: int = 36, grace_months: int = 0, repayment_type: str = "equal_payment") -> dict`.
- Produces: `not_comparable_bottlenecks` in the comparison result.
- Produces: `run_allocation_simulation(..., business_history: list | None = None)` while preserving existing callers.

- [ ] **Step 1: Write failing AI behavior tests**

Create `backend/tests/ai/test_outcome_tracker.py`.

```python
# 관측 가능한 집행 후 지표만 병목 변화로 판정하는 AI 결과 추적 테스트
from outcome_tracker import compare_outcomes


def test_unobserved_preexisting_bottleneck_is_not_marked_resolved(monkeypatch) -> None:
    monkeypatch.setattr(
        "outcome_tracker.detect_bottlenecks",
        lambda *args, **kwargs: [
            {"bottleneck_type": "high_cost_ratio"},
            {"bottleneck_type": "high_labor_ratio"},
        ],
    )
    result = compare_outcomes(
        pre_findings=[
            {"bottleneck_type": "high_cost_ratio"},
            {"bottleneck_type": "low_repeat_rate"},
        ],
        pre_pos_data={},
        post_pos_data={"monthly_revenue": 8_100_000},
        time_benchmark={},
        time_benchmark_sample_size=0,
        selected_allocation={"custom_1": 1.0},
        loan_amount=15_000_000,
        comparable_bottleneck_types={"high_cost_ratio", "high_labor_ratio"},
    )
    assert result["persisted_bottlenecks"] == ["high_cost_ratio"]
    assert result["new_bottlenecks"] == ["high_labor_ratio"]
    assert result["not_comparable_bottlenecks"] == ["low_repeat_rate"]
    assert result["resolved_bottlenecks"] == []
```

Add a second test that spies on `calculate_financial_projection` and asserts `annual_interest_rate`, `loan_term_months`, `grace_months` and `repayment_type` are passed unchanged.

Run: `cd backend && .venv/bin/pytest tests/ai/test_outcome_tracker.py -q`

Expected: FAIL because the optional arguments and result key do not exist.

- [ ] **Step 2: Make bottleneck detection skip unavailable dimensions**

Add one local predicate at the top of `detect_bottlenecks()`.

```python
def can_compare(bottleneck_type: str) -> bool:
    return (
        comparable_bottleneck_types is None
        or bottleneck_type in comparable_bottleneck_types
    )
```

Guard each of the five base checks and each of the four online checks with `can_compare()`. Do not read `time_of_day_sales`, `monthly_cogs`, `monthly_labor_cost`, `repeat_customer_rate`, seat fields or online fields when the corresponding type is unavailable. The default `None` path must preserve every existing call exactly.

- [ ] **Step 3: Extend outcome tracking without changing the default result**

Use the comparable set only for set classification.

```python
post_findings = detect_bottlenecks(
    post_pos_data,
    time_benchmark,
    time_benchmark_sample_size=time_benchmark_sample_size,
    comparable_bottleneck_types=comparable_bottleneck_types,
)
pre_types = {finding["bottleneck_type"] for finding in pre_findings}
post_types = {finding["bottleneck_type"] for finding in post_findings}
comparable = (
    pre_types | post_types
    if comparable_bottleneck_types is None
    else set(comparable_bottleneck_types)
)
resolved = (pre_types & comparable) - post_types
persisted = (pre_types & comparable) & post_types
newly_emerged = post_types - pre_types
not_comparable = pre_types - comparable
```

Pass the four loan condition arguments through to `calculate_financial_projection()` and return `not_comparable_bottlenecks=sorted(not_comparable)`.

Run: `cd backend && .venv/bin/pytest tests/ai -q`

Expected: all AI tests PASS without network access.

- [ ] **Step 4: Verify and connect deterministic business-history signals**

Add direct tests for `compute_persistence_counts()`, `compute_escalated_min_shares()` and `compute_tradeoff_warnings()` using ordered completed rounds. Add a regression test that passes two consecutive `high_cost_ratio` outcome rounds to `run_allocation_simulation(..., business_history=history)` and asserts A·B scenarios give `equipment_interior` at least `0.15`. Spy on `generate_scenario_explanation()` and assert a recorded trade-off warning is passed unchanged.

Extend `run_allocation_simulation()` with the optional `business_history` argument. When supplied, derive `min_shares` and `tradeoff_warnings` from the existing `business_history.py` functions before generating scenarios. Existing callers without history and explicit internal callers that already supply signals must preserve their behavior.

Do not activate `compute_personal_baselines()` in this function. It requires a diagnosis pass, while this entry point intentionally receives the saved completed diagnosis as its source of truth.

Run: `cd backend && .venv/bin/pytest tests/ai -q`

Expected: all AI tests PASS without a live LLM or network call.

- [ ] **Step 5: Commit the AI comparison and history change**

```bash
git add ai/bottleneck_detector.py ai/outcome_tracker.py ai/run_simulation.py backend/tests/ai/test_outcome_tracker.py backend/tests/ai/test_business_history.py backend/tests/ai/test_run_allocation_simulation.py
git commit -m "feat: 결과 비교와 선순환 이력 입력 지원"
```

---

### Task 3: In-process outcome engine adapter

**Files:**
- Create: `backend/app/services/outcome_engine.py`
- Create: `backend/tests/services/test_outcome_engine.py`

**Interfaces:**
- Produces: immutable `OutcomeEngineRequest` and `FinancialProjectionRequest`.
- Produces: `OutcomeEngine.generate_mock(monthly_revenue: int) -> dict[str, Any]`.
- Produces: `OutcomeEngine.compare(request: OutcomeEngineRequest) -> dict[str, Any]`.
- Produces: `OutcomeEngine.project_financial(request: FinancialProjectionRequest) -> dict[str, Any]`.
- Produces: `OutcomeCalculationError` and `get_outcome_engine()`.

- [ ] **Step 1: Write failing adapter tests**

```python
# 기존 AI 결과 추적 함수를 호출하는 같은 프로세스 어댑터 테스트
from decimal import Decimal

from app.domain.enums import RepaymentType
from app.services.outcome_engine import InProcessOutcomeEngine, OutcomeEngineRequest


def test_engine_passes_actual_execution_and_loan_conditions() -> None:
    captured = {}

    def fake_compare(**kwargs):
        captured.update(kwargs)
        return {
            "resolved_bottlenecks": [],
            "persisted_bottlenecks": [],
            "new_bottlenecks": [],
            "not_comparable_bottlenecks": [],
            "post_execution_findings": [],
            "post_execution_financial_result": {},
            "breakeven_status": {"status": "비교 불가", "reason": "근거 없음"},
            "next_round_pos_data_snapshot": {},
        }

    engine = InProcessOutcomeEngine(
        compare_loader=lambda: fake_compare,
        mock_loader=lambda: lambda **kwargs: {"monthly_revenue": kwargs["monthly_revenue"]},
        benchmark_loader=lambda: lambda: ({"11_14": 0.3}, 326),
        financial_loader=lambda: lambda **kwargs: {
            "monthly_loan_payment": 446_205,
            "additional_fixed_cost_per_month": 100_000,
            "remaining_cash_after_payment": 203_795,
            "break_even_additional_revenue": 0,
        },
    )
    request = OutcomeEngineRequest(
        pre_findings=({"bottleneck_type": "high_cost_ratio"},),
        post_pos_data={"monthly_revenue": 8_100_000},
        comparable_bottleneck_types=frozenset({"high_cost_ratio"}),
        allocation={"custom_1": 0.9},
        loan_amount=15_000_000,
        annual_interest_rate=Decimal("0.045"),
        term_months=36,
        grace_months=0,
        repayment_type=RepaymentType.EQUAL_PAYMENT,
        break_even_additional_revenue_target=500_000,
    )
    engine.compare(request)
    assert captured["selected_allocation"] == {"custom_1": 0.9}
    assert captured["loan_term_months"] == 36
```

Add a second test that calls `project_financial()` with `FinancialProjectionRequest` and asserts the loader receives the same allocation, observed revenue, interest rate, term, grace period and repayment type.

Run: `cd backend && .venv/bin/pytest tests/services/test_outcome_engine.py -q`

Expected: FAIL because the adapter module does not exist.

- [ ] **Step 2: Implement the protocol, lazy loaders and safe shape check**

Create the two requests with these exact fields and implement loaders using the same repository-root `ai` path pattern as `simulation_engine.py`.

```python
from collections.abc import Sequence


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
```

`generate_mock()` must call `generate_mock_pos_data(scenario="normal", monthly_revenue=monthly_revenue)`. `compare()` passes an empty `pre_pos_data` because the current AI function classifies previous state from `pre_findings` and does not read that argument.

`OutcomeEngineRequest.comparable_bottleneck_types` has type `frozenset[str] | None`; `None` means every AI 병목 유형을 비교한다. The required comparison keys are fixed.

```python
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
```

Add a financial loader for `calculate_financial_projection()` and implement `project_financial()` by passing allocation, loan amount, observed monthly revenue and all loan conditions unchanged. Wrap `ImportError`, `RuntimeError`, `ValueError`, malformed result types and missing keys as `OutcomeCalculationError("결과 검증 계산에 실패했습니다.")`. Do not expose the caught exception text.

Run: `cd backend && .venv/bin/pytest tests/services/test_outcome_engine.py -q`

Expected: PASS.

- [ ] **Step 3: Commit the adapter**

```bash
git add backend/app/services/outcome_engine.py backend/tests/services/test_outcome_engine.py
git commit -m "feat: 결과 검증 AI 어댑터 추가"
```

---

### Task 4: Verification targets and actual execution

**Files:**
- Create: `backend/app/services/verification.py`
- Create: `backend/tests/services/test_verification_service.py`

**Interfaces:**
- Produces: `require_owned_business(database, business_id, session_cookie) -> Business`.
- Produces: `require_owned_simulation(database, simulation_id, session_cookie, with_for_update=False) -> Simulation`.
- Produces: `ExecutionCreationCommand` and `ExecutionCreated`.
- Produces: `VerificationService.list_targets(business_id, include_completed, session_cookie, today=None)`.
- Produces: `VerificationService.create_execution(command, session_cookie, now=None)`.

- [ ] **Step 1: Write failing target and execution tests**

Cover these exact cases in a fake database fixture with completed simulations created 89 and 90 days ago.

```python
def test_targets_start_on_day_90_and_keep_execution_only_cycle(service) -> None:
    targets = service.list_targets(
        business_id=7,
        include_completed=False,
        session_cookie=SESSION_COOKIE,
        today=date(2026, 7, 31),
    )
    assert [target.simulation_id for target in targets.targets] == [45, 46]
    assert targets.targets[1].execution_registered is True


def test_custom_execution_locks_selection_and_preserves_free_names(service) -> None:
    created = service.create_execution(
        ExecutionCreationCommand(
            simulation_id=45,
            mode=ExecutionType.CUSTOM,
            executed_at=date(2026, 7, 30),
            items=(ExecutionItemCommand("저녁 광고", 14_500_000),),
            unused_amount=500_000,
        ),
        SESSION_COOKIE,
        now=datetime(2026, 7, 31, tzinfo=UTC),
    )
    assert created.total_executed_amount == 14_500_000
    assert service.database.selection.locked is True
    assert service.database.execution.allocations[0].category is None
```

Also assert 89 days, no selection, wrong session, future `executedAt`, amount mismatch and duplicate execution produce the specified `404` or `409`/`400` errors.

Run: `cd backend && .venv/bin/pytest tests/services/test_verification_service.py -q`

Expected: FAIL because the service module does not exist.

- [ ] **Step 2: Implement active-session ownership helpers**

Parse the cookie as UUID and verify the linked `DemoSession` is `ACTIVE` with `expires_at > datetime.now(UTC)`. All missing, invalid, expired and cross-session cases raise the same public error.

```python
raise ApiError(404, "RESOURCE_NOT_FOUND", "요청한 자원을 찾을 수 없습니다.")
```

Keep the helpers in `verification.py`; the later three services import them instead of copying session logic.

- [ ] **Step 3: Implement the target projection**

Select completed simulations for the owned business with selection and scenarios eagerly loaded. Query `Execution.simulation_id` and `OutcomeComparison.simulation_id` separately for those simulation IDs because the current `Simulation` model has no back-reference relationships. Compute `days_elapsed = (today - simulation.created_at.astimezone(UTC).date()).days`, require `>= 90`, and exclude only rows with an outcome comparison when `include_completed` is false. Sort by `created_at`, then `id`.

Return plan summaries in A·B·C order and set `execution_registered = execution is not None` independently of completion filtering.

- [ ] **Step 4: Implement locked, atomic execution creation**

Inside one `database.begin()` block, reload the simulation and selection with `with_for_update=True`, recheck 90 days and duplicate execution, then choose one of two item paths.

```python
SCENARIO_MODE = {
    ExecutionType.SAME_AS_A: ScenarioCode.A,
    ExecutionType.SAME_AS_B: ScenarioCode.B,
    ExecutionType.SAME_AS_C: ScenarioCode.C,
}
```

For a SAME_AS mode, reject request items, require `unused_amount == 0`, and copy scenario allocations with a deterministic Korean display name. For MIXED or CUSTOM, require at least one non-blank name, require each amount `> 0`, set `category=None`, and preserve the stripped name. Validate `total_amount + unused_amount == loan_amount`, add the execution and allocations, then call `selection.lock()` before flush.

Run: `cd backend && .venv/bin/pytest tests/services/test_verification_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the verification service**

```bash
git add backend/app/services/verification.py backend/tests/services/test_verification_service.py
git commit -m "feat: 검증 대상과 실제 집행 서비스 추가"
```

---

### Task 5: Outcome data ingestion

**Files:**
- Create: `backend/app/services/outcome_data.py`
- Create: `backend/tests/services/test_outcome_data_service.py`

**Interfaces:**
- Consumes: `OutcomeEngine.generate_mock()`.
- Consumes: `analyze_workbook()` and `normalize_rows()` from `dataset_import.py`.
- Produces: `OutcomeDataCreationCommand`, `ManualOutcomeMetrics`, `OutcomeDataCreated`.
- Produces: `OutcomeDataService.create(command, session_cookie, observed_on=None)`.

- [ ] **Step 1: Write failing tests for all three source types**

Use an execution-ready simulation fixture and assert the stored source semantics.

```python
def test_manual_input_stores_original_metrics_without_ratio_aliasing(service) -> None:
    created = service.create(manual_command(), SESSION_COOKIE, observed_on=date(2026, 7, 31))
    stored = service.database.outcome_data
    assert created.status == "READY"
    assert stored.online_order_ratio == Decimal("0.31")
    assert stored.observed_business_snapshot.online_sales_ratio is None
    assert stored.observed_business_snapshot.monthly_expense_amount == 25_800_000


def test_file_upload_is_mapping_ready_and_persists_normalized_rows(service) -> None:
    created = service.create(file_command(), SESSION_COOKIE, observed_on=date(2026, 7, 31))
    assert created.status == "MAPPING_READY"
    assert len(service.database.dataset.sales) == 1
    assert len(service.database.dataset.expenses) == 1


def test_mock_input_keeps_raw_pos_payload(service) -> None:
    created = service.create(mock_command(), SESSION_COOKIE, observed_on=date(2026, 7, 31))
    assert created.status == "READY"
    assert service.database.outcome_data.raw_pos_data["monthly_revenue"] == 7_500_000
```

Add rejection tests for no execution, duplicate data, damaged xlsx, missing required columns, invalid manual ratios and negative monthly sales. Assert parser failures add no `OutcomeData`, `Dataset` or snapshot.

Run: `cd backend && .venv/bin/pytest tests/services/test_outcome_data_service.py -q`

Expected: FAIL because the service module does not exist.

- [ ] **Step 2: Parse or generate data before the save transaction**

For FILE_UPLOAD, call `analyze_workbook()` for SALE and EXPENSE and reject `missing_columns` with `ApiError(400, "OUTCOME_FILE_MAPPING_FAILED", "업로드 파일의 필수 컬럼을 자동 매핑할 수 없습니다.")`. For MOCK, call the engine with the simulation baseline monthly revenue and keep the returned dictionary immutable by copying it. MANUAL_INPUT needs no engine call.

Do not create database objects before these operations succeed.

- [ ] **Step 3: Build source-specific snapshots**

Use these deterministic mappings.

```python
monthly_expense = metrics.monthly_sales_amount - metrics.operating_profit_amount
```

Reject a negative derived expense. For manual input, copy `contribution_margin_rate` and `employee_count` from the simulation baseline snapshot, set `online_sales_ratio=None`, and preserve all four manual values only on `OutcomeData`.

For FILE_UPLOAD, flush the new dataset and two `DatasetFile` rows, normalize rows with their real IDs, then call `collect_analysis_input(business, dataset)` to build the snapshot. For MOCK, derive monthly expense from `monthly_cogs + monthly_labor_cost`, derive contribution margin from monthly cogs, and store the complete POS dictionary in `raw_pos_data`.

- [ ] **Step 4: Save the complete graph atomically**

In a short transaction, lock the simulation, recheck ownership, execution and duplicate data, then save `Dataset(status=READY)`, any files and rows, `BusinessSnapshot`, and `OutcomeData`. Use `OutcomeDataStatus.READY` for MOCK·MANUAL_INPUT and `MAPPING_READY` for FILE_UPLOAD.

Map an unexpected integrity conflict to `409 OUTCOME_DATA_ALREADY_EXISTS`; rollback every graph node on other failures.

Run: `cd backend && .venv/bin/pytest tests/services/test_outcome_data_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit outcome data ingestion**

```bash
git add backend/app/services/outcome_data.py backend/tests/services/test_outcome_data_service.py
git commit -m "feat: 사후 성과 데이터 입력 서비스 추가"
```

---

### Task 6: Outcome comparison creation and stored result query

**Files:**
- Create: `backend/app/services/outcome.py`
- Create: `backend/tests/services/test_outcome_service.py`

**Interfaces:**
- Consumes: `OutcomeEngine.compare(OutcomeEngineRequest)`.
- Consumes: `OutcomeEngine.project_financial(FinancialProjectionRequest)`.
- Produces: `OutcomeCreationCommand`, `OutcomeCreated`, `OutcomeResult`.
- Produces: `classify_metric(target, break_even, observed) -> OutcomeMetricStatus`.
- Produces: `OutcomeService.create(command, session_cookie)` and `get_result(simulation_id, session_cookie)`.

- [ ] **Step 1: Write failing pure metric classification tests**

```python
# 실제 지표와 관측 가능한 병목만 결과 비교로 저장하는 서비스 테스트
from decimal import Decimal

from app.domain.enums import OutcomeMetricStatus
from app.services.outcome import classify_metric


def test_metric_uses_target_and_break_even_ranges() -> None:
    assert classify_metric(Decimal("120"), Decimal("100"), Decimal("125")) is OutcomeMetricStatus.ABOVE_EXPECTED
    assert classify_metric(Decimal("120"), Decimal("100"), Decimal("110")) is OutcomeMetricStatus.WITHIN_RANGE
    assert classify_metric(Decimal("120"), Decimal("100"), Decimal("90")) is OutcomeMetricStatus.BELOW_EXPECTED
    assert classify_metric(None, Decimal("100"), Decimal("90")) is OutcomeMetricStatus.NOT_COMPARABLE
```

Run: `cd backend && .venv/bin/pytest tests/services/test_outcome_service.py -q`

Expected: FAIL because the service module does not exist.

- [ ] **Step 2: Write failing preparation and mode tests**

Add service tests that assert wrong simulation IDs are `404`, a `FAILED` outcome data row is `409`, both `READY` and `MAPPING_READY` are accepted, duplicate outcome is `409`, and manual input calls `project_financial()` but never calls `compare()`. Add FILE_UPLOAD fixtures with complete transaction times and with missing times; only the complete fixture may include `time_of_day_weakness` in `comparable_bottleneck_types`.

The actual allocation transformation must use fixed categories when present and collision-proof keys for free items.

```python
allocation_key = allocation.category.value if allocation.category else f"custom_{allocation.id}"
allocation_ratio = Decimal(allocation.amount) / Decimal(simulation.loan_amount)
```

- [ ] **Step 3: Prepare AI inputs outside a transaction**

For MOCK, use `OutcomeData.raw_pos_data` and set `comparable_bottleneck_types=None` so the existing AI path compares every type. For FILE_UPLOAD, call `collect_analysis_input()` and construct only the keys required by the comparable set. Include `time_of_day_weakness` only when timed sales coverage is exactly `1`; always include cost and labor types because the expense file requires categorized rows; do not include repeat, seat or online types.

Use the simulation diagnosis bottleneck types as `pre_findings`. Pass the actual execution ratios and all stored loan conditions to `OutcomeEngineRequest`. MANUAL_INPUT bypasses `compare()` but calls `project_financial()` with the actual execution and provided monthly sales; it produces an empty resolved·remaining·new set plus all prior bottlenecks as not comparable.

- [ ] **Step 4: Build four metric rows with explicit boundaries**

Create exactly `MONTHLY_SALES`, `OPERATING_PROFIT`, `ONLINE_ORDER_RATIO`, `CASH_AFTER_REPAYMENT` rows. Use these boundaries from the approved design.

```python
sales_target = baseline_sales + financial["break_even_additional_revenue"]
sales_break_even = baseline_sales
profit_target = financial["monthly_loan_payment"] + financial["additional_fixed_cost_per_month"]
profit_break_even = 0
online_target = max(value for value in (baseline_online_ratio, Decimal("0.20")) if value is not None)
online_break_even = min(value for value in (baseline_online_ratio, Decimal("0.20")) if value is not None)
cash_target = max(0, financial["remaining_cash_after_payment"])
cash_break_even = min(0, financial["remaining_cash_after_payment"])
```

For MANUAL_INPUT, read all four observed values directly from `OutcomeData`. For FILE_UPLOAD, use snapshot sales, `sales - expense` operating profit, no online order ratio, and `operating profit - monthly loan payment - additional fixed cost` as calculated cash after repayment. For MOCK, use raw monthly revenue, `revenue - monthly_cogs - monthly_labor_cost`, online order count divided by estimated total monthly customers when present, and the same calculated cash formula.

When an observed or boundary value is unavailable, store `NOT_COMPARABLE` and `None` rather than zero. Derive the overall `OutcomeStatus` from the engine breakeven status for AI modes; for manual mode use the four metric statuses, mapping all above to `MET`, any below to `NOT_MET`, a mix without below to `PARTIALLY_MET`, and all non-comparable to `NOT_COMPARABLE`.

- [ ] **Step 5: Persist result and bottleneck changes atomically**

After calculation, begin a short transaction and lock simulation, execution and outcome data. Recheck ownership, readiness and duplicates. Save one `OutcomeComparison`, four metrics, one `ReassessmentSnapshot`, changes, and `next_round_pos_data_snapshot` with these mappings.

```python
CHANGE_TYPE_BY_KEY = {
    "resolved_bottlenecks": BottleneckChangeType.RESOLVED,
    "persisted_bottlenecks": BottleneckChangeType.REMAINING,
    "new_bottlenecks": BottleneckChangeType.NEW,
    "not_comparable_bottlenecks": BottleneckChangeType.NOT_COMPARABLE,
}
```

Link prior bottleneck IDs for resolved, remaining and not comparable rows. New rows keep both foreign keys null and store the generated finding detail. Map `OutcomeCalculationError` to `502 OUTCOME_CALCULATION_FAILED` and store no comparison graph.

For MOCK and FILE_UPLOAD, validate and persist the engine's `next_round_pos_data_snapshot`. For MANUAL_INPUT, persist only the provided observable values using stable POS keys such as `monthly_revenue`; do not synthesize costs, customer counts or repeat rates. A comparison and its snapshot must commit or roll back together.

- [ ] **Step 6: Project the stored GET response without recalculation**

`get_result()` loads comparison, metrics, baseline and observed snapshots and bottleneck changes. Return ordered trends, comparison rows, the four reevaluation entries and only `NEW` changes in `new_bottlenecks`. Add a spy test that records the engine call count before GET and asserts it does not change.

Run: `cd backend && .venv/bin/pytest tests/services/test_outcome_service.py -q`

Expected: PASS.

- [ ] **Step 7: Commit outcome comparison**

```bash
git add backend/app/services/outcome.py backend/tests/services/test_outcome_service.py
git commit -m "feat: 결과 비교 생성과 조회 서비스 추가"
```

---

### Task 7: Feed completed outcome history into the next simulation

**Files:**
- Modify: `backend/app/services/simulation_engine.py`
- Modify: `backend/app/services/simulation.py`
- Modify: `backend/tests/services/test_simulation_engine.py`
- Modify: `backend/tests/services/test_simulation_service.py`

**Interfaces:**
- Adds: `SimulationEngineRequest.business_history: tuple[dict[str, Any], ...]`.
- Adds: `to_ai_bottleneck_type(stored_type: str) -> str` with an explicit backend-to-AI mapping.
- Adds: `_load_business_history(business_id: int) -> tuple[dict[str, Any], ...]` ordered by completed outcome cycle.

- [ ] **Step 1: Write failing AI-contract and engine tests**

Add a test with a production diagnosis code such as `HIGH_MATERIAL_COST` and assert the engine receives `high_cost_ratio`, not the backend storage code. Extend the fake simulation runner to capture `business_history` and assert the adapter passes it as a keyword argument while an empty tuple preserves first-round behavior.

Use this exact mapping.

```python
AI_BOTTLENECK_TYPE_BY_STORED_TYPE = {
    "HIGH_MATERIAL_COST": "high_cost_ratio",
    "HIGH_LABOR_COST": "high_labor_ratio",
    "CHANNEL_CONCENTRATION": "low_online_sales_share",
    "HIGH_PLATFORM_COST": "high_platform_cost_rate",
    "HIGH_ONLINE_REFUND_RATE": "high_online_cancel_refund_rate",
    "LOW_NET_SETTLEMENT_RATE": "low_net_settlement_rate",
    "TIME_OF_DAY_WEAKNESS": "time_of_day_weakness",
}
```

Unknown and already-normalized codes must pass through unchanged so saved audit data is not lost.

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_engine.py tests/services/test_simulation_service.py -q`

Expected: FAIL because the request has no history and production codes are not normalized.

- [ ] **Step 2: Write failing completed-cycle projection tests**

Seed two completed outcome comparisons for the same business and one for another business. Each owned cycle must have an execution, allocations, result changes and `next_round_pos_data_snapshot`. Assert the captured engine request contains only the owned cycles in result creation order.

Each history record must have this shape.

```python
{
    "round": 1,
    "findings": [{"bottleneck_type": "high_cost_ratio"}],
    "pos_data": {"monthly_revenue": 8_100_000},
    "selected_allocation": {"equipment_interior": 0.60},
}
```

Include only `REMAINING` and `NEW` changes in findings. Compute allocation ratios against the simulation loan amount. Aggregate fixed categories, skip `category=None`, and do not renormalize after skipping free items or unused principal. This preserves the true share of borrowed funds and avoids inventing a category.

- [ ] **Step 3: Implement the history projection and transaction boundary**

During `_prepare()`, load completed comparisons for the owned business with execution allocations, reassessment changes and stored POS snapshots eagerly available. Sort by comparison creation time and ID, then build immutable plain dictionaries before closing the read transaction. Normalize bottleneck codes at the boundary for the current saved diagnosis and history findings.

Add `business_history` to `SimulationEngineRequest` and pass it to `run_allocation_simulation(..., business_history=[...])`. Keep AI/LLM execution outside the database transaction. Do not call `run_simulation()` and do not rerun diagnosis, because the command's completed `Diagnosis` remains the current source of truth.

Run: `cd backend && .venv/bin/pytest tests/ai tests/services/test_simulation_engine.py tests/services/test_simulation_service.py -q`

Expected: PASS with no live LLM or network call.

- [ ] **Step 4: Commit the simulation feedback loop**

```bash
git add backend/app/services/simulation_engine.py backend/app/services/simulation.py backend/tests/services/test_simulation_engine.py backend/tests/services/test_simulation_service.py
git commit -m "feat: 결과 이력을 다음 시뮬레이션에 연결"
```

---

### Task 8: Stored-cycle dashboard and repayment estimate

**Files:**
- Create: `backend/app/services/dashboard.py`
- Create: `backend/tests/services/test_dashboard_service.py`

**Interfaces:**
- Produces: `estimate_loan_status(simulation, execution, as_of) -> LoanStatusResult`.
- Produces: `DashboardService.get(business_id, session_cookie, as_of=None) -> DashboardResult`.

- [ ] **Step 1: Write failing repayment estimate tests**

Test equal payment, equal principal, bullet, grace period and term cap with fixed dates.

```python
# 저장된 검증 사이클과 추정 상환 현황을 투영하는 대시보드 테스트
def test_dashboard_labels_scheduled_repayment_as_estimated(service) -> None:
    result = service.get(7, SESSION_COOKIE, as_of=date(2026, 10, 30))
    assert result.loan_status.repayment_data_type == "ESTIMATED"
    assert result.loan_status.progress_rate == Decimal("0.0833")
    assert result.loan_status.estimated_remaining_principal < result.loan_status.loan_amount


def test_bullet_loan_keeps_principal_until_maturity() -> None:
    result = estimate_loan_status(bullet_simulation(), execution_on(date(2026, 7, 30)), date(2026, 10, 30))
    assert result.estimated_remaining_principal == 15_000_000
    assert result.paid_amount == result.monthly_repayment_amount * 3
```

Run: `cd backend && .venv/bin/pytest tests/services/test_dashboard_service.py -q`

Expected: FAIL because the service module does not exist.

- [ ] **Step 2: Implement deterministic schedule estimation**

Count only complete calendar months from `executed_at.date()` and cap at `term_months`. During grace, add monthly interest to `paid_amount` without reducing principal. After grace, calculate principal balance by the stored repayment type; at maturity force remaining principal to zero. `progress_rate` is elapsed months divided by term, quantized to four decimals.

For equal payment, use the standard remaining-balance formula with the payment calculated for `term_months - grace_months`. For equal principal, subtract the fixed principal portion for each amortizing month. For bullet, retain full principal until the final month and include principal in `paid_amount` at maturity. `monthly_repayment_amount` is the representative post-grace amount already stored on the selected scenario when available, otherwise calculate it from loan conditions.

- [ ] **Step 3: Project only stored cycle data**

Load owned business simulations with selection and scenarios, then query executions, outcome data and comparisons separately keyed by simulation ID. Load metrics and changes through their existing relationships. Sort cycles by simulation creation time. Build metric trends from stored baseline and observed values, cycle histories from selection·execution·overall result, unresolved bottlenecks from `REMAINING`, `NEW`, `NOT_COMPARABLE`, and next initial conditions from the most recent `OutcomeComparison.next_round_pos_data_snapshot`. Fall back to observed snapshot and manual fields only for legacy comparisons without the JSONB value.

When no execution exists, return `loan_status=None`. When no outcomes exist, return empty trend·cycle·bottleneck lists and `next_initial_conditions=None`. Do not inject `OutcomeEngine` into this service.

Run: `cd backend && .venv/bin/pytest tests/services/test_dashboard_service.py -q`

Expected: PASS.

- [ ] **Step 4: Commit the dashboard**

```bash
git add backend/app/services/dashboard.py backend/tests/services/test_dashboard_service.py
git commit -m "feat: 선순환 대시보드 서비스 추가"
```

---

### Task 9: Six HTTP APIs and dual Content-Type contract

**Files:**
- Create: `backend/app/api/routes/verifications.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/api/test_verifications.py`

**Interfaces:**
- Consumes: the four services and `get_outcome_engine()`.
- Produces: six exact Notion paths and camelCase response models.
- Produces: JSON and multipart OpenAPI request bodies for outcome data.

- [ ] **Step 1: Write failing API contract tests**

Use dependency overrides for each service and assert the exact request conversions and response status codes.

```python
# 결과 검증과 선순환 대시보드 여섯 API의 HTTP 계약 테스트
def test_create_custom_execution_returns_camel_case(api_client) -> None:
    response = api_client.post(
        "/api/simulations/45/executions",
        json={
            "executionMode": "CUSTOM",
            "executedAt": "2026-07-30",
            "items": [{"name": "저녁 광고", "amount": 14_500_000}],
            "unusedAmount": 500_000,
        },
    )
    assert response.status_code == 201
    assert response.json() == {
        "executionId": 81,
        "simulationId": 45,
        "executionMode": "CUSTOM",
        "totalExecutedAmount": 14_500_000,
        "savedAt": "2026-07-31T12:00:00Z",
    }


def test_outcome_data_accepts_json_and_multipart(api_client, sales_xlsx, expense_xlsx) -> None:
    manual = api_client.post(
        "/api/simulations/45/outcome-data",
        json={
            "sourceType": "MANUAL_INPUT",
            "metrics": {
                "monthlySalesAmount": 32_000_000,
                "operatingProfitAmount": 6_200_000,
                "onlineOrderRatio": 0.31,
                "cashAfterRepaymentAmount": 2_800_000,
            },
        },
    )
    assert manual.status_code == 201
```

Add separate tests for verification targets, MOCK JSON, FILE_UPLOAD multipart, outcome create, outcome GET, dashboard GET, unsupported content type `400`, Pydantic `422`, and representative `404`, `409`, `502` structured errors.

Run: `cd backend && .venv/bin/pytest tests/api/test_verifications.py -q`

Expected: FAIL with route not found.

- [ ] **Step 2: Define API enums and Pydantic models**

Create request enums with uppercase values and map them by member name to domain enums.

```python
class ExecutionModeRequest(StrEnum):
    SAME_AS_A = "SAME_AS_A"
    SAME_AS_B = "SAME_AS_B"
    SAME_AS_C = "SAME_AS_C"
    MIXED = "MIXED"
    CUSTOM = "CUSTOM"


class OutcomeSourceRequest(StrEnum):
    MOCK = "MOCK"
    FILE_UPLOAD = "FILE_UPLOAD"
    MANUAL_INPUT = "MANUAL_INPUT"
```

All models inherit `ConfigDict(from_attributes=True, populate_by_name=True)`. Limit names and filenames to their storage widths, use signed 64-bit limits for money, and validate `onlineOrderRatio` in `[0, 1]`.

Define response models matching every field in the design: verification targets, execution created, outcome data created, outcome created summary, stored trends·comparison·reevaluation·new bottlenecks, and dashboard business·loan·metric·cycle·bottleneck·next-condition sections.

- [ ] **Step 3: Implement explicit Content-Type dispatch**

The outcome-data route accepts `Request` so one path can parse both forms. Use prefix checks because multipart includes a boundary.

```python
content_type = request.headers.get("content-type", "").lower()
if content_type.startswith("application/json"):
    payload = OutcomeDataJsonRequest.model_validate(await request.json())
    command = to_json_outcome_command(simulation_id, payload)
elif content_type.startswith("multipart/form-data"):
    form = await request.form()
    payload = OutcomeDataFileRequest.model_validate(
        {
            "sourceType": form.get("sourceType"),
            "salesFile": form.get("salesFile"),
            "costFile": form.get("costFile"),
        }
    )
    command = await to_file_outcome_command(simulation_id, payload)
else:
    raise ApiError(400, "UNSUPPORTED_CONTENT_TYPE", "지원하지 않는 Content-Type입니다.")
```

Convert `pydantic.ValidationError` to `RequestValidationError` so the existing global `422 VALIDATION_ERROR` response remains consistent. Validate filename `.xlsx` before reading bytes.

Add an explicit `openapi_extra.requestBody.content` entry with both `application/json` and `multipart/form-data`; the multipart schema requires `sourceType`, `salesFile`, `costFile` and marks both files as `string/binary`.

- [ ] **Step 4: Wire the six routes and dependencies**

Use these exact paths and status codes.

```text
GET  /api/businesses/{businessId}/verification-targets  -> 200
POST /api/simulations/{simulationId}/executions         -> 201
POST /api/simulations/{simulationId}/outcome-data       -> 201
POST /api/simulations/{simulationId}/outcomes           -> 201
GET  /api/simulations/{simulationId}/outcomes           -> 200
GET  /api/businesses/{businessId}/dashboard             -> 200
```

Inject the database session into all services, `OutcomeEngine` only into outcome-data and outcome services, and pass `demo_session_id` unchanged. Register `verifications_router` after `simulations_router` in `main.py`.

Run: `cd backend && .venv/bin/pytest tests/api/test_verifications.py -q`

Expected: PASS.

- [ ] **Step 5: Verify OpenAPI and commit**

Run:

```bash
cd backend
.venv/bin/python -c "from app.main import app; schema=app.openapi(); paths=schema['paths']; assert all(path in paths for path in ['/api/businesses/{business_id}/verification-targets','/api/simulations/{simulation_id}/executions','/api/simulations/{simulation_id}/outcome-data','/api/simulations/{simulation_id}/outcomes','/api/businesses/{business_id}/dashboard']); content=paths['/api/simulations/{simulation_id}/outcome-data']['post']['requestBody']['content']; assert {'application/json','multipart/form-data'} <= set(content)"
.venv/bin/ruff check app/api/routes/verifications.py app/main.py tests/api/test_verifications.py
.venv/bin/ruff format --check app/api/routes/verifications.py app/main.py tests/api/test_verifications.py
```

Expected: all commands exit `0`.

Commit:

```bash
git add backend/app/api/routes/verifications.py backend/app/main.py backend/tests/api/test_verifications.py
git commit -m "feat: 결과 검증과 대시보드 API 추가"
```

---

### Task 10: PostgreSQL integration and final verification

**Files:**
- Create: `backend/tests/integration/test_verification_api.py`
- Modify: `checklist.md`
- Modify: `context-notes.md`

**Interfaces:**
- Verifies: full manual and Mock graph on PostgreSQL.
- Verifies: row locks·unique constraints·rollback and Alembic head.
- Verifies: no live AI, LLM or external API calls.

- [ ] **Step 1: Write the PostgreSQL full-cycle test**

Seed an active session, business, dataset, snapshot, completed diagnosis, a completed simulation created 90 days ago, A·B·C scenarios and a selection. Exercise the public API in this order.

```python
execution = client.post(
    f"/api/simulations/{simulation_id}/executions",
    json={
        "executionMode": "CUSTOM",
        "executedAt": "2026-07-30",
        "items": [{"name": "저녁 광고", "amount": 14_500_000}],
        "unusedAmount": 500_000,
    },
)
outcome_data = client.post(
    f"/api/simulations/{simulation_id}/outcome-data",
    json={
        "sourceType": "MANUAL_INPUT",
        "metrics": {
            "monthlySalesAmount": 32_000_000,
            "operatingProfitAmount": 6_200_000,
            "onlineOrderRatio": 0.31,
            "cashAfterRepaymentAmount": 2_800_000,
        },
    },
)
outcome = client.post(
    f"/api/simulations/{simulation_id}/outcomes",
    json={
        "executionId": execution.json()["executionId"],
        "outcomeDataId": outcome_data.json()["outcomeDataId"],
    },
)
assert execution.status_code == 201
assert outcome_data.status_code == 201
assert outcome.status_code == 201
```

Assert one execution, its free allocation, one outcome data row, four metrics, one reassessment and prior bottlenecks marked not comparable. Assert result GET and dashboard GET return the same stored statuses and `repaymentDataType=ESTIMATED`.

Add a second completed cycle with categorized actual allocations and active post-outcome bottlenecks, then create a later simulation through a fake engine. Assert the engine receives ordered `business_history`, only the current session's business cycles, stored next-round POS snapshots, normalized AI bottleneck codes and actual category ratios. This integration assertion proves the result API closes the loop instead of only displaying history.

- [ ] **Step 2: Add duplicate, isolation and rollback integration cases**

Send each POST twice and assert the second response is `409` with table counts unchanged. Use a second session cookie and assert all six paths hide the first session's resources with `404`.

Attach a SQLAlchemy `before_insert` listener to `OutcomeComparisonMetric`, raise an intentional `RuntimeError`, and assert `OutcomeComparison`, metrics, reassessment and changes all remain at zero after the `500` response. Remove the listener in `finally`.

- [ ] **Step 3: Run isolated PostgreSQL verification**

```bash
cd backend
ALLOW_DESTRUCTIVE_TEST_DATABASE_RESET=1 TEST_DATABASE_URL=postgresql+psycopg://keemhoeyune@127.0.0.1:55432/kb_domain_test .venv/bin/pytest tests/integration/test_alembic_migration.py tests/integration/test_verification_api.py -q
```

Expected: all migration and verification integration tests PASS. If PostgreSQL is unavailable, record the exact connection error and keep the tests skipped in the no-environment run; never point the destructive fixture at Supabase or a database not ending in `_test`.

- [ ] **Step 4: Run focused and full regression checks**

```bash
cd backend
.venv/bin/pytest tests/domain/test_execution.py tests/domain/test_outcome.py tests/ai/test_outcome_tracker.py tests/ai/test_business_history.py tests/ai/test_run_allocation_simulation.py tests/services/test_simulation_engine.py tests/services/test_simulation_service.py tests/services/test_outcome_engine.py tests/services/test_verification_service.py tests/services/test_outcome_data_service.py tests/services/test_outcome_service.py tests/services/test_dashboard_service.py tests/api/test_verifications.py -q
.venv/bin/pytest -q
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
git diff --check
```

Expected: focused and full pytest commands have zero failures, Ruff exits `0`, and `git diff --check` prints nothing. Run the Task 9 OpenAPI assertion again and record the exact pass·skip counts in `context-notes.md`.

- [ ] **Step 5: Review scope and update work records**

Inspect `git diff --stat`, `git diff --name-only` and each changed file. Confirm every changed line traces to issue #36, all new Python files have Korean role comments, `.gitignore` and `docs/project-proposal-plan.md` remain untouched, no public error contains internal exception text, and no test called a live LLM or external API.

Mark all completed issue #36 items in `checklist.md` and append the actual verification commands, results and any remaining environment risk to `context-notes.md`.

- [ ] **Step 6: Commit integration tests and work records**

```bash
git add backend/tests/integration/test_verification_api.py checklist.md context-notes.md
git commit -m "test: 결과 검증 전체 흐름 검증"
```

Expected: the branch contains reversible semantic commits for domain, AI comparison, adapter, each service group, HTTP API and PostgreSQL verification, while the two user-owned worktree changes remain unstaged.
