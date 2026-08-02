# PostgreSQL에서 전체 도메인 메타데이터의 생성과 핵심 타입을 검증하는 통합 테스트
import os

import pytest
from sqlalchemy import BigInteger, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

import app.domain  # noqa: F401
from app.db.base import Base

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


def test_all_24_entities_create_on_postgresql() -> None:
    reset_schema()
    engine = create_engine(TEST_DATABASE_URL)

    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert len(Base.metadata.tables) == 24
    assert set(inspector.get_table_names()) == set(Base.metadata.tables)
    assert isinstance(Base.metadata.tables["demo_sessions"].c.id.type, PostgreSQLUUID)
    assert all(
        isinstance(table.c.id.type, BigInteger)
        for table in Base.metadata.sorted_tables
        if "id" in table.c and table.name != "demo_sessions"
    )
    engine.dispose()
