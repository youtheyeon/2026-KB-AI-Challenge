# Final MVP Domain Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 최종 MVP 명세에 맞춰 기존 예측 중심 도메인을 스냅샷, 정규화 데이터, 고정 시나리오, 조건 계산, 관측 결과 중심 모델로 개편한다.

**Architecture:** `Business`, `Dataset`, `Diagnosis`, `Simulation`, `Execution`, `OutcomeData`의 aggregate 경계를 유지하면서 부모 종속 모델은 cascade로 관리한다. 대량 정규화 행은 `Dataset`을 참조하는 독립 엔티티로 저장하고, 과거 결과 재현에 필요한 출처와 버전은 생성 시점의 스냅샷에 저장한다.

**Tech Stack:** Java 21, Spring Boot 4.1, Jakarta Persistence, Hibernate, Flyway, MySQL, H2, JUnit 5.

## Global Constraints

- 최종 MVP 문서에 값 목록이 명시된 선택지만 `EnumType.STRING`으로 저장한다.
- 값 목록이 없는 프로필 분류, 전략 코드, 목표 지표 코드는 `String`으로 저장한다.
- 금액은 `Long`, 비율은 `BigDecimal`, 기준일은 `LocalDate`, 시각은 `LocalDateTime`을 사용한다.
- 매출 증가율과 영업이익 증가율 예측, 추천, 순위, 사용자 배분 수정 모델을 추가하지 않는다.
- 모든 새 Java 소스 첫 줄에 파일 역할을 설명하는 한국어 주석을 작성한다.
- 공개 setter와 Lombok `@Data`를 사용하지 않는다.
- Controller, DTO, Repository, Service, 인증 구현은 이번 변경에서 제외한다.

---

### Task 1: 사업 프로필과 정규화 데이터

**Files:**
- Modify: `src/main/java/org/sopt/backend/domain/business/Business.java`
- Create: `src/main/java/org/sopt/backend/domain/source/DataSourceType.java`
- Modify: `src/main/java/org/sopt/backend/domain/dataset/Dataset.java`
- Modify: `src/main/java/org/sopt/backend/domain/dataset/DatasetFile.java`
- Modify: `src/main/java/org/sopt/backend/domain/dataset/DatasetFileType.java`
- Modify: `src/main/java/org/sopt/backend/domain/dataset/DatasetStatus.java`
- Create: `src/main/java/org/sopt/backend/domain/dataset/DatasetFormat.java`
- Create: `src/main/java/org/sopt/backend/domain/dataset/ExpenseCategory.java`
- Create: `src/main/java/org/sopt/backend/domain/dataset/OnlineSalesReconciliationType.java`
- Create: `src/main/java/org/sopt/backend/domain/dataset/NormalizedSale.java`
- Create: `src/main/java/org/sopt/backend/domain/dataset/NormalizedExpense.java`
- Create: `src/main/java/org/sopt/backend/domain/dataset/NormalizedOnlineSale.java`
- Test: `src/test/java/org/sopt/backend/domain/FinalMvpDataDomainTest.java`

**Interfaces:**
- Consumes: `User`, `BaseTimeEntity`.
- Produces: 확장된 `Business`, 상태 전이 가능한 `Dataset`, 파일 형식과 출처, 세 종류의 정규화 엔티티.

- [x] **Step 1: 실패 테스트 작성.** 필수 프로필, 선택 온라인 파일, 데이터셋 상태 전이, 온라인 매출 중복 합산 구분을 검증한다.
- [x] **Step 2: 실패 확인.** `./gradlew test --tests org.sopt.backend.domain.FinalMvpDataDomainTest`가 누락 타입과 메서드 때문에 실패해야 한다.
- [x] **Step 3: 최소 구현.** 명세 필드와 Enum만 추가하고 사용자 매핑 중심 상태를 제거한다.
- [x] **Step 4: 통과 확인.** 타깃 테스트와 기존 사업·데이터 테스트를 통과시킨다.
- [x] **Step 5: 커밋.** `feat: 최종 MVP 사업 데이터 모델 반영`.

### Task 2: 사업 스냅샷과 진단

