# 파괴적 PostgreSQL 통합 테스트가 격리된 테스트 DB에서만 실행되는지 검증하는 테스트
import pytest
from database_guard import validate_destructive_test_database


def test_database_guard_requires_explicit_reset_opt_in() -> None:
    with pytest.raises(ValueError, match="ALLOW_DESTRUCTIVE_TEST_DATABASE_RESET=1"):
        validate_destructive_test_database(
            "postgresql+psycopg://postgres@localhost/kb_domain_test",
            reset_opt_in=None,
        )


def test_database_guard_rejects_non_test_database_name() -> None:
    with pytest.raises(ValueError, match="_test"):
        validate_destructive_test_database(
            "postgresql+psycopg://postgres@localhost/postgres",
            reset_opt_in="1",
        )


def test_database_guard_accepts_explicit_isolated_test_database() -> None:
    validate_destructive_test_database(
        "postgresql+psycopg://postgres@localhost/kb_domain_test",
        reset_opt_in="1",
    )
