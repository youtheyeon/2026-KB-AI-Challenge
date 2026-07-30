# FastAPI Backend Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 Java·Spring 백엔드 자리를 Python 3.13과 FastAPI 기반의 실행·테스트·CI 가능한 최소 백엔드로 교체한다.

**Architecture:** `app.main`이 FastAPI 애플리케이션을 조립하고, 환경설정은 `app.core.config`, 헬스 체크 라우트는 `app.api.routes.health`가 담당한다. 패키지와 가상환경은 uv로 관리하고 pytest와 Ruff를 로컬 및 GitHub Actions에서 동일하게 실행한다.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, Pydantic Settings, uv, pytest, HTTPX2, Ruff, GitHub Actions.

## Global Constraints

- 브랜치는 `feat/20`을 사용한다.
- 구현 완료 후 사용자의 후속 요청에 따라 변경사항을 네 개의 의미 단위 커밋으로 나눈다.
- 새 Python 소스 파일 첫 줄에는 파일 역할을 설명하는 한국어 주석을 작성한다.
- 데이터베이스, 인증, 비즈니스 API, 실제 AI 모델 연동은 이번 작업에 포함하지 않는다.
- 공개 동작은 `GET /health`가 HTTP 200과 `{"status": "ok"}`를 반환하는 것까지로 제한한다.
- Python 기준 버전은 AI 라이브러리 호환성을 고려해 3.13으로 고정한다.

---

### Task 1: Python 프로젝트와 헬스 체크 API

**Files:**
- Create: `backend/.gitignore`
- Create: `backend/.python-version`
- Create: `backend/.env.example`
- Create: `backend/pyproject.toml`
- Create: `backend/tests/test_health.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`

**Interfaces:**
- Consumes: `BACKEND_APP_NAME` 환경변수.
- Produces: `app.main:app`, `GET /health`, `HealthResponse(status: Literal["ok"])`.

- [x] **Step 1: Python 프로젝트 설정 작성**

```toml
[project]
name = "kb-ai-challenge-backend"
version = "0.1.0"
description = "KB AI Challenge FastAPI backend"
requires-python = ">=3.13,<3.15"
dependencies = [
    "fastapi>=0.139.0,<1.0",
    "pydantic-settings>=2.12.0,<3.0",
    "uvicorn[standard]>=0.40.0,<1.0",
]

[dependency-groups]
dev = [
    "httpx2>=2.7.0,<3.0",
    "pytest>=9.0.2,<10.0",
    "ruff>=0.16.0,<1.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["B", "E", "F", "I", "UP"]
```

`backend/.python-version`에는 `3.13`을 작성하고, `backend/.gitignore`에는 `.venv`, Python 캐시, pytest/Ruff 캐시, `.env`를 제외하도록 작성한다.

- [x] **Step 2: 실패하는 헬스 체크 테스트 작성**

```python
# FastAPI 애플리케이션의 기본 상태 확인 API를 검증하는 테스트
import pytest


def test_health_endpoint_returns_ok() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_application_uses_default_name() -> None:
    from app.main import app

    assert app.title == "KB AI Challenge API"


def test_settings_reads_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("BACKEND_APP_NAME", "Configured API")

    assert Settings().app_name == "Configured API"
```

- [x] **Step 3: 테스트가 예상한 이유로 실패하는지 확인**

Run: `cd backend && uv run pytest tests/test_health.py -v`

Expected: `ModuleNotFoundError: No module named 'app.main'` 때문에 실패한다.

- [x] **Step 4: 최소 FastAPI 애플리케이션 구현**

```python
# 백엔드 애플리케이션 환경설정을 정의하는 모듈
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KB AI Challenge API"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BACKEND_",
        extra="ignore",
    )


settings = Settings()
```

```python
# 백엔드 상태 확인 API를 제공하는 라우터
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(status="ok")
```

```python
# FastAPI 애플리케이션을 생성하고 API 라우터를 조립하는 진입점
from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(health_router)
```

각 `__init__.py` 첫 줄에도 해당 패키지 역할을 설명하는 한국어 주석을 작성한다.

- [x] **Step 5: 헬스 체크 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_health.py -v`

Expected: `3 passed`.

- [x] **Step 6: 애플리케이션 변경 분리 준비**

Python 프로젝트 설정과 FastAPI 애플리케이션 변경을 각각 독립 커밋으로 나눌 수 있도록 파일 책임을 분리한다.

### Task 2: Python Backend CI와 개발 문서

**Files:**
- Modify: `.github/workflows/backend-ci.yml`
- Create: `backend/README.md`
- Create: `backend/uv.lock`

**Interfaces:**
- Consumes: `backend/pyproject.toml`, `backend/app.main:app`.
- Produces: `uv sync --locked`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`를 실행하는 CI와 동일한 로컬 명령.

- [x] **Step 1: uv 잠금 파일 생성**

Run: `cd backend && uv lock`

Expected: `backend/uv.lock`이 생성되고 의존성 해석이 성공한다.

- [x] **Step 2: Java·Gradle CI를 Python·uv CI로 교체**

```yaml
name: Backend CI

on:
  pull_request:
    paths:
      - 'backend/**'
      - '.github/workflows/backend-ci.yml'

  push:
    branches:
      - develop
    paths:
      - 'backend/**'
      - '.github/workflows/backend-ci.yml'

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: backend

    steps:
      - name: Checkout
        uses: actions/checkout@v7

      - name: Install uv and Python
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
        with:
          python-version: '3.13'
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --dev

      - name: Lint
        run: uv run ruff check .

      - name: Check formatting
        run: uv run ruff format --check .

      - name: Test
        run: uv run pytest
```

- [x] **Step 3: 로컬 개발 문서 작성**

`backend/README.md`에 요구 Python 버전, uv 설치 전제, `uv sync --dev`, `uv run uvicorn app.main:app --reload`, `uv run pytest`, Ruff 검사 명령, `BACKEND_APP_NAME` 환경변수를 설명한다.

- [x] **Step 4: 전체 검증**

Run: `cd backend && uv sync --locked --dev`

Expected: 잠금 파일 변경 없이 개발 의존성 설치에 성공한다.

Run: `cd backend && uv run ruff check .`

Expected: 린트 오류 없이 종료 코드 0을 반환한다.

Run: `cd backend && uv run ruff format --check .`

Expected: 포맷 변경이 필요하지 않고 종료 코드 0을 반환한다.

Run: `cd backend && uv run pytest`

Expected: 모든 테스트가 통과한다.

Run: `git diff --check`

Expected: 공백 오류 없이 종료 코드 0을 반환한다.

- [x] **Step 5: CI와 문서 변경 분리 준비**

Backend CI와 개발 문서를 각각 독립 커밋으로 나눈다.
