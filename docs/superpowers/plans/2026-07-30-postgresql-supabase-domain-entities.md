# PostgreSQL·Supabase Domain Entities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI 백엔드에 PostgreSQL·Supabase용 SQLAlchemy 도메인 엔티티 24개와 Alembic 초기 스키마를 추가한다.

**Architecture:** SQLAlchemy 2 선언형 모델을 사업 데이터, 진단, 시뮬레이션, 집행, 결과 추적 aggregate로 나눈다. Alembic을 유일한 스키마 변경 도구로 사용하고, 부모 소유 하위 모델에만 삭제 연쇄를 적용하며 과거 스냅샷은 변경하지 않는다.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Psycopg 3, PostgreSQL 15+, Supabase, pytest, Ruff, uv.

## Global Constraints

- 작업 브랜치는 `feat/16`이며 시작 기준은 `develop`의 `615a195` 커밋이다.
- Supabase는 호스팅 PostgreSQL로만 사용하고 Auth, Storage, RLS는 제외한다.
- API, 서비스, AI 분석 로직과 프론트엔드는 변경하지 않는다.
- 새 Python 소스 파일 첫 줄에는 역할을 설명하는 한국어 주석을 작성한다.
- 금액은 정수 원 단위, 비율과 금리는 `Decimal`, 날짜는 `date`, 시각은 UTC 기준 timezone-aware `datetime`을 사용한다.
- DB Enum은 PostgreSQL native enum이 아닌 문자열과 체크 제약으로 저장한다.
- 기본키는 `BIGINT` 자동 증가 방식을 사용한다.
- Alembic만 스키마 변경 도구로 사용한다.
- 구현은 테스트를 먼저 작성하고 예상한 이유로 실패한 것을 확인한 뒤 진행한다.

---

### Task 1: PostgreSQL 영속성 기반

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `backend/.env.example`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Test: `backend/tests/test_database_config.py`

**Interfaces:**
- Consumes: `BACKEND_DATABASE_URL`, `BACKEND_MIGRATION_DATABASE_URL`.
- Produces: `Base`, `TimestampMixin`, `engine`, `SessionFactory`, Alembic metadata.

- [ ] 데이터베이스 설정과 공통 모델 API를 요구하는 실패 테스트를 작성한다.
- [ ] 테스트가 SQLAlchemy 또는 DB 설정 부재로 실패하는지 확인한다.
- [ ] SQLAlchemy 2, Alembic, Psycopg 3 의존성과 동기 세션 기반을 최소 구현한다.
- [ ] 런타임 URL과 마이그레이션 URL을 분리하고 비밀번호가 코드나 예시 파일에 들어가지 않게 한다.
- [ ] 타깃 테스트와 기존 헬스 체크 테스트를 통과시킨다.
- [ ] `chore: PostgreSQL 영속성 기반 추가`로 커밋한다.

### Task 2: 사업 데이터와 진단 엔티티

