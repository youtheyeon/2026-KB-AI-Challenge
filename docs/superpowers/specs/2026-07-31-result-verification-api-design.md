# 결과 검증 및 선순환 대시보드 API 설계

## 목표

완료된 자금 배분 시뮬레이션의 실제 집행과 사후 성과 데이터를 한 번씩 등록하고, 기존 `ai/` 결과 검증 로직으로 예상 대비 성과와 병목 변화를 계산해 저장한다. 저장된 결과는 결과 조회와 사업 대시보드에서 재계산 없이 일관되게 제공하며, 완료된 검증 이력은 다음 자금 배분 시뮬레이션의 지속 병목 최소 비중과 부작용 경고에 다시 사용한다.

## 확정 범위

- `GET /api/businesses/{businessId}/verification-targets`.
- `POST /api/simulations/{simulationId}/executions`.
- `POST /api/simulations/{simulationId}/outcome-data`.
- `POST /api/simulations/{simulationId}/outcomes`.
- `GET /api/simulations/{simulationId}/outcomes`.
- `GET /api/businesses/{businessId}/dashboard`.
- 익명 데모 세션 기반 소유권 검증.
- 기존 시뮬레이션·진단·데이터셋·스냅샷과 `ai/outcome_tracker.py` 재사용.
- 최신 `ai/business_history.py`의 지속 병목 상향과 부작용 이력 추적을 다음 시뮬레이션 생성에 연결.
- MOCK, FILE_UPLOAD, MANUAL_INPUT의 세 가지 사후 데이터 입력 방식.
- 실제 상환 이력이 없는 현재 도메인에서 계산한 대출 상환 추정치의 명시적 표시.

집행·사후 데이터·검증 결과 수정 API, 실제 상환 내역 등록, 비동기 작업 큐, 결과 검증 단계의 LLM 호출, 여러 번의 사후 측정과 시뮬레이션 재검증은 이번 범위에 포함하지 않는다. 저장된 완료 진단을 배분 근거의 단일 원천으로 사용하는 현재 시뮬레이션 계약도 유지하므로, 과거 POS로 현재 병목을 다시 진단하는 개인 기준선 치환은 이번 API에서 활성화하지 않는다. 다만 다음 사후 POS 스냅샷은 손실 없이 저장해 향후 진단 생성 경로에서 개인 기준선에 사용할 수 있게 한다.

## 공통 계약

외부 필드는 camelCase를 사용하고 상태와 enum은 대문자 문자열로 반환한다. 모든 자원은 현재 활성 데모 세션에 속한 사업장과 시뮬레이션을 통해서만 접근할 수 있다. 다른 세션의 자원은 존재 여부를 숨기기 위해 `404`로 처리한다.

집행, 사후 데이터, 검증 결과는 각각 시뮬레이션당 하나만 생성할 수 있는 불변 기록이다. 이미 존재하는 자원에 같은 POST를 다시 보내면 기존 자원을 덮어쓰지 않고 `409`를 반환한다.

## API 계약

### 검증 대상 목록

`GET /api/businesses/{businessId}/verification-targets`는 다음 조건을 모두 만족하는 시뮬레이션을 반환한다.

- 요청 사업장에 속한다.
- 상태가 `COMPLETED`다.
- 최종 `ScenarioSelection`이 존재한다.
- 서버 UTC 날짜를 기준으로 `Simulation.created_at`의 UTC 날짜부터 90일 이상 지났다.
- `includeCompleted=false`인 기본 요청에서는 아직 결과 검증이 완료되지 않았다.

`includeCompleted=true`이면 결과 검증이 이미 완료된 대상도 포함한다. 실제 집행만 등록되고 결과 검증이 남은 시뮬레이션은 기본 목록에 계속 노출하며 `executionRegistered=true`로 표시한다. 정확히 90일이 되는 날부터 대상에 포함하며 `daysElapsed`는 두 UTC 날짜의 차이다.

