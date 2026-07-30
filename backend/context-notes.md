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
