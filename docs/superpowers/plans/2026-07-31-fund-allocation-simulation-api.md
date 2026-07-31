# Fund Allocation Simulation API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 완료된 진단과 대출 조건으로 A·B·C 자금 배분안을 동기 생성하고 결과 조회·비교·최종 선택 API를 제공한다.

**Architecture:** FastAPI 라우터는 HTTP 계약만 담당하고 `SimulationService`가 소유권·선행 상태·영속화를 조정한다. `SimulationEngine` 인터페이스의 같은 프로세스 구현이 저장 진단을 AI findings로 변환한 결과를 `run_allocation_simulation()`에 전달하며, AI 호출 중에는 데이터베이스 트랜잭션을 열어 두지 않는다.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL, pytest 9, Ruff, 기존 `ai/` Python 엔진.

## Global Constraints

- 생성 API는 동기 처리하고 `201 Created`로 `simulationId`와 `COMPLETED`만 반환한다.
- 결과 상세는 GET API에서만 반환한다.
- 저장된 `COMPLETED` 진단을 배분 근거의 단일 원천으로 사용하며 병목을 다시 진단하지 않는다.
- 외부 필드는 camelCase, 상태·분류 enum은 대문자 문자열을 사용한다.
- 자동 테스트에서 실제 LLM과 외부 API를 호출하지 않는다.
- 다른 익명 데모 세션 소유 자원은 `404`로 숨긴다.
- AI 호출 전 조회 트랜잭션을 끝내고, 성공 결과는 하나의 짧은 트랜잭션으로 저장한다.
- 새 Python 소스 파일의 첫 줄에는 역할을 설명하는 한 줄 한국어 주석을 둔다.
- 사용자 변경인 `.gitignore`와 `docs/project-proposal-plan.md`는 수정하거나 스테이징하지 않는다.

## File Map

- Create `backend/tests/ai/conftest.py` — 백엔드 테스트에서 저장소의 `ai/` 모듈을 불러오는 테스트 경로 설정.
- Create `backend/tests/ai/test_financial_calculator.py` — 상환 방식과 거치 기간 계산 단위 테스트.
- Create `backend/tests/ai/test_run_allocation_simulation.py` — 저장 findings 기반 A·B·C 생성 단위 테스트.
- Modify `ai/financial_calculator.py` — 대표 월 상환액에 상환 방식과 거치 기간 반영.
- Modify `ai/run_simulation.py` — 진단 이후 시나리오 생성 단계를 재사용 가능한 함수로 추출.
- Modify `ai/llm_explainer.py` — 키 누락이 프로세스를 종료하지 않고 일반 예외가 되도록 변경.
- Modify `backend/pyproject.toml`, `backend/uv.lock` — AI 런타임의 직접 의존성 선언.
- Create `backend/app/services/simulation_engine.py` — AI 엔진 인터페이스와 같은 프로세스 어댑터.
- Create `backend/tests/services/test_simulation_engine.py` — 어댑터 입력·출력과 예외 래핑 테스트.
- Create `backend/app/core/errors.py` — 구조화된 API 오류 타입.
- Create `backend/app/services/simulation.py` — 생성·조회·비교·선택 유스케이스.
- Create `backend/tests/services/test_simulation_service.py` — 순수 변환과 서비스 규칙 테스트.
- Create `backend/app/api/routes/simulations.py` — 네 API와 요청·응답 스키마.
- Modify `backend/app/main.py` — 시뮬레이션 라우터와 오류 핸들러 등록.
- Create `backend/tests/api/test_simulations.py` — API 계약과 세션 격리 테스트.
- Create `backend/tests/integration/test_simulation_api.py` — PostgreSQL 저장 그래프와 롤백 검증.
- Modify `checklist.md`, `context-notes.md` — 진행 상태와 검증 결과 기록.

---

### Task 1: AI allocation core and repayment calculations

**Files:**
- Create: `backend/tests/ai/conftest.py`
- Create: `backend/tests/ai/test_financial_calculator.py`
- Create: `backend/tests/ai/test_run_allocation_simulation.py`
- Modify: `ai/financial_calculator.py`
- Modify: `ai/run_simulation.py`
- Modify: `ai/llm_explainer.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`