```json
{
  "businessId": 7,
  "targets": [
    {
      "simulationId": 45,
      "savedAt": "2026-04-30T12:00:00Z",
      "daysElapsed": 92,
      "executionRegistered": false,
      "businessName": "청춘카페",
      "region": "서울특별시 강남구",
      "loanAmount": 15000000,
      "planSummaries": [
        {
          "planCode": "A",
          "title": "병목 집중형"
        }
      ]
    }
  ]
}
```

### 실제 집행 등록

`POST /api/simulations/{simulationId}/executions`는 사용자가 실제로 집행한 배분을 저장한다.

```json
{
  "executionMode": "MIXED",
  "executedAt": "2026-07-30",
  "items": [
    {
      "name": "저녁 시간대 광고",
      "amount": 8000000
    },
    {
      "name": "좌석 및 조명 개선",
      "amount": 6500000
    }
  ],
  "unusedAmount": 500000
}
```

검증 규칙은 다음과 같다.

- 검증 대상 조건을 만족하고 최종 선택이 존재해야 한다.
- `executionMode`는 `SAME_AS_A`, `SAME_AS_B`, `SAME_AS_C`, `MIXED`, `CUSTOM` 중 하나다.
- `SAME_AS_A`, `SAME_AS_B`, `SAME_AS_C`는 서버가 해당 시나리오의 배분 항목과 카테고리를 복사하며 요청 `items`는 허용하지 않는다.
- `MIXED`, `CUSTOM`은 비어 있지 않은 `items`가 필요하고, 각 이름은 공백이 아닌 문자열이며 각 금액은 0보다 커야 한다.
- 자유 입력 항목은 이름을 필수로 저장하고 기존 고정 카테고리가 없으면 `category=null`로 저장한다.
- 집행 항목 금액 합계와 `unusedAmount`의 합은 시뮬레이션 대출 금액과 정확히 같아야 한다.
- `executedAt`은 미래 날짜일 수 없다.
- 실제 집행 방식이 기존 최종 선택과 달라도 허용한다. `ScenarioSelection`은 당시 결정의 감사 기록으로 보존하고 집행 생성과 함께 잠근다.

성공하면 `201 Created`를 반환한다.

```json
{
  "executionId": 81,
  "simulationId": 45,
  "executionMode": "MIXED",
  "totalExecutedAmount": 14500000,
  "savedAt": "2026-07-31T12:00:00Z"
}
```

### 사후 데이터 등록

`POST /api/simulations/{simulationId}/outcome-data`는 같은 URL에서 Content-Type에 따라 두 입력 계약을 제공한다.

- `MOCK`, `MANUAL_INPUT`은 `application/json`을 사용한다.
- `FILE_UPLOAD`는 `multipart/form-data`를 사용한다.
- 라우터는 Content-Type을 판별한 뒤 서로 다른 Pydantic 요청 모델로 검증한다.

MOCK 요청은 다음 형태를 사용한다.

```json
{
  "sourceType": "MOCK"
}
```

MANUAL_INPUT 요청은 다음 형태를 사용한다.

```json
{
  "sourceType": "MANUAL_INPUT",
  "metrics": {
    "monthlySalesAmount": 32000000,
    "operatingProfitAmount": 6200000,
    "onlineOrderRatio": 0.31,
    "cashAfterRepaymentAmount": 2800000
  }
}
```

FILE_UPLOAD 요청은 `sourceType=FILE_UPLOAD`, `salesFile`, `costFile`의 multipart 파트를 사용한다. 기존 xlsx 파서와 정규화 규칙을 재사용하고 업로드 원본은 영구 저장하지 않는다. 필수 컬럼을 자동 매핑할 수 없는 파일은 `400`으로 거부하고 사후 데이터의 유일 슬롯을 소비하지 않으므로 지원 형식으로 다시 요청할 수 있다.

