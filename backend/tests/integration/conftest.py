# 모든 PostgreSQL 통합 테스트 전에 파괴적 스키마 초기화 대상을 검증하는 픽스처
import os

import pytest
from database_guard import validate_destructive_test_database


@pytest.fixture(autouse=True)
def require_isolated_test_database() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        return

    try:
        validate_destructive_test_database(
            database_url,
            reset_opt_in=os.getenv("ALLOW_DESTRUCTIVE_TEST_DATABASE_RESET"),
        )
    except ValueError as error:
        pytest.fail(str(error), pytrace=False)
