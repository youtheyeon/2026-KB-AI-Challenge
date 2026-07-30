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
    assert set(inspect(engine).get_table_names()) >= set(Base.metadata.tables)

    run_alembic("downgrade base")
    assert not set(Base.metadata.tables) & set(inspect(engine).get_table_names())

    run_alembic("upgrade head")
    assert set(inspect(engine).get_table_names()) >= set(Base.metadata.tables)
    engine.dispose()
