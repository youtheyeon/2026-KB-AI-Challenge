# 사업자 기본 정보 등록 API 구현 계획

## 목표

익명 데모 세션을 기준으로 사업자 기본 정보를 등록하는 `POST /api/businesses` API를 구현한다.

## 범위

- 요청 필드는 `name`, `region`, `industry`, `employeeCount`, `primarySalesChannels`로 정의한다.
- 성공 시 `201 Created`와 생성된 사업자 정보를 반환한다.
- 유효한 데모 세션 쿠키가 없으면 새 세션을 생성해 `HttpOnly`, `SameSite=Lax` 쿠키로 발급한다.
- 운영 환경에서는 쿠키에 `Secure` 속성을 적용한다.
- 생성된 사업자는 현재 데모 세션과 연결한다.
- 이슈 2의 데이터 업로드 및 데이터셋 API는 구현하지 않는다.

## 전역 제약

- 작업 브랜치는 `feat/28`이다.
- 새 Python 소스 파일 첫 줄에는 역할을 설명하는 한국어 주석을 작성한다.
- 기존 SQLAlchemy 모델과 PostgreSQL 마이그레이션은 변경하지 않는다.
- `.gitignore`와 `docs/project-proposal-plan.md`의 기존 사용자 변경을 건드리지 않는다.
- 외부 API는 camelCase를 사용하고 내부 모델은 snake_case를 유지한다.
- TDD의 RED, GREEN 순서를 지키고 테스트 근거를 남긴다.
- 데이터 업로드와 컬럼 매핑 API는 구현하지 않는다.

### Task 1: 사업자 기본 정보 등록 API 구현

#### 외부 계약

- 쿠키 이름은 `demo_session_id`다.
- 새 데모 세션의 유효 기간은 생성 시점부터 24시간이다.
- `BACKEND_ENVIRONMENT=production`일 때만 쿠키에 `Secure`를 적용한다.
- 요청의 `name`, `region`, `industry`는 공백을 제거한 뒤 한 글자 이상이어야 한다.
- `employeeCount`는 생략 시 `0`이며 음수를 허용하지 않는다.
- `primarySalesChannels`는 생략 시 빈 배열이다.
- 응답은 `businessId`, `name`, `region`, `industry`, `employeeCount`, `primarySalesChannels`를 반환한다.
- 유효한 요청은 `201 Created`, 스키마 검증 실패는 `422 Unprocessable Entity`를 반환한다.

#### 세션 동작

- 쿠키가 없거나 UUID 형식이 아니면 새 활성 세션을 생성한다.
- 쿠키가 가리키는 세션이 없거나 만료되었거나 활성 상태가 아니면 새 활성 세션을 생성한다.
- 만료된 기존 활성 세션은 `expired` 상태로 변경한다.
- 유효한 세션은 재사용하고 `last_accessed_at`을 현재 시각으로 갱신한다.
- 세션 확인과 사업자 생성은 하나의 데이터베이스 트랜잭션으로 커밋한다.

#### 작업 순서

1. 사업자 등록 API의 성공, 입력 검증, 세션 재사용과 만료 동작을 표현하는 실패 테스트를 작성한다.
2. 데이터베이스 세션 의존성과 데모 세션 쿠키 해석 로직을 구현한다.
3. Pydantic 요청·응답 스키마와 사업자 등록 서비스를 구현한다.
4. `POST /api/businesses` 라우터를 애플리케이션에 연결한다.
5. 관련 테스트와 전체 백엔드 검사를 실행한다.

## 완료 조건

- 유효한 요청은 `201 Created`를 반환한다.
- 쿠키가 없거나 만료되면 새 데모 세션이 만들어진다.
- 유효한 쿠키가 있으면 기존 데모 세션을 재사용한다.
- 빈 필수값과 음수 직원 수는 `422 Unprocessable Entity`로 거부한다.
- 세션 쿠키는 `HttpOnly`, `SameSite=Lax`이며 운영 환경에서만 `Secure`다.
- `.venv/bin/pytest -q`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`가 통과한다.