모든 입력 방식은 후속 분석이 참조할 `Dataset`과 `BusinessSnapshot`을 생성한다. MOCK은 `ai/mock_pos_data.py`의 생성 결과를 정규화하고, FILE_UPLOAD는 파일을 파싱·정규화하며, MANUAL_INPUT은 네 지표를 `OutcomeData`에 구조화해 저장하고 스냅샷의 표현 가능한 필드를 함께 채운다. `datasetId`는 세 방식 모두 생성된 데이터셋을 가리킨다.

MANUAL_INPUT 스냅샷의 월 비용은 월 매출에서 영업이익을 뺀 값으로 계산하고, 온라인 주문 비중을 의미가 다른 `BusinessSnapshot.online_sales_ratio`에 복사하지 않는다. 공헌이익률과 직원 수처럼 스냅샷의 필수지만 이번 입력에서 관측하지 않은 값은 직전 스냅샷의 값으로 유지하고 비교 대상에서는 제외한다. 실제 입력한 네 값의 원본은 `OutcomeData`가 단일 원천이다.

성공하면 `201 Created`를 반환한다.

```json
{
  "outcomeDataId": 91,
  "simulationId": 45,
  "sourceType": "MANUAL_INPUT",
  "status": "READY",
  "datasetId": 62
}
```

외부 상태는 `READY`, `MAPPING_READY`, `FAILED`를 사용한다. 정상 MOCK·MANUAL_INPUT은 `READY`, 필수 컬럼 매핑과 정규화가 끝난 FILE_UPLOAD는 출처를 구분하기 위해 `MAPPING_READY`다. 두 상태 모두 결과 생성에 사용할 수 있다. 요청 검증 단계에서 발견한 손상 파일과 누락 컬럼은 `400`으로 거부하며, 저장 이후 예기치 않은 처리 실패가 발생한 경우에만 `FAILED`로 표시한다. `READY` 또는 `MAPPING_READY`가 아닌 데이터로 결과 생성을 요청하면 `409`를 반환한다.

### 결과 검증 생성

`POST /api/simulations/{simulationId}/outcomes`는 등록된 집행과 준비된 사후 데이터를 비교한다.

```json
{
  "executionId": 81,
  "outcomeDataId": 91
}
```

요청 식별자는 모두 URL의 시뮬레이션에 속해야 한다. 결과는 계산에 성공한 뒤 전체 비교 그래프를 한 번에 저장하고 `201 Created`를 반환한다.

```json
{
  "outcomeId": 101,
  "simulationId": 45,
  "status": "COMPLETED",
  "summary": {
    "salesGrowthStatus": "ABOVE_EXPECTED",
    "onlineRatioStatus": "WITHIN_RANGE",
    "cashAfterRepaymentStatus": "BELOW_EXPECTED"
  },
  "createdAt": "2026-07-31T12:10:00Z"
}
```

응답의 `COMPLETED`는 결과 생성 상태다. 전체 성과 판정인 `MET`, `PARTIALLY_MET`, `NOT_MET`, `NOT_COMPARABLE`과 지표별 판정인 `ABOVE_EXPECTED`, `WITHIN_RANGE`, `BELOW_EXPECTED`, `NOT_COMPARABLE`은 서로 다른 enum으로 저장하고 혼용하지 않는다.

지표별 판정은 임의의 성장률을 예측하지 않고 `targetValue`, `breakEvenValue`, `observedValue`의 세 값으로 결정한다.

- `observedValue >= targetValue`이면 `ABOVE_EXPECTED`다.
- `breakEvenValue <= observedValue < targetValue`이면 `WITHIN_RANGE`다.
- `observedValue < breakEvenValue`이면 `BELOW_EXPECTED`다.
- 목표나 관측 근거가 없거나 두 경계의 순서를 정할 수 없으면 `NOT_COMPARABLE`이다.