**Files:**
- Create: `src/main/java/org/sopt/backend/domain/business/BusinessSnapshot.java`
- Create: `src/main/java/org/sopt/backend/domain/business/PublicDataSnapshot.java`
- Modify: `src/main/java/org/sopt/backend/domain/diagnosis/Diagnosis.java`
- Modify: `src/main/java/org/sopt/backend/domain/diagnosis/Bottleneck.java`
- Create: `src/main/java/org/sopt/backend/domain/diagnosis/BottleneckSeverity.java`
- Create: `src/main/java/org/sopt/backend/domain/diagnosis/DiagnosisMetric.java`
- Delete: `src/main/java/org/sopt/backend/domain/diagnosis/FinancialMetrics.java`
- Delete: `src/main/java/org/sopt/backend/domain/diagnosis/ActivityMetrics.java`
- Delete: `src/main/java/org/sopt/backend/domain/diagnosis/CommercialMetrics.java`
- Test: `src/test/java/org/sopt/backend/domain/FinalMvpDiagnosisDomainTest.java`

**Interfaces:**
- Consumes: `Business`, `Dataset`, `DataSourceType`.
- Produces: 재현 가능한 기준 스냅샷, 출처가 포함된 진단 지표, 심각도와 연결 카테고리를 가진 병목.

- [x] **Step 1: 실패 테스트 작성.** 기준 사업 상태, 공공데이터 기준일, 진단 현재값·비교값·출처, 병목 심각도와 연결 카테고리를 검증한다.
- [x] **Step 2: 실패 확인.** 타깃 테스트가 새 스냅샷과 진단 타입 부재로 실패해야 한다.
- [x] **Step 3: 최소 구현.** 기존 고정 지표 Embeddable을 일반화된 진단 지표와 병목 하위 엔티티로 교체한다.
- [x] **Step 4: 통과 확인.** 타깃 테스트를 통과시킨다.
- [ ] **Step 5: 커밋.** `feat: 사업 스냅샷과 근거 기반 진단 모델 추가`.

### Task 3: 고정 시나리오와 재무 결과

**Files:**
- Modify: `src/main/java/org/sopt/backend/domain/simulation/LoanCondition.java`
- Modify: `src/main/java/org/sopt/backend/domain/simulation/RepaymentType.java`
- Modify: `src/main/java/org/sopt/backend/domain/simulation/Simulation.java`
- Move: `src/main/java/org/sopt/backend/domain/simulation/AllocationPlan.java` to `src/main/java/org/sopt/backend/domain/simulation/Scenario.java`
- Move: `src/main/java/org/sopt/backend/domain/simulation/AllocationItem.java` to `src/main/java/org/sopt/backend/domain/simulation/ScenarioAllocation.java`
- Move: `src/main/java/org/sopt/backend/domain/simulation/PlanCode.java` to `src/main/java/org/sopt/backend/domain/simulation/ScenarioCode.java`
- Create: `src/main/java/org/sopt/backend/domain/simulation/AllocationCategory.java`
- Create: `src/main/java/org/sopt/backend/domain/simulation/ScenarioDraftReason.java`
- Create: `src/main/java/org/sopt/backend/domain/simulation/ScenarioFinancialResult.java`
- Create: `src/main/java/org/sopt/backend/domain/simulation/RiskLevel.java`
- Move: `src/main/java/org/sopt/backend/domain/selection/PlanSelection.java` to `src/main/java/org/sopt/backend/domain/selection/ScenarioSelection.java`
- Test: `src/test/java/org/sopt/backend/domain/FinalMvpSimulationDomainTest.java`

**Interfaces:**
- Consumes: `BusinessSnapshot`, `Dataset`, `Diagnosis`, `LoanCondition`.
- Produces: 수정 불가능한 A·B·C 시나리오, 비율·금액 배분, 생성 근거, 조건 계산 결과, 단일 선택.

- [ ] **Step 1: 실패 테스트 작성.** 대출 입력 계약, 카테고리 최소 5%, 비율 100%, 금액 합계, 재무 결과, 출처 버전을 검증한다.
- [ ] **Step 2: 실패 확인.** 타깃 테스트가 변경된 시나리오 API 부재로 실패해야 한다.
- [ ] **Step 3: 최소 구현.** 예측 기간과 예측 결과를 제거하고 고정 시나리오와 조건 계산 결과를 저장한다.
- [ ] **Step 4: 통과 확인.** 타깃 테스트를 통과시킨다.
- [ ] **Step 5: 커밋.** `feat: 고정 시나리오와 재무 비교 모델 반영`.

