# 자금 배분 시뮬레이션 API 설계

## 목표

완료된 사업 진단과 사용자가 입력한 대출 조건을 바탕으로 A·B·C 자금 배분안을 동기 생성하고, 생성 결과 조회·중립 비교·최종 선택을 지원한다.

## 확정 범위

- `POST /api/businesses/{businessId}/simulations`.
- `GET /api/simulations/{simulationId}`.
- `GET /api/simulations/{simulationId}/comparison`.
- `POST /api/simulations/{simulationId}/selection`.
- 익명 데모 세션 기반 소유권 검증.
- 기존 `Simulation`, `Scenario`, `ScenarioAllocation`, `ScenarioReason`, `ScenarioSelection` 모델 활용.
- 저장된 완료 진단을 배분 근거의 단일 원천으로 사용.
- 같은 Python 프로세스에서 서비스와 AI 어댑터를 거쳐 AI 엔진을 동기 호출.

진단 생성·조회 API, 결과 검증 API, 실제 집행 API, 비동기 작업 큐, 시뮬레이션 재시도와 멱등성 키는 이번 범위에 포함하지 않는다.

## API 계약

외부 필드는 camelCase를 사용하고 상태와 enum은 대문자 문자열로 반환한다.

### 시뮬레이션 생성

`POST /api/businesses/{businessId}/simulations` 요청은 다음 형태를 사용한다.

```json
{
  "diagnosisId": 31,
  "loanAmount": 15000000,
  "annualInterestRate": 0.045,
  "termMonths": 36,
  "graceMonths": 0,
  "repaymentType": "EQUAL_PAYMENT"
}
```

검증 규칙은 다음과 같다.

- `loanAmount`는 0보다 커야 한다.
- `annualInterestRate`는 0 이상 1 이하여야 한다.
- `termMonths`는 0보다 커야 한다.
- `graceMonths`는 0 이상이고 `termMonths`보다 작아야 한다.
- `repaymentType`은 `EQUAL_PAYMENT`, `EQUAL_PRINCIPAL`, `BULLET_PAYMENT` 중 하나다.
- `diagnosisId`가 가리키는 진단은 요청 사업장에 속하고 `COMPLETED` 상태여야 한다.
- 진단에 연결된 데이터셋은 요청 사업장에 속하고 `READY` 상태여야 한다.

생성은 동기 처리한다. 성공하면 전체 결과를 저장하고 다음 식별자 응답만 `201 Created`로 반환한다.

```json
{
  "simulationId": 45,
  "status": "COMPLETED"
}
```

### 시뮬레이션 결과 조회

`GET /api/simulations/{simulationId}`는 저장된 결과를 반환한다.

```json
{
  "simulationId": 45,
  "businessId": 7,
  "diagnosisId": 31,
  "status": "COMPLETED",
  "loanCondition": {
    "amount": 15000000,
    "annualInterestRate": 0.045,
    "termMonths": 36,
    "graceMonths": 0,
    "repaymentType": "EQUAL_PAYMENT"
  },
  "scenarios": [
    {
      "scenarioId": 101,
      "scenarioCode": "A",
      "strategyType": "BOTTLENECK_FOCUSED",
      "title": "병목 집중형",
      "allocations": [
        {
          "category": "MARKETING_ONLINE",
          "ratio": 0.85,
          "amount": 12750000
        }
      ],
      "reasons": [
        {
          "bottleneckId": 201,
          "category": "MARKETING_ONLINE",
          "description": "특정 시간대 고객 유입 부족에 대응하는 배분입니다.",
          "sourceType": "CALCULATED"
        }
      ],
      "financialResult": {
        "monthlyLoanPayment": 446205,
        "monthlyRecurringCost": 812500,
        "cashAfterPayment": -313705,
        "breakEvenAdditionalRevenue": 540871,
        "requiredAdditionalOrders": 62,
        "paybackPeriodMonths": null,
        "riskLevel": "HIGH"
      },
      "targetMetrics": [
        "EVENING_REVENUE",
        "ORDER_COUNT"
      ],
      "riskReasons": [
        "현재 매출 수준에서 상환·고정비 부담이 발생합니다."
      ]
    }
  ],
  "selectedScenarioId": null,
  "createdAt": "2026-07-31T12:00:00Z"
}
```

