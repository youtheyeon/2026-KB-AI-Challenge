# Backend

Python 3.13과 FastAPI를 사용하는 KB AI Challenge 백엔드입니다.

## 요구 사항

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

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

## 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

기본 주소는 `http://127.0.0.1:8000`이며 상태 확인 API는 `GET /health`입니다.

## 검사

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
