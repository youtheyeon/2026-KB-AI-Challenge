# PostgreSQL에서 사업자 등록 API의 저장과 트랜잭션 원자성을 검증하는 통합 테스트
import os
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.domain  # noqa: F401
from app.db import session as db_session
from app.db.base import Base
from app.domain.business import Business
from app.domain.demo_session import DemoSession
from app.domain.enums import DemoSessionStatus
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="격리된 PostgreSQL TEST_DATABASE_URL이 필요합니다.",
)


def reset_schema() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    reset_schema()
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_register_business_commits_session_and_business_to_postgresql(
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
) -> None:
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False),
    )

    response = TestClient(app).post(
        "/api/businesses",
        json={
            "name": "Y카페",
            "region": "서울 마포구",
            "industry": "카페",
            "employeeCount": 3,
            "primarySalesChannels": ["매장", "배달"],
        },
    )

    assert response.status_code == 201
    with Session(postgres_engine) as database:
        business = database.scalar(select(Business))
        demo_session = database.scalar(select(DemoSession))

    assert business is not None
    assert demo_session is not None
    assert isinstance(business.demo_session_id, UUID)
    assert business.demo_session_id == demo_session.id
    assert business.primary_sales_channels == ["매장", "배달"]
    assert demo_session.status is DemoSessionStatus.ACTIVE


def test_register_business_rolls_back_session_when_business_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
) -> None:
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False),
    )

    def fail_business_insert(*_: object) -> None:
        raise RuntimeError("의도적인 business insert 실패")

    event.listen(Business, "before_insert", fail_business_insert)
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/businesses",
            json={
                "name": "Y카페",
                "region": "서울 마포구",
                "industry": "카페",
            },
        )
    finally:
        event.remove(Business, "before_insert", fail_business_insert)

    assert response.status_code == 500
    with Session(postgres_engine) as database:
        assert database.scalar(select(func.count()).select_from(DemoSession)) == 0
        assert database.scalar(select(func.count()).select_from(Business)) == 0