**Files:**
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/enums.py`
- Create: `backend/app/domain/user.py`
- Create: `backend/app/domain/business.py`
- Create: `backend/app/domain/dataset.py`
- Create: `backend/app/domain/diagnosis.py`
- Test: `backend/tests/domain/test_business_data.py`
- Test: `backend/tests/domain/test_diagnosis.py`

**Interfaces:**
- Produces: `User`, `Business`, `Dataset`, `DatasetFile`, `NormalizedSale`, `NormalizedExpense`, `NormalizedOnlineSale`, `PublicDataSnapshot`, `BusinessSnapshot`, `Diagnosis`, `DiagnosisMetric`, `Bottleneck`.

- [ ] 이메일 정규화, 필수 사업 프로필, 파일 유형 유일성, 온라인 매출 정합 기본값을 검증하는 실패 테스트를 작성한다.
- [ ] 동일 사업장·데이터셋 스냅샷과 진단 근거 출처를 검증하는 실패 테스트를 작성한다.
- [ ] 12개 엔티티와 필요한 문자열 Enum, 관계, 인덱스, 체크 제약을 최소 구현한다.
- [ ] 공공데이터 원본과 가변 메타데이터는 PostgreSQL `JSONB`로 저장한다.
- [ ] 매출·비용 파일 필수 여부는 `Dataset.validate_ready()`에서 검증하고 온라인 파일은 선택으로 둔다.
- [ ] 타깃 테스트와 전체 기존 테스트를 통과시킨다.
- [ ] `feat: 사업 데이터와 진단 엔티티 추가`로 커밋한다.

### Task 3: 시뮬레이션과 집행 엔티티

**Files:**
- Create: `backend/app/domain/simulation.py`
- Create: `backend/app/domain/execution.py`
- Test: `backend/tests/domain/test_simulation.py`
- Test: `backend/tests/domain/test_execution.py`

**Interfaces:**
- Produces: `Simulation`, `Scenario`, `ScenarioAllocation`, `ScenarioReason`, `ScenarioSelection`, `Execution`, `ExecutionAllocation`, `LoanCondition`, `ScenarioFinancialResult`.

- [ ] A·B·C 구성, 네 카테고리, 카테고리별 5% 이상, 비율 100%, 금액 합계를 요구하는 실패 테스트를 작성한다.
- [ ] 다른 시뮬레이션의 선택 거부, 집행 후 선택 잠금, 집행액과 미집행액 합계를 요구하는 실패 테스트를 작성한다.
- [ ] `LoanCondition`과 `ScenarioFinancialResult`는 별도 테이블 없이 부모 컬럼에 매핑되는 값 객체로 구현한다.
- [ ] 고정 배분안을 변경하는 공개 API나 수정 이력은 만들지 않는다.
- [ ] 타깃 테스트와 전체 테스트를 통과시킨다.
- [ ] `feat: 시뮬레이션과 집행 엔티티 추가`로 커밋한다.

### Task 4: 결과 추적과 재평가 엔티티

**Files:**
- Create: `backend/app/domain/outcome.py`
- Test: `backend/tests/domain/test_outcome.py`

**Interfaces:**
- Produces: `OutcomeData`, `OutcomeComparison`, `OutcomeComparisonMetric`, `ReassessmentSnapshot`, `BottleneckChange`.

- [ ] 관측 데이터와 시뮬레이션의 사업장 일치, 실제 집행 기준 비교, 목표·손익분기·관측값 명칭을 요구하는 실패 테스트를 작성한다.
- [ ] 해결·잔존·신규 병목과 다음 회차 스냅샷 보존을 요구하는 실패 테스트를 작성한다.
- [ ] 시뮬레이션별 관측 데이터와 결과 비교는 각각 하나만 존재하도록 구현한다.
- [ ] 예측값이나 매출·영업이익 증가율 필드를 만들지 않는다.
- [ ] 타깃 테스트와 전체 테스트를 통과시킨다.
- [ ] `feat: 결과 추적과 재평가 엔티티 추가`로 커밋한다.

### Task 5: 초기 마이그레이션과 통합 검증

**Files:**
- Create: `backend/alembic/versions/20260730_0001_initial_domain_schema.py`
- Create: `backend/compose.yaml`
- Modify: `.github/workflows/backend-ci.yml`
- Modify: `backend/README.md`
- Test: `backend/tests/integration/test_domain_persistence.py`
- Test: `backend/tests/integration/test_alembic_migration.py`

**Interfaces:**
- Consumes: 모든 SQLAlchemy 모델과 `Base.metadata`.
- Produces: 재현 가능한 PostgreSQL 초기 스키마와 로컬·CI 테스트 DB 실행 방법.

- [ ] PostgreSQL에서 전체 관계 저장·조회와 삭제 연쇄를 검증하는 실패 통합 테스트를 작성한다.
- [ ] 빈 PostgreSQL DB에서 Alembic upgrade, downgrade, 재-upgrade를 검증하는 실패 테스트를 작성한다.
- [ ] 전체 테이블, 외래키, 유일·체크 제약, 인덱스를 가진 초기 마이그레이션을 작성한다.
- [ ] CI에 격리된 PostgreSQL 서비스를 추가하고 원격 Supabase에는 연결하지 않는다.
- [ ] README에 로컬 PostgreSQL, 런타임 연결, Alembic 직접 연결, 검증 명령을 설명한다.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `git diff --check`를 통과시킨다.
- [ ] `feat: PostgreSQL 초기 도메인 스키마 추가`와 `test: 도메인 영속성 검증`으로 의미를 분리해 커밋한다.