시나리오는 항상 A, B, C 순서로, 배분은 `MARKETING_ONLINE`, `EQUIPMENT_INTERIOR`, `LABOR`, `INVENTORY` 순서로 반환한다.

### 시나리오 비교 조회

`GET /api/simulations/{simulationId}/comparison`은 저장된 세 시나리오를 같은 필드로 투영한다. 새 계산이나 추천 순위를 만들지 않는다.

응답에는 다음 항목을 포함한다.

- 시나리오 식별자, 코드, 전략 유형과 제목.
- 네 카테고리의 배분 금액과 비율.
- 월 상환액, 월 반복 비용, 상환 후 현금, 손익분기 추가 매출, 추가 주문 수와 회수 기간.
- 위험 수준, 위험 근거와 목표 지표.
- 추천과 성과 보장을 하지 않는 고정 안내문.

### 최종 시나리오 선택

`POST /api/simulations/{simulationId}/selection` 요청은 다음 형태를 사용한다.

```json
{
  "scenarioId": 101
}
```

선택이 없으면 생성하고, 기존 선택이 있으면 집행 잠금 전까지만 변경한다. 선택한 시나리오는 반드시 요청한 시뮬레이션에 속해야 한다. 성공 응답은 생성과 변경 모두 `200 OK`를 사용한다.

```json
{
  "simulationId": 45,
  "selectedScenarioId": 101,
  "selectedAt": "2026-07-31T12:30:00Z",
  "locked": false
}
```

## 구조

### 라우터

`backend/app/api/routes/simulations.py`는 요청·응답 스키마, 쿠키 수신, 의존성 주입과 HTTP 오류 변환만 담당한다.

### 시뮬레이션 서비스

`backend/app/services/simulation.py`는 다음 책임을 가진다.

- 사업장, 진단, 데이터셋과 시뮬레이션의 소유권 검증.
- 완료 진단과 준비된 데이터셋 검증.
- 사업장·스냅샷·정규화 데이터에서 AI 입력 생성.
- AI 어댑터 호출.
- AI 결과의 도메인 모델 변환과 영속화.
- 결과·비교 응답 투영.
- 시나리오 선택 생성·변경과 잠금 검증.

### AI 어댑터

`backend/app/services/simulation_engine.py`는 백엔드가 사용하는 작은 인터페이스와 기본 구현을 제공한다. 서비스 테스트는 가짜 엔진을 주입하고, 기본 구현만 `ai/` 모듈을 직접 호출한다.

현재 `ai/` 디렉터리가 설치 가능한 패키지가 아니므로 기본 구현은 저장소 루트의 `ai` 경로를 import 검색 경로에 한 번 추가한 뒤 모듈을 불러온다. 이 경로 처리는 어댑터 밖으로 노출하지 않는다.

## AI 엔진 변경

현재 `run_simulation()`은 병목 탐지와 시나리오 생성을 한 함수에서 수행한다. 저장된 진단과 다른 진단을 재생성하지 않도록 시나리오 생성 부분을 `run_allocation_simulation(findings, loan, pos_data)` 함수로 추출한다.

- 기존 `run_simulation()`은 병목을 탐지한 뒤 새 함수를 호출해 기존 동작을 유지한다.
- 백엔드 어댑터는 저장된 `Diagnosis.bottlenecks`를 AI findings 구조로 변환해 새 함수를 직접 호출한다.
- 저장된 병목의 `detail`을 비교 설명으로 사용한다.
- 병목의 `related_categories`와 `evidence_source_type`으로 제안 카테고리와 신뢰도 배지를 구성한다.
- LLM 설명 생성은 네트워크 오류와 키 누락 시 일반 예외를 발생시키며 프로세스를 종료하지 않는다.

AI 결과의 전체 설명 중 구조화 가능한 근거는 `ScenarioReason`에 저장한다.