월 매출 목표는 사전 월 매출에 실제 집행안으로 다시 계산한 손익분기 추가 매출을 더한 값이고, 손익분기값은 사전 월 매출이다. 영업이익 목표는 월 상환액과 추가 고정비의 합이고 손익분기값은 0원이다. 온라인 주문 비중의 목표와 손익분기값은 사전 비중과 업계 참고 비중 중 큰 값과 작은 값이다. 상환 후 현금의 목표와 손익분기값은 0원과 실제 집행안의 재계산값 중 큰 값과 작은 값이다. 필요한 입력이 없으면 해당 지표를 `NOT_COMPARABLE`로 둔다.

### 결과 검증 조회

`GET /api/simulations/{simulationId}/outcomes`는 저장된 결과만 투영한다. 조회 시 `ai/` 계산을 다시 실행하지 않는다.

응답에는 다음 항목을 포함한다.

- 사전·사후 월 매출과 온라인 비중 등의 `trends`.
- 지표명, 소상공인 기준, 예상값, 실제값, 외부 기준과 판정을 담은 `comparisonRows`.
- 매출, 영업이익, 온라인 주문 비중, 상환 후 현금의 `reevaluation`.
- 새로 발생한 병목의 제목과 설명을 담은 `newBottlenecks`.

데이터에 없는 지표는 임의로 0을 만들지 않고 값과 판정을 `null` 또는 `NOT_COMPARABLE`로 반환한다.

### 선순환 대시보드

`GET /api/businesses/{businessId}/dashboard`는 사업장의 저장된 시뮬레이션과 결과 검증 기록을 시간순으로 모아 반환한다.

- `business`는 사업장 기본 정보를 반환한다.
- `loanStatus`는 가장 최근 실제 집행의 대출 조건과 경과 기간을 기준으로 계산한 상환 추정치다.
- `metricTrends`는 저장된 사전·사후 스냅샷의 지표 흐름이다.
- `cycleHistories`는 시뮬레이션, 최종 선택, 실제 집행, 검증 결과를 한 사이클로 묶는다.
- `unresolvedBottlenecks`는 가장 최근 검증에서 지속되거나 새로 발생한 병목이다.
- `nextInitialConditions`는 결과 비교와 함께 저장한 `next_round_pos_data_snapshot`을 우선 사용하는 가장 최근 사후 스냅샷이다.

실제 상환 내역을 입력받거나 저장하는 모델이 없으므로 `paidAmount`, `estimatedRemainingPrincipal`, `progressRate`는 실제 납부 실적이 아니다. 대출 원금, 금리, 상환 방식, 거치 기간, 집행일 이후 지난 완전한 개월 수를 기존 상환 계산 규칙에 적용한다. 결과에는 다음 구분 필드를 반드시 포함한다.

```json
{
  "loanStatus": {
    "loanAmount": 15000000,
    "monthlyRepaymentAmount": 446205,
    "paidAmount": 1338615,
    "estimatedRemainingPrincipal": 13932143,
    "progressRate": 0.0833,
    "repaymentDataType": "ESTIMATED"
  }
}
```

집행이나 검증 기록이 없으면 해당 선택 객체는 `null`, 반복 목록은 빈 배열로 반환한다. 대시보드는 저장된 결과를 조합하며 결과 검증을 새로 실행하지 않는다.

## 구조

### 라우터

새 `backend/app/api/routes/verifications.py`는 여섯 경로의 요청·응답 스키마, 쿠키 수신, Content-Type 분기, 의존성 주입과 HTTP 오류 변환만 담당한다. `backend/app/main.py`는 이 라우터를 등록한다.

### 서비스

책임을 네 서비스로 분리한다.

- `VerificationService`는 검증 대상 조회, 90일 판정, 실제 집행 생성과 선택 잠금을 담당한다.
- `OutcomeDataService`는 MOCK 생성, xlsx 파싱·정규화, 수동 지표 검증, 데이터셋·스냅샷·사후 데이터 저장을 담당한다.
- `OutcomeService`는 AI 입력 준비, 엔진 호출 결과 검증, 전체 비교 그래프 저장과 결과 조회를 담당한다.
- `DashboardService`는 저장된 사이클·추세·병목과 상환 추정치를 읽기 전용으로 투영한다.

