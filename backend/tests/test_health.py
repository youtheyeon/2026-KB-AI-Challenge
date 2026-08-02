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