- 의미 있게 배분된 카테고리와 연결된 저장 병목마다 계산 근거를 저장한다.
- LLM이 생성한 전체 배분 설명은 가장 높은 비율의 카테고리에 `AI_GENERATED_TEXT` 근거로 한 번 저장한다.

## 대출 상환 계산

기존 계산기는 원리금 균등 상환만 계산하므로 입력한 상환 방식과 거치 기간을 반영하도록 보강한다.

- `EQUAL_PAYMENT`는 거치 기간 뒤 남은 기간의 원리금 균등 월 납부액을 사용한다.
- `EQUAL_PRINCIPAL`은 거치 기간 뒤 첫 달의 원금 균등 납부액을 사용한다. 이후 납부액은 감소하므로 첫 달 값을 보수적인 대표 월 납부액으로 본다.
- `BULLET_PAYMENT`는 만기 전 월 이자액을 대표 월 납부액으로 사용하고, 만기 원금 상환 위험을 `riskReasons`에 명시한다.
- 거치 기간에는 이자만 납부하지만 시나리오 비교의 `monthlyLoanPayment`는 거치 종료 후 대표 납부액을 사용한다.

## 데이터 흐름과 트랜잭션

생성 요청은 다음 순서로 처리한다.

1. 짧은 조회 세션에서 소유권과 선행 상태를 검증하고 필요한 입력을 불변 값으로 복사한다.
2. 데이터베이스 트랜잭션을 열지 않은 상태에서 AI 엔진을 호출한다.
3. AI 결과가 A·B·C와 네 배분 카테고리 불변조건을 만족하는지 검증한다.
4. 짧은 저장 트랜잭션에서 시뮬레이션, 시나리오, 배분과 근거를 모두 저장한다.
5. 저장 중 하나라도 실패하면 전체 트랜잭션을 롤백한다.

AI 실행에 실패하면 시뮬레이션 행을 남기지 않는다. 같은 요청을 재전송하면 새 시뮬레이션을 생성하며 요청 멱등성은 이번 범위에서 보장하지 않는다.

## 오류 계약

오류 응답은 다음 형태를 사용한다.

```json
{
  "error": {
    "code": "DIAGNOSIS_NOT_COMPLETED",
    "message": "완료된 진단만 시뮬레이션에 사용할 수 있습니다."
  }
}
```

- 요청 스키마와 대출 조건 검증 실패는 `422`.
- 사업장·진단·시뮬레이션이 없거나 세션 소유권이 없으면 `404`.
- 완료되지 않은 진단과 준비되지 않은 데이터셋은 `409`.
- 다른 시뮬레이션의 시나리오 선택은 `400`.
- 집행으로 잠긴 선택 변경은 `409`.
- AI 키 누락, 타임아웃, HTTP 오류와 잘못된 AI 결과는 `502 SIMULATION_GENERATION_FAILED`.

내부 예외 메시지, API 키와 외부 응답 원문은 클라이언트에 노출하지 않는다.

## 테스트

- AI 단위 테스트로 저장 findings 기반 A·B·C 생성과 기존 `run_simulation()` 호환성을 검증한다.
- 재무 계산 단위 테스트로 세 상환 방식, 무이자, 거치 기간과 경계값을 검증한다.
- 서비스 테스트는 가짜 AI 엔진으로 입력 변환, 도메인 매핑, 불변조건과 롤백을 검증한다.
- API 테스트는 생성·조회·비교·선택의 성공 응답과 `400`, `404`, `409`, `422`, `502`를 검증한다.
- 세션 테스트는 다른 익명 데모 세션의 자원을 숨기는지 검증한다.
- PostgreSQL 통합 테스트는 시뮬레이션 전체 그래프와 선택이 실제 제약 조건 아래 저장되는지 검증한다.
- 자동 테스트는 실제 LLM과 외부 API를 호출하지 않는다.
- 최종 검증은 백엔드 전체 pytest, Ruff 검사와 OpenAPI 계약 확인으로 수행한다.