서비스를 파일별로 과도하게 쪼개지 않고 관련 dataclass 명령·결과를 각 서비스 모듈에 함께 둔다. 라우터에는 도메인 계산을 두지 않는다.

### OutcomeEngine

`backend/app/services/outcome_engine.py`는 백엔드와 기존 `ai/` 코드 사이의 작은 어댑터다.

- MOCK 입력은 `ai/mock_pos_data.py`의 `generate_mock_pos_data()`를 호출한다.
- MOCK과 FILE_UPLOAD 비교는 `ai/outcome_tracker.py`의 `compare_outcomes()`를 호출한다.
- `compare_outcomes()`가 내부에서 재사용하는 `detect_bottlenecks()`와 `calculate_financial_projection()` 결과를 저장 모델로 변환한다.
- MANUAL_INPUT은 제공된 네 지표만 비교하며 `compare_outcomes()`가 요구하는 원시 POS 데이터를 꾸며내지 않는다.
- 자동 테스트는 가짜 엔진 또는 고정 입력을 사용하고 실제 LLM이나 외부 API를 호출하지 않는다.

현재 `compare_outcomes()`와 `detect_bottlenecks()`는 모든 POS 필드가 있다고 가정한다. 기존 완전 입력 동작을 유지하면서 선택적인 `comparable_bottleneck_types` 인자를 추가해 관측 가능한 유형만 읽고 비교하도록 최소 확장한다. 관측하지 않은 기존 병목을 해결된 병목으로 분류하지 않고 별도 `not_comparable_bottlenecks`로 반환한다.

MOCK은 생성기가 전체 POS 구조를 제공하므로 모든 병목을 재평가한다. FILE_UPLOAD는 실제 파일에서 계산 가능한 병목만 재평가한다. 예를 들어 거래 시간이 있으면 시간대 매출, 재료비·인건비 분류가 있으면 해당 비용 비율을 비교할 수 있지만, 매출·비용 두 파일에 없는 재구매율·좌석·온라인 정산 병목은 `NOT_COMPARABLE`로 유지한다. MANUAL_INPUT은 네 지표만 비교하고 모든 병목 재평가를 `NOT_COMPARABLE`로 저장한다.

실제 집행안은 항목 금액을 대출 원금으로 나눈 비율로 변환해 `calculate_financial_projection()`에 전달한다. 고정 카테고리가 없는 자유 항목은 기존 계산기의 미분류 항목 기본값인 12개월간 50% 반복 지출 가정을 적용하고 근거를 `DOMAIN_ASSUMPTION`으로 표시한다. 이 가정은 예상값 계산에만 사용하며 자유 항목에 임의의 고정 카테고리를 부여하지 않는다.

### 다음 회차 선순환 이력

결과 검증이 완료된 사이클은 사업장별 시간순 `business_history`로 변환해 다음 `SimulationService.create()`의 AI 입력에 전달한다. 한 이력 항목은 회차, 사후 활성 병목, 사후 POS 스냅샷과 실제 집행 카테고리 비율로 구성한다.

