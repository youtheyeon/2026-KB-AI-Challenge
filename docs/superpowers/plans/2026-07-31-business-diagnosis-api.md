# Business Diagnosis API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 정규화된 사업 데이터와 고정된 서울시 카페 벤치마크로 비동기 진단을 실행하고 상태·지표·병목을 조회하는 두 API를 구현한다.

**Architecture:** 라우터는 세션 소유권과 HTTP 계약을 담당하고, 진단 서비스는 스냅샷과 상태 전이를 영속화한다. 순수 분석 서비스는 DB에서 수집한 월별 입력과 버전 고정 벤치마크를 받아 지표·병목을 계산하며, FastAPI `BackgroundTasks`는 요청 세션과 분리된 새 SQLAlchemy 세션으로 결과를 저장한다.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2, PostgreSQL 15+, pytest 9, Ruff.

## Global Constraints

- Notion 계약의 `POST /api/businesses/{businessId}/diagnoses`와 `GET /api/diagnoses/{diagnosisId}`를 구현한다.
- 외부 응답의 상태, 우선순위, 신뢰도는 대문자 문자열로 반환한다.
- 진단 요청 중 외부 공공데이터 API를 호출하지 않는다.
- 유동인구 자료가 없으므로 `floatingPopulationGrowthRate`는 `null`이다.
- 온라인 자료가 없으면 온라인 지표는 `null`이고 온라인 병목은 생성하지 않는다.
- 기존 진단·스냅샷 테이블을 사용하며 Alembic 마이그레이션을 추가하지 않는다.
- 새 Python 파일 첫 줄에는 역할을 설명하는 한국어 주석을 둔다.
- 파괴적 PostgreSQL 통합 테스트는 격리된 `TEST_DATABASE_URL`에서만 실행한다.

---

### Task 1: 고정 벤치마크와 순수 분석 계산

**Files:**
- Create: `backend/app/data/seoul_cafe_benchmark.json`
- Create: `backend/app/services/diagnosis_analysis.py`
- Create: `backend/tests/services/test_diagnosis_analysis.py`

**Interfaces:**
- Consumes: `AnalysisInput`, `Benchmark` 데이터 클래스.
- Produces: `load_benchmark() -> Benchmark`, `analyze(input_data, benchmark) -> AnalysisResult`.
- Produces: `AnalysisResult.metrics: tuple[MetricResult, ...]`, `AnalysisResult.bottlenecks: tuple[BottleneckResult, ...]`.

- [ ] **Step 1: 핵심 지표 계산 실패 테스트를 작성한다**

```python
def test_analyze_calculates_financial_activity_and_commercial_metrics() -> None:
    result = analyze(
        AnalysisInput(
            reference_date=date(2026, 7, 31),
            monthly_sales_amount=30_000_000,
            monthly_expense_amount=26_700_000,
            material_cost_amount=12_000_000,
            labor_cost_amount=6_000_000,
            existing_monthly_repayment_amount=1_500_000,
            monthly_order_count=420,
            employee_count=2,
            online_sales_amount=2_700_000,
            online_gross_order_amount=3_000_000,
            online_platform_cost_amount=450_000,
            online_refund_amount=150_000,
            online_settlement_amount=2_760_000,
            timed_sales_by_bucket={},
            timed_sales_coverage=Decimal("0"),
        ),
        benchmark(),
    )

    values = {metric.code: metric.current_value for metric in result.metrics}
    assert values["MONTHLY_SALES_AMOUNT"] == Decimal("30000000")
    assert values["OPERATING_PROFIT_RATE"] == Decimal("11.0")
    assert values["MATERIAL_COST_RATE"] == Decimal("40.0")
    assert values["CASH_SURPLUS_AMOUNT"] == Decimal("1800000")
    assert values["ONLINE_SALES_RATIO"] == Decimal("9.0")
    assert values["SALES_COMPARED_TO_PEER_RATE"] == Decimal("-8.0")
```