**Interfaces:**
- Produces: `run_allocation_simulation(findings: list[dict], loan: dict, pos_data: dict) -> dict`.
- Produces: `calculate_financial_projection(allocation: dict, loan_amount: int, baseline_monthly_revenue: int, annual_interest_rate: float = 0.045, loan_term_months: int = 36, avg_daily_customers: int | None = None, grace_months: int = 0, repayment_type: str = "equal_payment") -> dict`.
- Produces: `calc_representative_monthly_payment(amount, rate, term, grace, repayment_type) -> int`.

- [ ] **Step 1: Declare AI runtime dependencies and test import path**

Add direct dependencies to `backend/pyproject.toml`.

```toml
"python-dotenv>=1.2.0,<2.0",
"requests>=2.32.0,<3.0",
```

Create `backend/tests/ai/conftest.py`.

```python
# 백엔드 테스트에서 저장소의 AI 모듈을 불러오도록 경로를 설정하는 테스트 구성
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[3] / "ai"
sys.path.insert(0, str(AI_ROOT))
```

Run: `cd backend && .venv/bin/uv lock`

Expected: `uv.lock` records `requests` as a direct backend dependency without changing unrelated package constraints.

- [ ] **Step 2: Write failing repayment tests**

Create tests that call the exact new helper.

```python
# 세 상환 방식과 거치 기간의 대표 월 상환액을 검증하는 테스트
from financial_calculator import calc_representative_monthly_payment


def test_equal_payment_uses_remaining_term_after_grace() -> None:
    without_grace = calc_representative_monthly_payment(
        12_000_000, 0.06, 36, 0, "equal_payment"
    )
    with_grace = calc_representative_monthly_payment(
        12_000_000, 0.06, 36, 6, "equal_payment"
    )
    assert with_grace > without_grace


def test_equal_principal_uses_first_post_grace_payment() -> None:
    payment = calc_representative_monthly_payment(
        12_000_000, 0.06, 36, 6, "equal_principal"
    )
    assert payment == 460_000


def test_bullet_payment_uses_monthly_interest() -> None:
    payment = calc_representative_monthly_payment(
        12_000_000, 0.06, 36, 0, "bullet_payment"
    )
    assert payment == 60_000
```

Run: `cd backend && .venv/bin/pytest tests/ai/test_financial_calculator.py -q`

Expected: FAIL because `calc_representative_monthly_payment` does not exist.

- [ ] **Step 3: Implement the repayment helper and pass loan fields through**

Implement the exact branch rules.

```python
def calc_representative_monthly_payment(
    loan_amount: int,
    annual_rate: float,
    term_months: int,
    grace_months: int,
    repayment_type: str,
) -> int:
    amortizing_months = term_months - grace_months
    monthly_interest = loan_amount * annual_rate / 12
    if repayment_type == "bullet_payment":
        return round(monthly_interest)
    if repayment_type == "equal_principal":
        return round(loan_amount / amortizing_months + monthly_interest)
    return calc_monthly_loan_payment(loan_amount, annual_rate, amortizing_months)
```

Update `calculate_financial_projection()` to call this helper. Add the bullet maturity warning to `risk_level_basis` so `riskReasons` can expose it.

Run: `cd backend && .venv/bin/pytest tests/ai/test_financial_calculator.py -q`

Expected: PASS.

- [ ] **Step 4: Write a failing stored-findings scenario test**

Create a complete finding and replace only the LLM boundary.

```python
# 저장된 진단 findings로 A·B·C 배분안을 생성하는 AI 코어 테스트
import run_simulation


def test_run_allocation_simulation_uses_supplied_findings(monkeypatch) -> None:
    monkeypatch.setattr(
        run_simulation,
        "generate_scenario_explanation",
        lambda **_: {
            "allocation_rationale": "저장된 병목을 사용한 배분 근거",
            "scb_growth_outlook": "정성적 성장 가능성",
        },
    )
    findings = [
        {
            "bottleneck_type": "high_cost_ratio",
            "title": "원가율 상승",
            "detail": "원가율이 비교 기준보다 높습니다.",
            "comparison_chip": "원가율 비교",
            "evidence_source": "업계 가정치 (실증 데이터 없음)",
            "methodology": "저장 진단 근거",
            "severity": "심각",
            "confidence_badge": "보통",
            "suggested_category": "equipment_interior",
        }
    ]
    result = run_simulation.run_allocation_simulation(
        findings,
        {
            "amount": 15_000_000,
            "annual_interest_rate": 0.045,
            "term_months": 36,
            "grace_months": 0,
            "repayment_type": "equal_payment",
        },
        {"monthly_revenue": 7_500_000, "avg_daily_customers": 90},
    )
    assert [item["scenario_id"] for item in result["scenario_results"]] == ["A", "B", "C"]
    assert result["bottleneck_diagnosis"] == findings
```