- `findings`에는 결과 검증에서 `REMAINING` 또는 `NEW`로 확정된 병목만 포함한다. `RESOLVED`와 관측하지 못한 `NOT_COMPARABLE`은 활성 병목으로 간주하지 않는다.
- `selected_allocation`은 실제 집행의 카테고리별 금액을 대출 원금으로 나눈 비율이다. 카테고리가 없는 자유 항목은 선순환 학습에서 다른 카테고리로 추측하지 않고 제외한다.
- 백엔드 진단의 `HIGH_MATERIAL_COST` 같은 코드는 AI의 `high_cost_ratio` 코드로 명시적으로 정규화한다. 알 수 없는 코드는 원문을 보존하되 카테고리 상향 대상에는 포함하지 않는다.
- `compute_persistence_counts()`와 `compute_escalated_min_shares()` 결과는 같은 병목이 최근 두 완료 회차에 연속 존재할 때 A·B안의 대응 카테고리 최소 비중을 5%에서 15%로 올린다.
- `compute_tradeoff_warnings()` 결과는 과거 특정 카테고리 집행 뒤 새 병목이 발생한 이력을 다음 배분 설명에 전달한다.
- 완료된 이력이 없으면 기존 1회차 동작과 동일해야 한다.

현재 백엔드 시뮬레이션은 저장된 완료 진단을 다시 진단하지 않고 `run_allocation_simulation()`을 호출한다. 따라서 개인 기준선은 결과 검증 API가 아니라 향후 진단 생성 경로에서 적용한다. 이번 구현은 그때 필요한 `next_round_pos_data_snapshot`을 저장하고, 현 구조에서 안전하게 적용 가능한 지속 병목 상향과 부작용 경고만 연결한다.

## 도메인과 마이그레이션

기존 초기 마이그레이션은 수정하지 않고 후속 Alembic 마이그레이션을 추가한다.

### 실제 집행

- `ExecutionAllocation.name`을 추가해 사용자가 입력한 집행 항목명을 보존한다.
- `ExecutionAllocation.category`를 nullable로 변경해 고정 카테고리가 없는 자유 배분을 허용한다.
- A·B·C 복사 항목은 기존 카테고리와 표시 이름을 함께 저장한다.
- `ExecutionType`에는 API가 요구하는 `SAME_AS_A`, `SAME_AS_B`, `SAME_AS_C`를 추가하고, 새 API는 다섯 확정 모드만 허용한다.
- 시뮬레이션당 하나인 기존 `Execution` 유일성, 배분 합계 검증과 `ScenarioSelection.locked`를 유지한다.

### 사후 데이터와 비교

- 사후 입력 종류를 나타내는 전용 `OutcomeDataSourceType`은 `MOCK`, `FILE_UPLOAD`, `MANUAL_INPUT`을 사용한다.
- 사후 데이터 처리 상태를 나타내는 전용 enum은 `READY`, `MAPPING_READY`, `FAILED`를 사용한다.
- 수동 입력의 월 매출, 영업이익, 온라인 주문 비중, 상환 후 현금을 `OutcomeData`의 nullable 구조화 필드로 저장한다.
- AI 비교가 반환한 다음 회차 POS 입력을 `OutcomeComparison.next_round_pos_data_snapshot` JSONB에 저장한다. 수동 입력은 제공된 값만 담은 부분 스냅샷을 저장한다.
- 지표 비교 상태는 `ABOVE_EXPECTED`, `WITHIN_RANGE`, `BELOW_EXPECTED`, `NOT_COMPARABLE`을 사용한다.
- 전체 성과 상태는 기존 의미의 `MET`, `PARTIALLY_MET`, `NOT_MET`, `NOT_COMPARABLE`을 유지한다.
- 병목 변화 상태에는 관측되지 않은 기존 병목을 보존하는 `NOT_COMPARABLE`을 추가한다.
- 결과 조회에 필요한 추세, 비교 행, 재평가와 병목 변화는 관계형 행과 JSON 값 중 기존 모델에 맞는 최소 필드로 저장하되, 공개 응답 전체를 단일 JSON blob으로 중복 저장하지 않는다.
- 기존 시뮬레이션당 하나인 `OutcomeData`와 시뮬레이션·집행·사후 데이터 조합당 하나인 `OutcomeComparison` 유일성을 유지하고 서비스 수준에서도 시뮬레이션당 결과 하나를 강제한다.

## 데이터 흐름과 트랜잭션

### 검증 대상 조회