- [ ] **Step 2: 분석 테스트가 모듈 부재로 실패하는지 확인한다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest tests/services/test_diagnosis_analysis.py -q`

Expected: `ModuleNotFoundError: No module named 'app.services.diagnosis_analysis'`.

- [ ] **Step 3: 벤치마크와 최소 분석 구현을 추가한다**

```python
@dataclass(frozen=True)
class AnalysisInput:
    reference_date: date
    monthly_sales_amount: int
    monthly_expense_amount: int
    material_cost_amount: int
    labor_cost_amount: int
    existing_monthly_repayment_amount: int
    monthly_order_count: int
    employee_count: int
    online_sales_amount: int | None
    online_gross_order_amount: int | None
    online_platform_cost_amount: int | None
    online_refund_amount: int | None
    online_settlement_amount: int | None
    timed_sales_by_bucket: dict[str, int]
    timed_sales_coverage: Decimal


def analyze(input_data: AnalysisInput, benchmark: Benchmark) -> AnalysisResult:
    if input_data.monthly_sales_amount <= 0:
        raise DiagnosisAnalysisError("월매출이 0보다 커야 합니다.")
    operating_profit = _percent(
        input_data.monthly_sales_amount - input_data.monthly_expense_amount,
        input_data.monthly_sales_amount,
    )
    material_cost = _percent(
        input_data.material_cost_amount,
        input_data.monthly_sales_amount,
    )
    cash_surplus = (
        input_data.monthly_sales_amount
        - input_data.monthly_expense_amount
        - input_data.existing_monthly_repayment_amount
    )
    return AnalysisResult(
        metrics=_build_metrics(input_data, benchmark, operating_profit, material_cost, cash_surplus),
        bottlenecks=_detect_bottlenecks(input_data, benchmark),
    )
```

벤치마크 JSON에는 `20242`, 기준일 `2024-06-30`, 표본 `326`, 월매출 중앙값 `94283406`, 월주문 중앙값 `11729`, 시간대 비중 `0.005565/0.12448/0.345965/0.268165/0.217863/0.037963`을 저장한다.

- [ ] **Step 4: 병목 경계값과 자료 부재 테스트를 추가한다**

```python
def test_analyze_detects_severe_material_cost_and_channel_concentration() -> None:
    result = analyze(input_with(material_cost_amount=17_100_000, online_sales_amount=1_500_000), benchmark())
    by_code = {item.code: item for item in result.bottlenecks}
    assert by_code["HIGH_MATERIAL_COST"].severity is BottleneckSeverity.SEVERE
    assert by_code["CHANNEL_CONCENTRATION"].severity is BottleneckSeverity.SEVERE


def test_analyze_omits_online_metrics_and_bottlenecks_without_online_data() -> None:
    result = analyze(input_with(online_sales_amount=None), benchmark())
    assert "ONLINE_SALES_RATIO" not in {metric.code for metric in result.metrics}
    assert not any(item.code.startswith("CHANNEL_") for item in result.bottlenecks)
```

- [ ] **Step 5: 분석 테스트를 통과시킨다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest tests/services/test_diagnosis_analysis.py -q`

Expected: 모든 분석 테스트 통과.

- [ ] **Step 6: 분석 단위를 커밋한다**

```bash
git add backend/app/data backend/app/services/diagnosis_analysis.py backend/tests/services/test_diagnosis_analysis.py
git commit -m "feat: 사업 진단 계산 서비스 추가"
```

### Task 2: 진단 스냅샷과 백그라운드 상태 전이

**Files:**
- Create: `backend/app/services/diagnosis_service.py`
- Create: `backend/tests/services/test_diagnosis_service.py`

**Interfaces:**
- Consumes: `Session`, `Business`, `Dataset`, `load_benchmark`, `analyze`.
- Produces: `create_running_diagnosis(database, business, dataset) -> Diagnosis`.
- Produces: `run_diagnosis(diagnosis_id: int) -> None`.

- [ ] **Step 1: 최신 월 집계와 스냅샷 실패 테스트를 작성한다**

```python
def test_collect_analysis_input_uses_latest_sales_month() -> None:
    input_data = collect_analysis_input(database, business, dataset, benchmark())
    assert input_data.reference_date == date(2026, 7, 31)
    assert input_data.monthly_sales_amount == 30_000_000
    assert input_data.material_cost_amount == 12_000_000
    assert input_data.monthly_order_count == 420
```

