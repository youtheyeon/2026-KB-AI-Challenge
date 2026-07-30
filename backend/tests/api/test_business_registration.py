# 사업자 기본 정보 등록 API의 외부 계약을 검증하는 테스트
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.db import session as db_session
from app.domain.business import Business
from app.domain.demo_session import DemoSession
from app.main import app


class FakeDatabaseSession:
    def __init__(self) -> None:
        self.businesses: list[Business] = []
        self.demo_sessions: dict[UUID, DemoSession] = {}
        self.next_business_id = 1

    @contextmanager
    def begin(self) -> Iterator[None]:
        yield

    def add(self, instance: Business | DemoSession) -> None:
        if isinstance(instance, DemoSession):
            self.demo_sessions[instance.id] = instance
        else:
            self.businesses.append(instance)

    def flush(self) -> None:
        for business in self.businesses:
            if business.id is None:
                business.id = self.next_business_id
                self.next_business_id += 1

    def get(self, model: type[DemoSession], identifier: UUID) -> DemoSession | None:
        assert model is DemoSession
        return self.demo_sessions.get(identifier)

    def close(self) -> None:
        pass


def test_register_business_rejects_blank_required_value() -> None:
    response = TestClient(app).post(
        "/api/businesses",
        json={
            "name": "   ",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    assert response.status_code == 422


def test_register_business_returns_created_business(monkeypatch) -> None:
    database = FakeDatabaseSession()
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    response = TestClient(app).post(
        "/api/businesses",
        json={
            "name": " Y카페 ",
            "region": " 서울 마포구 ",
            "industry": " 카페 ",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "businessId": 1,
        "name": "Y카페",
        "region": "서울 마포구",
        "industry": "카페",
        "employeeCount": 0,
        "primarySalesChannels": [],
    }


def test_register_business_rejects_negative_employee_count(monkeypatch) -> None:
    database = FakeDatabaseSession()
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    response = TestClient(app).post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
            "employeeCount": -1,
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "가" * 151),
        ("region", "가" * 256),
        ("industry", "가" * 101),
        ("employeeCount", 2_147_483_648),
        ("primarySalesChannels", ["가" * 101]),
    ],
)
def test_register_business_rejects_values_larger_than_storage_limit(
    monkeypatch,
    field: str,
    value: int | str | list[str],
) -> None:
    database = FakeDatabaseSession()
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    payload = {
        "name": "Y카페",
        "region": "서울 마포구",
        "industry": "카페",
    }
    payload[field] = value

    response = TestClient(app).post("/api/businesses", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,maximum_length",
    [("name", 150), ("region", 255), ("industry", 100)],
)
def test_register_business_accepts_trimmed_value_at_storage_limit(
    monkeypatch,
    field: str,
    maximum_length: int,
) -> None:
    database = FakeDatabaseSession()
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    normalized_value = "가" * maximum_length
    payload = {
        "name": "Y카페",
        "region": "서울 마포구",
        "industry": "카페",
        field: f" {normalized_value} ",
    }

    response = TestClient(app).post("/api/businesses", json=payload)

    assert response.status_code == 201
    assert response.json()[field] == normalized_value


def test_register_business_creates_session_and_sets_cookie(monkeypatch) -> None:
    database = FakeDatabaseSession()
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    response = TestClient(app).post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    session_id = UUID(response.cookies["demo_session_id"])
    created_session = database.demo_sessions[session_id]

    assert created_session.status == "active"
    assert created_session.expires_at - created_session.last_accessed_at == timedelta(hours=24)
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert "Secure" not in response.headers["set-cookie"]


def test_register_business_sets_secure_cookie_in_production(monkeypatch) -> None:
    from app.core.config import settings

    database = FakeDatabaseSession()
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    monkeypatch.setattr(settings, "environment", "production")

    response = TestClient(app).post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    assert "Secure" in response.headers["set-cookie"]


def test_register_business_replaces_invalid_session_cookie(monkeypatch) -> None:
    database = FakeDatabaseSession()
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("demo_session_id", "not-a-uuid")
    response = client.post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    assert response.status_code == 201
    assert len(database.demo_sessions) == 1
    assert UUID(response.cookies["demo_session_id"]) in database.demo_sessions


def test_register_business_replaces_unknown_valid_session_cookie(monkeypatch) -> None:
    database = FakeDatabaseSession()
    unknown_session_id = UUID("fb1646d8-0529-4ea0-b970-832040340607")
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    client = TestClient(app)
    client.cookies.set("demo_session_id", str(unknown_session_id))
    response = client.post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    created_session_id = UUID(response.cookies["demo_session_id"])

    assert response.status_code == 201
    assert created_session_id != unknown_session_id
    assert set(database.demo_sessions) == {created_session_id}


def test_register_business_reuses_valid_demo_session(monkeypatch) -> None:
    database = FakeDatabaseSession()
    session_id = UUID("a7f6c4b5-9ea7-43a3-8c35-2fbfcacbda89")
    previous_access = datetime(2026, 7, 30, tzinfo=UTC)
    database.demo_sessions[session_id] = DemoSession(
        id=session_id,
        last_accessed_at=previous_access,
        expires_at=datetime(2026, 8, 1, tzinfo=UTC),
        status="active",
    )
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    client = TestClient(app)
    client.cookies.set("demo_session_id", str(session_id))
    response = client.post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    assert response.status_code == 201
    assert len(database.demo_sessions) == 1
    assert database.businesses[0].demo_session_id == session_id
    assert database.demo_sessions[session_id].last_accessed_at > previous_access
    assert "set-cookie" not in response.headers


def test_register_business_expires_stale_active_session(monkeypatch) -> None:
    database = FakeDatabaseSession()
    expired_session_id = UUID("29d78009-70a2-4f46-98b5-2d9429ee3639")
    database.demo_sessions[expired_session_id] = DemoSession(
        id=expired_session_id,
        last_accessed_at=datetime(2026, 7, 29, tzinfo=UTC),
        expires_at=datetime(2026, 7, 30, tzinfo=UTC),
        status="active",
    )
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    client = TestClient(app)
    client.cookies.set("demo_session_id", str(expired_session_id))
    response = client.post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    assert response.status_code == 201
    assert database.demo_sessions[expired_session_id].status == "expired"
    assert len(database.demo_sessions) == 2
    assert database.businesses[0].demo_session_id != expired_session_id


def test_register_business_replaces_inactive_session_before_expiry(monkeypatch) -> None:
    database = FakeDatabaseSession()
    inactive_session_id = UUID("ef35ab42-e307-4a9b-967b-656d8f372f80")
    database.demo_sessions[inactive_session_id] = DemoSession(
        id=inactive_session_id,
        last_accessed_at=datetime(2026, 7, 30, tzinfo=UTC),
        expires_at=datetime(2026, 8, 1, tzinfo=UTC),
        status="expired",
    )
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)

    client = TestClient(app)
    client.cookies.set("demo_session_id", str(inactive_session_id))
    response = client.post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
        },
    )

    assert response.status_code == 201
    assert len(database.demo_sessions) == 2
    assert database.businesses[0].demo_session_id != inactive_session_id
