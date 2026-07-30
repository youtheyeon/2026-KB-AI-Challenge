# feat/16 컨텍스트 노트

## 확정한 결정

- 작업 브랜치는 `feat/16`이다.
- 외부 식별 엔티티는 `User`, `Business`, `Dataset`, `Diagnosis`, `Simulation`, `PlanSelection`, `Execution`, `OutcomeData`, `Outcome`이다.
- `DatasetFile`, `ColumnMapping`, `AllocationPlan`은 부모에 종속된 하위 엔티티로 구현한다.
- 식별자는 API 명세의 `number` 타입에 맞춰 `Long` 자동 증가 전략을 사용한다.
- 원화 금액은 `Long`, 비율과 신뢰도는 `BigDecimal`, 시각은 `LocalDateTime`, 기준일은 `LocalDate`를 사용한다.
- 명세에 값 목록이 확정된 필드만 문자열 Enum으로 저장한다.
- 연관관계는 기본적으로 지연 로딩 단방향이며, 소유 하위 모델에만 cascade와 orphan removal을 적용한다.
- `Dashboard`, `ScenarioComparison`, `VerificationTarget`은 조회 모델이므로 저장 엔티티에서 제외한다.
- API, 서비스, Repository, 인증, 실제 파일 저장은 이번 작업에서 제외한다.
- 운영 설정의 `ddl-auto=validate`를 유지하고 Flyway 초기 마이그레이션을 추가한다.
- 테스트는 H2 MySQL 모드에서 Flyway 적용 후 Hibernate 검증을 수행한다.

## 확인한 현재 상태

- `feat/16`은 `develop`과 같은 `fe23fbe`에서 시작한다.
- 작업 시작 전 Git 변경 사항은 없다.
- 작업 시작 전 `./gradlew test`는 성공한다.

## 진행 기록

- 2026-07-30. 구현 계획, 체크리스트, 컨텍스트 노트를 작성했다.
- 2026-07-30. 사업체 소유 관계, 데이터셋 파일·매핑 상태, 진단 완료 상태의 실패 테스트를 확인한 뒤 관련 모델을 구현했다.
- 2026-07-30. `./gradlew test`와 `git diff --check`로 첫 번째 도메인 묶음을 검증했다.
- 2026-07-30. 시뮬레이션 배분안, 선택, 집행 금액 불변식, 결과 데이터와 결과 비교의 실패 테스트를 확인한 뒤 관련 모델을 구현했다.
- 2026-07-30. 결과 추이와 비교 행은 순서를 보존하는 값 객체 컬렉션으로 저장하도록 결정했다.
- 2026-07-30. `./gradlew test`와 `git diff --check`로 두 번째 도메인 묶음을 검증했다.
- 2026-07-30. Spring Boot 4의 Flyway 자동 설정 모듈인 `spring-boot-flyway`와 MySQL 지원 모듈을 추가했다.
- 2026-07-30. H2 MySQL 모드에서 Flyway 마이그레이션 후 Hibernate `ddl-auto=validate`가 통과함을 확인했다.
- 2026-07-30. 전체 도메인 그래프 저장·조회와 사용자 이메일 유일 제약조건을 영속성 통합 테스트로 검증했다.
- 2026-07-30. `./gradlew test`와 `git diff --check`로 초기 스키마와 통합 테스트를 검증했다.
- 2026-07-30. 리뷰 결과에 따라 부모 종속 하위 엔티티를 단방향 `OneToMany`와 `JoinColumn`로 변경했다.
- 2026-07-30. 시뮬레이션 저장 시 A, B, C 배분안이 각각 하나씩 있는지 생명주기 콜백으로 검증한다.
- 2026-07-30. `OutcomeData`의 `Dataset` 참조는 명세에 없는 유일 제약을 제거하고 지연 로딩 다대일 관계로 유지한다.
- 2026-07-30. 진단 병목과 모든 목록형 값 객체는 순서 컬럼을 사용해 재조회 순서를 보존한다.
- 2026-07-30. 파일 유형, 컬럼 매핑, 배분안 코드와 시뮬레이션별 선택·집행·결과 데이터·결과 유일 제약을 실제 DB 위반 테스트로 검증했다.
- 2026-07-30. `./gradlew clean` 후 `./gradlew test`, `./gradlew bootJar`, `git diff --check develop...HEAD`가 모두 성공했다.

## 최종 MVP 개편 결정

- 2026-07-30. 확정 MVP 문서를 기존 API 명세와 엔티티보다 우선하는 기준으로 사용한다.
- 2026-07-30. `User`와 사업 소유 관계는 인증·소유권 검증을 위해 유지한다.
- 2026-07-30. 값 목록이 없는 사업 프로필 분류, 시나리오 전략, 목표 지표는 문자열로 저장한다.
- 2026-07-30. `BusinessSnapshot`, `PublicDataSnapshot`과 버전 필드로 과거 시뮬레이션 입력을 보존한다.
- 2026-07-30. 매출·비용·온라인 주문은 각각 정규화 엔티티로 저장하고 온라인 매출의 POS 포함 여부를 명시한다.
- 2026-07-30. 사용자 컬럼 매핑은 핵심 흐름에서 제거하되 `ColumnMapping`은 관리자 예외 수정용 하위 모델로 유지한다.
- 2026-07-30. `AllocationPlan`은 `Scenario`, `Outcome`은 `OutcomeComparison`으로 변경하고 예측 표현을 제거한다.
- 2026-07-30. 최종 MVP 개편 전 `./gradlew test`는 성공했다.
- 2026-07-30. 사업 프로필의 값 목록이 없는 분류는 문자열로 저장하고 선택 입력 지표는 nullable로 유지했다.
- 2026-07-30. 정규화 데이터는 대량 행 조회를 고려해 `Dataset` 컬렉션에 cascade하지 않고 지연 로딩 다대일로 연결했다.
- 2026-07-30. 온라인 매출은 `OnlineSalesReconciliationType`으로 POS 전체 매출 중복 합산 여부를 명시한다.
- 2026-07-30. `FinalMvpDataDomainTest`와 기존 사업·데이터 도메인 테스트가 성공했다.
- 2026-07-30. `BusinessSnapshot`은 기준 재무·활동값과 원본 `Dataset` 버전을 보존한다.
- 2026-07-30. `PublicDataSnapshot`은 공공데이터 기준일, 출처명, 지역과 버전을 보존한다.
- 2026-07-30. 진단 지표는 현재값·비교값·차이·단위·출처·벤치마크 버전을 가진 목록으로 일반화했다.
- 2026-07-30. 병목은 심각도와 관련 배분 카테고리를 저장하는 `Diagnosis` 소유 하위 엔티티로 변경했다.
- 2026-07-30. `FinalMvpDiagnosisDomainTest`와 관련 기존 도메인 테스트가 성공했다.