- [ ] **Step 2: 서비스 테스트의 예상 실패를 확인한다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest tests/services/test_diagnosis_service.py -q`

Expected: `ModuleNotFoundError: No module named 'app.services.diagnosis_service'`.

- [ ] **Step 3: 실행 진단 생성과 결과 저장을 구현한다**

```python
def create_running_diagnosis(
    database: Session,
    business: Business,
    dataset: Dataset,
) -> Diagnosis:
    benchmark = load_benchmark()
    input_data = collect_analysis_input(database, business, dataset, benchmark)
    business_snapshot = _get_or_create_business_snapshot(database, business, dataset, input_data)
    public_snapshot = _create_public_data_snapshot(database, business, benchmark)
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
    database.add(diagnosis)
    database.flush()
    return diagnosis
```

`run_diagnosis`는 새 세션과 단일 트랜잭션에서 입력 재수집, 분석, `DiagnosisMetric`·`Bottleneck` 저장, `COMPLETED` 전이를 수행한다. 예외 시 롤백 후 새 트랜잭션에서 `FAILED`로 변경하고 `logger.exception`으로 원인을 기록한다.

- [ ] **Step 4: 성공·실패 상태 전이 테스트를 추가한다**

```python
def test_run_diagnosis_persists_results_and_marks_completed(monkeypatch) -> None:
    run_diagnosis(diagnosis_id)
    assert stored_diagnosis.status is DiagnosisStatus.COMPLETED
    assert stored_diagnosis.metrics
    assert stored_diagnosis.bottlenecks


def test_run_diagnosis_marks_failed_when_analysis_raises(monkeypatch) -> None:
    monkeypatch.setattr(diagnosis_service, "analyze", raise_analysis_error)
    run_diagnosis(diagnosis_id)
    assert stored_diagnosis.status is DiagnosisStatus.FAILED
```

- [ ] **Step 5: 서비스 테스트를 통과시키고 커밋한다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest tests/services/test_diagnosis_service.py -q`

Expected: 모든 진단 서비스 테스트 통과.

```bash
git add backend/app/services/diagnosis_service.py backend/tests/services/test_diagnosis_service.py
git commit -m "feat: 비동기 진단 상태 전이 구현"
```

### Task 3: 진단 실행·조회 API

**Files:**
- Create: `backend/app/api/routes/diagnoses.py`
- Create: `backend/tests/api/test_diagnosis_api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `create_running_diagnosis`, `run_diagnosis`, `DiagnosisMetric`, `Bottleneck`.
- Produces: `POST /api/businesses/{business_id}/diagnoses`.
- Produces: `GET /api/diagnoses/{diagnosis_id}`.

- [ ] **Step 1: API 계약 실패 테스트를 작성한다**

```python
def test_create_diagnosis_returns_running_and_schedules_background_task(monkeypatch) -> None:
    response = client.post("/api/businesses/1/diagnoses", json={"datasetId": 10})
    assert response.status_code == 202
    assert response.json() == {
        "diagnosisId": 20,
        "businessId": 1,
        "status": "RUNNING",
        "createdAt": "2026-07-29T03:26:00+09:00",
    }


def test_get_completed_diagnosis_returns_metrics_and_bottlenecks() -> None:
    response = client.get("/api/diagnoses/20")
    assert response.status_code == 200
    assert response.json()["financialMetrics"]["monthlySalesAmount"] == 30_000_000
    assert response.json()["commercialMetrics"]["floatingPopulationGrowthRate"] is None
    assert response.json()["bottlenecks"][0]["priority"] == "HIGH"
```

- [ ] **Step 2: 라우터 부재로 404가 발생하는지 확인한다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest tests/api/test_diagnosis_api.py -q`

Expected: 진단 경로가 `404 Not Found`로 실패.

- [ ] **Step 3: 요청·응답 모델과 라우터를 구현한다**