Run: `cd backend && .venv/bin/pytest tests/ai/test_run_allocation_simulation.py -q`

Expected: FAIL because `run_allocation_simulation` does not exist.

- [ ] **Step 5: Extract the reusable allocation function**

Move draft generation, financial calculation, SCB mapping, LLM explanation and response assembly from `run_simulation()` into `run_allocation_simulation()`. Keep `run_simulation()` as diagnosis followed by the new function.

Change missing-key handling in `llm_explainer.py`.

```python
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
```

Run: `cd backend && .venv/bin/pytest tests/ai -q`

Expected: all AI tests PASS.

- [ ] **Step 6: Commit the AI core**

Run:

```bash
git add ai/financial_calculator.py ai/run_simulation.py ai/llm_explainer.py backend/pyproject.toml backend/uv.lock backend/tests/ai
git commit -m "feat: 저장 진단 기반 시뮬레이션 계산 지원"
```

Expected: one commit containing only AI calculation, dependencies and their tests.

---

### Task 2: In-process simulation engine adapter

**Files:**
- Create: `backend/app/services/simulation_engine.py`
- Create: `backend/tests/services/test_simulation_engine.py`

**Interfaces:**
- Consumes: `run_allocation_simulation(findings, loan, pos_data) -> dict`.
- Produces: immutable `SimulationEngineRequest`.
- Produces: `SimulationEngine.run(request: SimulationEngineRequest) -> dict[str, Any]`.
- Produces: `get_simulation_engine() -> SimulationEngine`.

- [ ] **Step 1: Write the failing adapter contract test**

```python
# 같은 프로세스 AI 어댑터의 입력 변환과 예외 경계를 검증하는 테스트
from decimal import Decimal

from app.domain.enums import RepaymentType
from app.services.simulation_engine import InProcessSimulationEngine, SimulationEngineRequest


def test_engine_translates_request_to_ai_payload(monkeypatch) -> None:
    captured = {}

    def fake_runner(findings, loan, pos_data):
        captured.update(findings=findings, loan=loan, pos_data=pos_data)
        return {"scenario_results": []}

    engine = InProcessSimulationEngine(loader=lambda: fake_runner)
    request = SimulationEngineRequest(
        findings=({"bottleneck_type": "high_cost_ratio"},),
        loan_amount=15_000_000,
        annual_interest_rate=Decimal("0.045"),
        term_months=36,
        grace_months=0,
        repayment_type=RepaymentType.EQUAL_PAYMENT,
        baseline_monthly_revenue=7_500_000,
        average_daily_customers=90,
    )
    assert engine.run(request) == {"scenario_results": []}
    assert captured["loan"]["repayment_type"] == "equal_payment"
    assert captured["pos_data"]["monthly_revenue"] == 7_500_000
```

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_engine.py -q`

Expected: FAIL because the adapter module does not exist.

- [ ] **Step 2: Implement the protocol, request and lazy loader**

The default loader computes the repository `ai` path from `simulation_engine.py`, inserts it once into `sys.path`, and imports `run_allocation_simulation`. `InProcessSimulationEngine` accepts a loader callable so tests never import or call the live LLM boundary.

Wrap `RuntimeError`, request timeouts, HTTP failures and invalid result shape as `SimulationGenerationError` while preserving no secret-bearing exception text in the public error.

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_engine.py -q`

Expected: PASS.

- [ ] **Step 3: Commit the adapter**

Run:

```bash
git add backend/app/services/simulation_engine.py backend/tests/services/test_simulation_engine.py
git commit -m "feat: 시뮬레이션 AI 어댑터 추가"
```

