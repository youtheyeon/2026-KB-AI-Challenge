# PostgreSQL·Supabase 도메인 엔티티 작업 기록

## 확정 결정

- 백엔드는 Python 3.13과 FastAPI 기반을 유지한다.
- 운영 데이터베이스는 Supabase가 호스팅하는 PostgreSQL을 사용한다.
- Supabase Auth, Storage, RLS는 이번 작업에서 제외한다.
- SQLAlchemy 2 동기 세션과 Psycopg 3를 사용한다.
- Alembic을 유일한 스키마 변경 도구로 사용한다.
- 원격 Supabase가 아닌 격리된 PostgreSQL에서 로컬·CI 테스트를 실행한다.
- 매출이나 영업이익을 예측하지 않고 목표·손익분기 조건과 관측 결과를 비교한다.
- A·B·C 시나리오는 읽기 전용 고정안이며 사용자가 배분을 수정하지 않는다.

## 작업 기준

- 작업 시작 커밋은 `615a195`이다.
- 기준 테스트는 `uv run pytest`로 실행했으며 기존 테스트 3개가 통과했다.
- `uv`는 실행 환경의 `/private/tmp/codex-uv-bin/uv`를 사용한다.

## Task 1 구현 결정

- 런타임과 Alembic 마이그레이션 URL은 각각 `database_url`, `migration_database_url` 환경설정으로 분리한다.
- 예시와 기본 URL은 로컬 PostgreSQL의 비밀번호 없는 접속 형태만 제공한다. 실제 Supabase 자격 증명은 `.env`에서만 주입한다.
- `TimestampMixin`은 PostgreSQL 서버 시각 기본값과 갱신 시각을 제공하고, 동기 `SessionFactory`는 `autoflush=False`, `autocommit=False`를 유지한다.
- Alembic `env.py`는 실행 시 `BACKEND_MIGRATION_DATABASE_URL` 값을 `sqlalchemy.url`에 주입하고 `Base.metadata`를 메타데이터로 사용한다.

## Task 1 검증 기록

- RED. `uv run pytest tests/test_database_config.py`는 `ModuleNotFoundError: No module named 'sqlalchemy'`로 실패해 요구 의존성 부재를 확인했다.
- GREEN. 의존성 잠금·설치 후 타깃 테스트 3개와 전체 테스트 6개가 통과했다.
- `uv run alembic -c alembic.ini upgrade head --sql`, `uv run ruff check .`, `uv run ruff format --check .`, `git diff --check`를 통과했다.

## Task 1 리뷰 후속 조치

- Alembic `Config.set_main_option()`은 URL 인코딩된 `%`를 ConfigParser 보간으로 해석하므로, 마이그레이션 URL을 설정하기 전에 `%`를 `%%`로 이스케이프한다.
- `%40`을 포함한 URL로 실제 Alembic 오프라인 마이그레이션 실행을 검증해 회귀를 방지한다.

## Task 2 구현 계획

- 사업 데이터와 진단 aggregate는 각각의 소유 부모에만 ORM 삭제 연쇄를 적용하고, 공개 데이터와 사업 스냅샷은 과거 진단의 근거로 보존한다.
- `Dataset.validate_ready()`는 매출과 비용 파일만 요구하며 온라인 매출 파일은 선택으로 유지한다.
- 파일 유형과 사업장·데이터셋 스냅샷은 DB 유일 제약으로 보호하고, 진단은 사업·공개 데이터 스냅샷을 근거로 명시한다.
- Enum은 PostgreSQL native enum 대신 문자열 컬럼과 `CheckConstraint`로 저장한다.

## Task 2 검증 기록

- 도메인 모델 부재로 테스트 수집이 실패하는 RED를 확인했다.
- 사업 데이터와 진단 타깃 테스트 13개, 당시 전체 테스트 20개가 통과했다.

## Task 3 구현 결정과 검증

- 대출 조건과 재무 계산 결과는 각각 `Simulation`, `Scenario` 컬럼에 composite 값 객체로 매핑한다.
- 시나리오는 A·B·C와 네 고정 카테고리, 최소 5%, 비율 100%, 금액 합계를 검증한다.
- 선택은 집행 등록 시 잠기며 실제 집행금액과 미집행금액의 합은 대출금액과 같아야 한다.
- 모델 부재 RED 후 타깃 테스트 7개, 당시 전체 테스트 27개가 통과했다.

## Task 4 구현 결정과 검증

- 결과 비교는 시뮬레이션과 실제 또는 Mock 집행, 관측 데이터가 모두 일치할 때만 유효하다.
- 비교 지표는 목표값, 손익분기값, 관측값만 저장하고 예측값 필드는 두지 않는다.
- 재평가 스냅샷은 최신 사업 스냅샷과 해결·잔존·신규 병목 변화를 소유한다.
- 모델 부재 RED 후 타깃 테스트 5개, 당시 전체 테스트 32개가 통과했다.

## Task 5 구현 결정과 검증

- Alembic 자동 생성 결과를 초기 마이그레이션으로 고정하고 이후 스키마 변경도 Alembic만 사용한다.
- CI는 PostgreSQL 15 격리 서비스를 사용하며 원격 Supabase에는 연결하지 않는다.
- 로컬 환경에는 Docker가 없어 임시 PostgreSQL 14 서버에서 동일 DDL을 검증하고, CI에서 PostgreSQL 15를 재검증한다.
- 마이그레이션 부재로 RED를 확인한 뒤 24개 테이블 생성과 upgrade, downgrade, re-upgrade 통합 테스트가 통과했다.
- `TEST_DATABASE_URL`을 지정한 전체 pytest 34개, Alembic drift 검사, Ruff 검사와 포맷 검사가 통과했다.
