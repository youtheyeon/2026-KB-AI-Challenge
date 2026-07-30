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