Expected: one adapter commit with no route or persistence code.

---

### Task 3: Simulation creation service

**Files:**
- Create: `backend/app/core/errors.py`
- Create: `backend/app/services/simulation.py`
- Create: `backend/tests/services/test_simulation_service.py`

**Interfaces:**
- Consumes: `SimulationEngine.run(SimulationEngineRequest)`.
- Produces: `SimulationCreationCommand`.
- Produces: `SimulationCreated(simulation_id: int, status: str)`.
- Produces: `SimulationService(database: Session, engine: SimulationEngine)`.
- Produces: `SimulationService.create(command, session_cookie) -> SimulationCreated`.
- Produces: `ApiError(status_code: int, code: str, message: str)`.

- [ ] **Step 1: Write failing preparation and ownership tests**

Use a focused fake session containing a business, completed diagnosis, ready dataset and business snapshot. Test these exact rules.

```python
def test_create_rejects_diagnosis_owned_by_another_business(service) -> None:
    with pytest.raises(ApiError) as error:
        service.create(valid_command(business_id=2), SESSION_COOKIE)
    assert error.value.status_code == 404


def test_create_rejects_running_diagnosis(service) -> None:
    service.database.diagnosis.status = DiagnosisStatus.RUNNING
    with pytest.raises(ApiError) as error:
        service.create(valid_command(), SESSION_COOKIE)
    assert error.value.code == "DIAGNOSIS_NOT_COMPLETED"
    assert error.value.status_code == 409
```

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_service.py -q`

Expected: FAIL because `SimulationService` does not exist.

- [ ] **Step 2: Implement preparation and finding mapping**

Map stored bottlenecks with exact deterministic conversions.

```python
SEVERITY_MAP = {"mild": "경미", "clear": "뚜렷", "severe": "심각"}
CONFIDENCE_MAP = {
    "public_data": "높음",
    "synthetic_sales": "낮음",
    "synthetic_expense": "낮음",
    "synthetic_online_sales": "높음",
    "benchmark": "높음",
    "domain_assumption": "보통",
}
```

Use `BusinessSnapshot.monthly_net_sales_amount` as `baseline_monthly_revenue`. Derive `average_daily_customers` by rounding `monthly_order_count / 30` when the order count exists and is positive.

End the read transaction before `engine.run()` and copy only primitives into `SimulationEngineRequest`.

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_service.py -q`

Expected: preparation tests PASS.

- [ ] **Step 3: Write a failing persistence graph test**

The fake engine returns three complete scenarios. Assert one simulation, three scenarios, twelve allocations and deterministic reasons are added only after the engine succeeds.

```python
def test_create_persists_complete_scenario_graph(service) -> None:
    created = service.create(valid_command(), SESSION_COOKIE)
    simulation = service.database.saved_simulation
    assert created.status == "COMPLETED"
    assert [scenario.code.value for scenario in simulation.scenarios] == ["A", "B", "C"]
    assert sum(len(scenario.allocations) for scenario in simulation.scenarios) == 12
    assert all(scenario.reasons for scenario in simulation.scenarios)
```

Run the single test and expect it to fail because persistence mapping is missing.

- [ ] **Step 4: Implement domain mapping and atomic persistence**

Use `Simulation.validate_scenarios()` before adding the graph. Map AI strategy, category and risk values explicitly to domain enums. Store an `AI_GENERATED_TEXT` reason once per scenario and calculated reasons linked to stored bottlenecks where the category receives more than 5%.

