# PostgreSQL에서 Alembic 초기 스키마의 업그레이드와 롤백을 검증하는 통합 테스트
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

import app.domain  # noqa: F401
from app.db.base import Base

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
BACKEND_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="격리된 PostgreSQL TEST_DATABASE_URL이 필요합니다.",
)


def run_alembic(command: str) -> None:
    environment = os.environ | {
        "BACKEND_MIGRATION_DATABASE_URL": TEST_DATABASE_URL,
    }
    subprocess.run(
        ["alembic", "-c", "alembic.ini", *command.split()],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def reset_schema() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def test_initial_migration_upgrades_downgrades_and_reupgrades() -> None:
    reset_schema()
    engine = create_engine(TEST_DATABASE_URL)

    run_alembic("upgrade head")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert tables >= set(Base.metadata.tables)
    assert "demo_sessions" in tables
    assert "users" not in tables
    assert "demo_session_id" in {column["name"] for column in inspector.get_columns("businesses")}

    run_alembic("downgrade base")
    assert not set(Base.metadata.tables) & set(inspect(engine).get_table_names())

    run_alembic("upgrade head")
    assert set(inspect(engine).get_table_names()) >= set(Base.metadata.tables)
    engine.dispose()


def test_demo_session_migration_preserves_existing_business() -> None:
    reset_schema()
    run_alembic("upgrade 20260730_0001")
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        business_id = connection.execute(
            text(
                """
                INSERT INTO businesses (
                    name,
                    region,
                    industry,
                    employee_count,
                    primary_sales_channels
                )
                VALUES (
                    'Y카페',
                    '서울',
                    '카페',
                    0,
                    ARRAY[]::varchar[]
                )
                RETURNING id
                """
            )
        ).scalar_one()

    run_alembic("upgrade head")

    with engine.connect() as connection:
        demo_session_id = connection.execute(
            text(
                """
                SELECT demo_session_id
                FROM businesses
                WHERE id = :business_id
                """
            ),
            {"business_id": business_id},
        ).scalar_one()
        status = connection.execute(
            text(
                """
                SELECT status
                FROM demo_sessions
                WHERE id = :demo_session_id
                """
            ),
            {"demo_session_id": demo_session_id},
        ).scalar_one()

    assert demo_session_id is not None
    assert status == "expired"
    engine.dispose()