```python
@router.post(
    "/api/businesses/{business_id}/diagnoses",
    response_model=DiagnosisStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_diagnosis(
    business_id: int,
    request: DiagnosisStartRequest,
    background_tasks: BackgroundTasks,
    database: Annotated[Session, Depends(get_db)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> DiagnosisStartResponse:
    with database.begin():
        business, dataset = _get_owned_ready_dataset(
            database, business_id, request.dataset_id, demo_session_cookie
        )
        diagnosis = create_running_diagnosis(database, business, dataset)
        response = _start_response(diagnosis)
    background_tasks.add_task(run_diagnosis, response.diagnosis_id)
    return response
```

조회 응답은 메트릭 코드를 camelCase 필드에 매핑한다. 병목의 `severity`에서 우선순위를, 근거 출처에서 신뢰도를 도출한다. 진단 전용 요청 검증 오류만 `400`으로 바꾸고 기존 API의 FastAPI `422` 동작은 유지한다.

- [ ] **Step 4: 오류와 세션 격리 테스트를 추가한다**

```python
def test_create_diagnosis_returns_conflict_when_dataset_is_not_ready() -> None:
    response = client.post("/api/businesses/1/diagnoses", json={"datasetId": 10})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DATASET_NOT_READY"


def test_get_diagnosis_hides_another_session_result() -> None:
    response = other_session_client.get("/api/diagnoses/20")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DIAGNOSIS_NOT_FOUND"
```

- [ ] **Step 5: API 테스트를 통과시키고 커밋한다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest tests/api/test_diagnosis_api.py -q`

Expected: 모든 진단 API 테스트 통과.

```bash
git add backend/app/api/routes/diagnoses.py backend/app/main.py backend/tests/api/test_diagnosis_api.py
git commit -m "feat: 사업 진단 실행 및 조회 API 추가"
```

### Task 4: PostgreSQL 영속화와 전체 검증

**Files:**
- Create: `backend/tests/integration/test_diagnosis_api.py`
- Modify: `backend/README.md`
- Modify: `checklist.md`
- Modify: `context-notes.md`

**Interfaces:**
- Consumes: 완성된 진단 API와 기존 `TEST_DATABASE_URL` 격리 장치.
- Produces: 실제 PostgreSQL에서 스냅샷·지표·병목의 원자성을 검증하는 회귀 테스트.

- [ ] **Step 1: PostgreSQL 통합 테스트를 작성한다**

```python
def test_diagnosis_background_task_persists_snapshots_metrics_and_bottlenecks(
    postgres_engine: Engine,
) -> None:
    response = client.post(
        f"/api/businesses/{business_id}/diagnoses",
        json={"datasetId": dataset_id},
    )
    assert response.status_code == 202
    with Session(postgres_engine) as database:
        diagnosis = database.scalar(select(Diagnosis))
        assert diagnosis is not None
        assert diagnosis.status is DiagnosisStatus.COMPLETED
        assert diagnosis.metrics
        assert diagnosis.public_data_snapshot.raw_data["sampleSize"] == 326
```

- [ ] **Step 2: 격리 DB가 없을 때 통합 테스트가 안전하게 스킵되는지 확인한다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest tests/integration/test_diagnosis_api.py -q`

Expected: `TEST_DATABASE_URL`이 없으면 스킵, 있으면 통과.

- [ ] **Step 3: 문서와 작업 기록을 갱신한다**

`backend/README.md`에 진단 API의 BackgroundTasks 특성과 재시작 시 작업 유실 가능성을 기록한다. `checklist.md`의 이슈 3 항목을 완료 표시하고 `context-notes.md`에 실제 테스트 결과와 남은 위험을 기록한다.

- [ ] **Step 4: 전체 검증을 실행한다**

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/python -m pytest -q`

Expected: 기존 테스트와 신규 테스트가 모두 통과하고 PostgreSQL 전용 테스트만 환경에 따라 스킵.

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/ruff check .`

Expected: `All checks passed!`.

Run: `cd backend && /Users/keemhoeyune/Desktop/2026-KB-AI-Challenge/backend/.venv/bin/ruff format --check .`

Expected: 모든 파일이 포맷됨.

Run: `git diff --check`

Expected: 출력 없이 종료 코드 0.

- [ ] **Step 5: 구현 기록을 커밋한다**

```bash
git add backend/README.md backend/tests/integration/test_diagnosis_api.py checklist.md context-notes.md
git commit -m "test: 사업 진단 API 통합 검증 추가"
```