### Task 4: 집행과 관측 결과

**Files:**
- Modify: `src/main/java/org/sopt/backend/domain/execution/Execution.java`
- Move: `src/main/java/org/sopt/backend/domain/execution/ExecutionItem.java` to `src/main/java/org/sopt/backend/domain/execution/ExecutionAllocation.java`
- Move: `src/main/java/org/sopt/backend/domain/execution/ExecutionMode.java` to `src/main/java/org/sopt/backend/domain/execution/ExecutionType.java`
- Modify: `src/main/java/org/sopt/backend/domain/outcome/OutcomeData.java`
- Move: `src/main/java/org/sopt/backend/domain/outcome/Outcome.java` to `src/main/java/org/sopt/backend/domain/outcome/OutcomeComparison.java`
- Modify: `src/main/java/org/sopt/backend/domain/outcome/ComparisonRow.java`
- Move: `src/main/java/org/sopt/backend/domain/outcome/OutcomeReevaluation.java` to `src/main/java/org/sopt/backend/domain/outcome/ReassessmentSnapshot.java`
- Delete: `src/main/java/org/sopt/backend/domain/outcome/OutcomeSummary.java`
- Delete: `src/main/java/org/sopt/backend/domain/outcome/OutcomeTrends.java`
- Test: `src/test/java/org/sopt/backend/domain/FinalMvpOutcomeDomainTest.java`

**Interfaces:**
- Consumes: `Simulation`, `ScenarioSelection`, `BusinessSnapshot`, `Dataset`.
- Produces: 실제·Mock 집행, 집행 배분, 목표 조건 대비 관측 결과, 최신 상태와 병목 변화.

- [ ] **Step 1: 실패 테스트 작성.** 새 집행 유형, 실제 배분 합계, 관측값 명칭, 결과 상태, 해결·잔존·신규 병목을 검증한다.
- [ ] **Step 2: 실패 확인.** 타깃 테스트가 구형 집행·예측 비교 타입 때문에 실패해야 한다.
- [ ] **Step 3: 최소 구현.** 예측 대비 실제 필드를 목표 조건 대비 관측 필드로 교체한다.
- [ ] **Step 4: 통과 확인.** 타깃 테스트를 통과시킨다.
- [ ] **Step 5: 커밋.** `feat: 집행과 관측 결과 모델 개편`.

### Task 5: 스키마와 통합 검증

**Files:**
- Modify: `src/main/resources/db/migration/V1__create_domain_schema.sql`
- Replace: `src/test/java/org/sopt/backend/domain/BusinessDiagnosisDomainTest.java`
- Replace: `src/test/java/org/sopt/backend/domain/SimulationOutcomeDomainTest.java`
- Replace: `src/test/java/org/sopt/backend/domain/DomainPersistenceTest.java`
- Modify: `checklist.md`
- Modify: `context-notes.md`

**Interfaces:**
- Consumes: Task 1부터 Task 4까지의 모든 JPA 매핑.
- Produces: 최종 MVP 모델과 일치하는 초기 스키마와 전체 저장·조회 검증.

- [ ] **Step 1: 실패 통합 테스트 작성.** Flyway 적용 후 Hibernate `validate`, aggregate cascade, Enum 문자열, 버전 보존, 유일 제약을 검증한다.
- [ ] **Step 2: 실패 확인.** 기존 V1과 새 매핑 불일치로 애플리케이션 컨텍스트가 실패해야 한다.
- [ ] **Step 3: V1 개편.** 아직 배포되지 않은 초기 마이그레이션을 최종 MVP 테이블과 제약조건으로 교체한다.
- [ ] **Step 4: 최종 검증.** `./gradlew test`, `./gradlew bootJar`, `git diff --check develop...HEAD`를 실행한다.
- [ ] **Step 5: 커밋.** `test: 최종 MVP 도메인 매핑 검증`.
