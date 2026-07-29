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
