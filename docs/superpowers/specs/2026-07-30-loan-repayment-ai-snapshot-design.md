# 대출 조건·AI 결과 스냅샷·실제 상환 기록 보강 설계

## 목표

기존 도메인 흐름을 유지하면서 시뮬레이션 당시 대출 입력값, AI가 생성한 비교·SCB 결과, 집행 후 실제 상환 현황을 이력으로 보존한다.

## 확정 범위

- 컬럼 자동 매핑·검수 엔티티는 추가하지 않는다.
- 배분 항목은 기존 네 고정 카테고리만 지원한다.
- AI 모델 호출과 계산 로직은 이번 작업에서 구현하지 않는다.
- AI가 생성한 시나리오 비교 지표와 SCB 해석은 `Scenario`의 JSONB 스냅샷으로 저장한다.
- 실제 상환 내역을 저장하는 `RepaymentRecord`만 새 영속 엔티티로 추가한다.

## 모델 변경

### LoanCondition

`LoanCondition`은 계속 `Simulation`에 종속된 composite 값 객체로 유지하고 다음 값을 추가한다.

- `own_funds_amount`.
- `existing_monthly_repayment_amount`.
- `planned_use_date`.

자기자금은 상환 부담과 잔여현금 계산 입력으로 사용하며 시나리오 배분금액 합계는 계속 대출금액과 일치시킨다.

### Scenario AI 결과 스냅샷

`Scenario`에 다음 필드를 추가한다.

- `comparison_metrics` JSONB.
- `scb_interpretation` JSONB.
- `ai_model_version`.
- `ai_generated_at`.

JSONB는 AI 응답 형식 변화에 대응하기 위한 저장 경계이며, 기존 `prompt_version`과 `calculation_version`은 생성 근거 추적에 계속 사용한다.

### RepaymentRecord

`RepaymentRecord`는 실제 또는 Mock 집행인 `Execution`에 종속되며 다음 값을 저장한다.

- 납부 예정일과 실제 납부 시각.
- 원금, 이자, 총 납부액.
- 납부 후 남은 원금.
- `SCHEDULED`, `PAID`, `OVERDUE` 상태.

동일 집행과 납부 예정일 조합은 하나만 허용하고 모든 금액은 0 이상이어야 한다.

## 관계와 삭제 정책

- `Execution 1:N RepaymentRecord`.
- 상환 기록은 집행이 소유하므로 집행 삭제 시에만 연쇄 삭제한다.
- 기존 스냅샷, 진단, 시뮬레이션, 집행 이력의 갱신 금지 원칙은 유지한다.

## 마이그레이션

이미 공개된 초기 마이그레이션은 수정하지 않고 후속 Alembic 마이그레이션을 추가한다. 기존 시뮬레이션 행에도 적용될 수 있도록 새 필수 컬럼은 안전한 기본값으로 채운 뒤 불필요한 임시 기본값을 제거한다.

## 검증

- composite 값 객체가 추가 대출 조건을 보존하는지 검증한다.
- AI 결과 JSONB와 생성 메타데이터가 저장되는지 검증한다.
- 상환 기록 관계, 상태, 유일 제약, 금액 범위를 검증한다.
- PostgreSQL에서 25개 테이블 생성과 Alembic upgrade, downgrade, re-upgrade를 검증한다.