현재 세션 소유 사업장의 완료 시뮬레이션, 선택, 집행과 결과 검증 존재 여부를 한 번에 읽고 UTC 날짜 차이를 계산한다. 결과 검증 존재 여부에 따라 기본 목록을 거른 뒤 생성 시각 오름차순으로 반환한다.

### 실제 집행 생성

1. 짧은 트랜잭션에서 시뮬레이션과 선택 행을 잠근다.
2. 소유권, 완료 상태, 90일 경과, 선택과 중복 집행 여부를 다시 검증한다.
3. A·B·C 모드는 저장 시나리오 배분을 복사하고 MIXED·CUSTOM은 요청 항목을 검증한다.
4. `Execution`과 전체 배분 항목을 저장하고 같은 트랜잭션에서 선택을 잠근다.
5. 어느 저장 단계든 실패하면 집행과 선택 잠금을 함께 롤백한다.

### 사후 데이터 생성

1. 짧은 조회에서 소유권, 집행 존재와 중복 사후 데이터 여부를 확인하고 입력 생성에 필요한 불변 값을 복사한다.
2. MOCK 생성 또는 파일 파싱·정규화는 데이터베이스 트랜잭션 밖에서 수행한다.
3. 짧은 저장 트랜잭션에서 시뮬레이션을 다시 잠그고 선행 상태와 중복을 재검증한다.
4. 데이터셋, 정규화 행, 사업 스냅샷과 `OutcomeData`를 한 번에 저장한다.
5. 저장 실패 시 전체를 롤백해 부분 데이터셋이나 고아 스냅샷을 남기지 않는다.

### 결과 검증 생성

1. 읽기 세션에서 소유권, 집행, `READY` 또는 `MAPPING_READY` 사후 데이터와 사전·사후 스냅샷을 불변 입력으로 복사한다.
2. 트랜잭션을 닫은 뒤 `OutcomeEngine`을 호출한다.
3. 엔진 결과의 필수 지표, 상태와 병목 분류 형상을 검증한다.
4. 짧은 저장 트랜잭션에서 관련 행을 잠그고 선행 입력과 중복을 다시 확인한다.
5. 비교, 지표, 재평가 스냅샷, 병목 변화와 다음 회차 POS 스냅샷을 원자적으로 저장한다.

엔진 실패나 잘못된 결과 형상에서는 비교 데이터를 일부도 저장하지 않는다. 데이터베이스 유일 제약과 행 잠금을 함께 사용해 동시 POST 두 건 중 하나만 성공하게 한다.

### 다음 시뮬레이션 생성

1. 기존 완료 진단과 데이터셋을 확인하면서 같은 사업장의 완료된 결과 비교 사이클을 시간순으로 읽는다.
2. 결과 병목 변화, 실제 집행과 저장된 다음 회차 POS 스냅샷을 불변 `business_history` 입력으로 복사한다.
3. 읽기 트랜잭션을 닫은 뒤 AI 시뮬레이션 엔진을 호출한다.
4. AI 엔진은 이력에서 지속 병목 최소 비중과 부작용 경고를 계산하되, 현재 병목은 저장된 완료 진단을 그대로 사용한다.

## 오류 계약

오류 응답은 기존 구조를 따른다.

```json
{
  "error": {
    "code": "OUTCOME_DATA_NOT_READY",
    "message": "준비된 사후 데이터만 결과 검증에 사용할 수 있습니다."
  }
}
```

- 지원하지 않는 Content-Type, 잘못된 집행 합계, 항목과 파일 형식은 `400`.
- 사업장·시뮬레이션·집행·사후 데이터·결과가 없거나 세션 소유권이 없으면 `404`.
- 90일 미경과, 최종 선택 없음, 선행 자원 미준비와 각 자원 중복 생성은 `409`.
- Pydantic 요청 형식 검증은 기존 전역 계약에 따라 `422`.
- `compare_outcomes()` 실행 실패와 잘못된 결과 형상은 `502 OUTCOME_CALCULATION_FAILED`.