Set `Simulation.status` to `completed`, copy calculation/prompt/allocation versions and `public_data_reference_date`, then add and flush inside one transaction.

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_service.py -q`

Expected: all creation service tests PASS.

- [ ] **Step 5: Commit creation service**

Run:

```bash
git add backend/app/core/errors.py backend/app/services/simulation.py backend/tests/services/test_simulation_service.py
git commit -m "feat: 시뮬레이션 생성 서비스 구현"
```

Expected: service commit remains independent of FastAPI routes.

---

### Task 4: Result, comparison and selection service operations

**Files:**
- Modify: `backend/app/services/simulation.py`
- Modify: `backend/tests/services/test_simulation_service.py`

**Interfaces:**
- Produces: `SimulationService.get_result(simulation_id, session_cookie) -> SimulationResult`.
- Produces: `SimulationService.get_comparison(simulation_id, session_cookie) -> SimulationComparison`.
- Produces: `SimulationService.select_scenario(simulation_id, scenario_id, session_cookie) -> ScenarioSelected`.

- [ ] **Step 1: Write failing deterministic projection tests**

Assert scenario and allocation ordering, uppercase enum projection, selected scenario inclusion and the fixed neutral disclaimer.

```python
def test_get_result_orders_scenarios_and_allocations(service) -> None:
    result = service.get_result(45, SESSION_COOKIE)
    assert [scenario.scenario_code for scenario in result.scenarios] == ["A", "B", "C"]
    assert [item.category for item in result.scenarios[0].allocations] == [
        "MARKETING_ONLINE",
        "EQUIPMENT_INTERIOR",
        "LABOR",
        "INVENTORY",
    ]


def test_comparison_never_returns_a_recommendation(service) -> None:
    comparison = service.get_comparison(45, SESSION_COOKIE)
    assert comparison.recommendation_provided is False
    assert comparison.scenarios[0].financial_result.risk_level in {"LOW", "MEDIUM", "HIGH"}
```

Run the two tests and expect missing-method failures.

- [ ] **Step 2: Implement result and comparison projections**

Use frozen dataclasses inside the service as route-independent return values. Comparison reuses the same stored scenario mapper and omits reasons that are not required for side-by-side display. It must not call the AI engine.

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_service.py -q`

Expected: projection tests PASS.

- [ ] **Step 3: Write failing selection tests**

```python
def test_selection_rejects_scenario_from_another_simulation(service) -> None:
    with pytest.raises(ApiError) as error:
        service.select_scenario(45, 999, SESSION_COOKIE)
    assert error.value.code == "SCENARIO_NOT_IN_SIMULATION"
    assert error.value.status_code == 400


def test_selection_cannot_change_after_lock(service) -> None:
    service.database.selection.lock()
    with pytest.raises(ApiError) as error:
        service.select_scenario(45, 102, SESSION_COOKIE)
    assert error.value.code == "SELECTION_LOCKED"
    assert error.value.status_code == 409
```

Run the two tests and expect missing-method failures.

- [ ] **Step 4: Implement selection create and update**

Validate simulation ownership first, then load the scenario under that simulation. Create `ScenarioSelection` when absent. When present, call `change_scenario()` and translate its locked `ValueError` to `ApiError(409, "SELECTION_LOCKED", ...)`. Set `selected_at` with an aware UTC timestamp.

Run: `cd backend && .venv/bin/pytest tests/services/test_simulation_service.py -q`

Expected: all service tests PASS.

- [ ] **Step 5: Commit read and selection operations**

Run:

```bash
git add backend/app/services/simulation.py backend/tests/services/test_simulation_service.py
git commit -m "feat: 시뮬레이션 조회와 선택 서비스 추가"
```

Expected: one commit extending the already tested service.

---

### Task 5: FastAPI contracts and structured errors

**Files:**
- Create: `backend/app/api/routes/simulations.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/api/test_simulations.py`

**Interfaces:**
- Consumes: all `SimulationService` operations and `get_simulation_engine()`.
- Produces: `POST /api/businesses/{businessId}/simulations`.
- Produces: `GET /api/simulations/{simulationId}`.
- Produces: `GET /api/simulations/{simulationId}/comparison`.
- Produces: `POST /api/simulations/{simulationId}/selection`.
- Produces: `{"error": {"code": str, "message": str}}` for service and validation errors.

- [ ] **Step 1: Write failing creation contract tests**

Use `TestClient`, a fake database and a fake engine. Cover `201`, body shape, uppercase repayment input, invalid grace, missing ownership, incomplete diagnosis and engine failure.

```python
def test_create_simulation_returns_identifier_only(client) -> None:
    response = client.post(
        "/api/businesses/7/simulations",
        json={
            "diagnosisId": 31,
            "loanAmount": 15_000_000,
            "annualInterestRate": 0.045,
            "termMonths": 36,
            "graceMonths": 0,
            "repaymentType": "EQUAL_PAYMENT",
        },
    )
    assert response.status_code == 201
    assert response.json() == {"simulationId": 45, "status": "COMPLETED"}
```

