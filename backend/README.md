# Backend

Python 3.13과 FastAPI를 사용하는 KB AI Challenge 백엔드입니다.

## 요구 사항

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 15 이상

uv가 설치되어 있으면 프로젝트에 필요한 Python과 패키지를 자동으로 준비할 수 있습니다.

## 개발 환경 준비

```bash
uv sync --locked --dev
```

환경변수를 파일로 관리하려면 예시 파일을 복사해 사용합니다.

```bash
cp .env.example .env
```

지원하는 환경변수는 다음과 같습니다.

- `BACKEND_APP_NAME`은 OpenAPI 문서에 표시할 애플리케이션 이름입니다.
- `BACKEND_DATABASE_URL`은 FastAPI 런타임의 PostgreSQL 연결 주소입니다.
- `BACKEND_MIGRATION_DATABASE_URL`은 Alembic이 사용하는 직접 연결 주소입니다.

로컬 PostgreSQL은 다음 명령으로 실행할 수 있습니다.

```bash
docker compose up -d postgres
uv run alembic upgrade head
```

Supabase에서는 런타임 서버의 네트워크 환경에 따라 직접 연결 또는 세션 풀러 주소를
`BACKEND_DATABASE_URL`로 사용합니다. 마이그레이션에는 Supabase의 직접 연결 주소를
`BACKEND_MIGRATION_DATABASE_URL`로 사용합니다. 실제 비밀번호가 포함된 연결 문자열은
`.env`에만 저장합니다.

## 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

기본 주소는 `http://127.0.0.1:8000`이며 상태 확인 API는 `GET /health`입니다.

## 사업 상태 분석 및 병목 진단 API

컬럼 매핑이 끝나 `READY` 상태인 데이터셋은 다음 API로 진단할 수 있습니다.

```http
POST /api/businesses/{businessId}/diagnoses
Content-Type: application/json

{"datasetId": 1}
```

POST 요청은 진단 레코드와 입력·공공데이터 스냅샷을 저장한 뒤 즉시 `202 RUNNING`을
반환합니다. 계산은 FastAPI `BackgroundTasks`에서 이어서 수행하며 결과는 다음 API로
조회합니다.

```http
GET /api/diagnoses/{diagnosisId}
```

계산 중에는 `RUNNING`, 성공하면 `COMPLETED`, 실패하면 `FAILED`를 반환합니다.
`RUNNING`과 `FAILED`에서는 지표와 병목 필드가 `null`입니다. 현재 캐시된 공공데이터에
유동인구가 없으므로 완료 응답의 `floatingPopulationGrowthRate`도 `null`입니다.

`BackgroundTasks`는 별도 작업 큐가 아니므로 프로세스가 재시작되면 실행 중인 작업이
유실될 수 있습니다. 단일 EC2 프로세스용 초기 구현이며, 다중 인스턴스나 재시작 복구가
필요해지면 외부 작업 큐와 재시도 정책으로 교체해야 합니다.

## 검사

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

PostgreSQL 통합 테스트를 포함하려면 격리된 테스트 DB 주소를 지정합니다.
통합 테스트는 `public` 스키마를 초기화하므로 데이터베이스 이름이 `_test`로 끝나야 하고
파괴적 초기화 동의를 명시해야 합니다.

```bash
ALLOW_DESTRUCTIVE_TEST_DATABASE_RESET=1 \
TEST_DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/kb_ai_challenge_test \
  uv run pytest
```

운영 또는 공유 DB 주소는 `TEST_DATABASE_URL`에 사용하지 않습니다.