공개 오류에는 내부 예외 원문, 사용자 입력 원문, 업로드 파일 경로, 스택 트레이스와 비밀 정보를 포함하지 않는다.

## 테스트 전략

각 동작은 실패 테스트를 먼저 추가해 예상한 이유로 실패하는지 확인한 뒤 최소 구현으로 통과시킨다.

### 도메인과 AI 단위 테스트

- 자유 집행 이름, nullable 카테고리, 대출 원금과의 합계, 선택 잠금과 중복 유일성을 검증한다.
- `compare_outcomes()`가 해결·지속·신규 병목과 재무 상태를 올바르게 분류하는지 고정 입력으로 검증한다.
- `OutcomeEngine`이 기존 AI 결과를 저장 모델로 변환하고 잘못된 결과 형상을 거부하는지 검증한다.
- `business_history.py`가 연속 병목, 최소 비중 상향과 부작용 경고를 결정론적으로 계산하는지 검증한다.
- 테스트에서는 실제 API, LLM과 네트워크를 사용하지 않는다.

### 서비스 테스트

- 정확히 90일 경계, 기본 결과 미완료 필터, 집행만 등록된 대상 유지, `includeCompleted`와 세션 격리를 검증한다.
- A·B·C 복사와 MIXED·CUSTOM 자유 집행, 합계 검증과 선택 잠금을 검증한다.
- MOCK, FILE_UPLOAD, MANUAL_INPUT의 정규화와 상태 전이를 검증한다.
- 수동 입력의 지표 비교와 병목 `NOT_COMPARABLE` 처리를 검증한다.
- 집행·사후 데이터·결과의 중복 요청이 `409`로 거부되는지 검증한다.
- 대시보드의 `ESTIMATED` 상환 표시, 추세, 사이클 기록과 다음 초기 조건을 검증한다.
- 완료된 검증 이력이 다음 시뮬레이션 엔진 입력으로 전달되고, 대문자 백엔드 병목 코드가 AI 코드로 정규화되는지 검증한다.

### API와 통합 테스트

- JSON과 multipart Content-Type 분기, camelCase 응답, 성공 상태 코드와 구조화 오류를 검증한다.
- OpenAPI에 여섯 경로와 사후 데이터의 두 Content-Type 계약이 노출되는지 확인한다.
- PostgreSQL 통합 테스트로 전체 저장 그래프, 유일 제약, 행 잠금과 중간 실패 롤백을 검증한다.
- 최종 검증은 백엔드 전체 pytest, Ruff 검사·포맷 검사, `git diff --check`와 OpenAPI 계약 확인으로 수행한다.

## 성공 기준

- 여섯 API가 Notion 계약의 필드와 상태 코드를 제공한다.
- 서로 다른 데모 세션의 데이터가 노출되지 않는다.
- 시뮬레이션당 집행·사후 데이터·결과가 불변 기록으로 한 번만 저장된다.
- MOCK과 FILE_UPLOAD는 기존 `ai/` 결과 검증 경로를 재사용하고, FILE_UPLOAD와 MANUAL_INPUT에서 관측하지 않은 병목을 해결로 오판하지 않는다.
- 완료 결과의 다음 회차 POS 스냅샷이 저장되고, 후속 시뮬레이션에서 지속 병목 최소 비중과 부작용 경고가 실제 집행 이력으로부터 적용된다.
- 개인 기준선 치환은 현재 저장 진단 계약을 우회해 재진단하지 않으며, 향후 진단 경로가 사용할 POS 스냅샷만 보존한다.
- 실패와 동시 요청에서 부분 저장이 발생하지 않는다.
- 대시보드는 실제 납부 내역이 없는 추정치를 `repaymentDataType=ESTIMATED`로 명확히 구분한다.
- 관련 단위·API·PostgreSQL 통합 테스트와 전체 백엔드 검사가 통과한다.