Run: `cd backend && .venv/bin/pytest tests/api/test_simulations.py -q`

Expected: FAIL with `404` because the routes are not registered.

- [ ] **Step 2: Implement request schemas and creation route**

Use a model-level validator so `graceMonths < termMonths`. Convert the uppercase request enum to the domain `RepaymentType`. Catch only `SimulationGenerationError` at the service boundary and convert it to `ApiError(502, "SIMULATION_GENERATION_FAILED", ...)`.

Run the creation tests.

Expected: PASS.

- [ ] **Step 3: Write failing GET, comparison and selection contract tests**

Assert camelCase keys, A·B·C order, fixed disclaimer, `200` selection response and no AI invocation during GET operations.

Run the three tests and expect route-not-found failures.

- [ ] **Step 4: Implement remaining routes and error handlers**

Register handlers in `main.py`.

```python
@app.exception_handler(ApiError)
async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
    )
```

Add a `RequestValidationError` handler returning `422 VALIDATION_ERROR` without echoing invalid input values. Register `simulations_router` after existing routers.

Run: `cd backend && .venv/bin/pytest tests/api/test_simulations.py -q`

Expected: all API tests PASS.

- [ ] **Step 5: Verify OpenAPI**

Run a Python assertion against `app.openapi()` for all four paths, the `201` creation response, and request property names.

Expected: all assertions pass and no snake_case request property is exposed.

- [ ] **Step 6: Commit the HTTP layer**

Run:

```bash
git add backend/app/api/routes/simulations.py backend/app/main.py backend/tests/api/test_simulations.py
git commit -m "feat: 자금 배분 시뮬레이션 API 추가"
```

Expected: one commit containing only HTTP contracts and their tests.

---

### Task 6: PostgreSQL integration and final verification

**Files:**
- Create: `backend/tests/integration/test_simulation_api.py`
- Modify: `checklist.md`
- Modify: `context-notes.md`

**Interfaces:**
- Consumes: the public API and `get_simulation_engine` dependency.
- Verifies: real PostgreSQL constraints, transaction atomicity and selection uniqueness.

- [ ] **Step 1: Write PostgreSQL success and rollback tests**

Seed `DemoSession`, `Business`, ready `Dataset`, `BusinessSnapshot`, `PublicDataSnapshot`, completed `Diagnosis` and one `Bottleneck`. Override the engine with a deterministic fake.

The success test asserts the API returns `201` and the database contains one simulation, three scenarios, twelve allocations, reasons and one selectable scenario. The rollback test attaches a `before_insert` failure to `ScenarioAllocation` and asserts that no simulation graph row remains.

Run: `cd backend && TEST_DATABASE_URL=postgresql://keemhoeyune@127.0.0.1:55432/kb_domain_test .venv/bin/pytest tests/integration/test_simulation_api.py -q`

Expected with configured test PostgreSQL: PASS. Without `TEST_DATABASE_URL`: two tests SKIPPED with the repository-standard reason.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
cd backend
.venv/bin/pytest tests/ai tests/services/test_simulation_engine.py tests/services/test_simulation_service.py tests/api/test_simulations.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Expected: all non-PostgreSQL tests PASS, PostgreSQL tests either PASS with the configured URL or SKIP for the documented reason, and the backend CI와 동일한 두 Ruff 명령이 PASS.

- [ ] **Step 3: Inspect the final change set**

Run:

```bash
git diff --check
git status -sb
git log --oneline --decorate -8
```

Expected: no whitespace errors, only issue #34 implementation and the two preserved user changes remain, and logical implementation commits are visible.

- [ ] **Step 4: Update work records and commit**

Mark completed checklist items and append exact test counts, skipped integration reason, OpenAPI verification and remaining risks to `context-notes.md`.

Run:

```bash
git add backend/tests/integration/test_simulation_api.py checklist.md context-notes.md
git commit -m "test: 시뮬레이션 API 통합 검증 추가"
```

Expected: final logical commit contains integration coverage and verified work records.
