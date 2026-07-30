# 파괴적 통합 테스트에 사용할 PostgreSQL 주소와 명시적 실행 동의를 검증하는 모듈
from sqlalchemy.engine import make_url


def validate_destructive_test_database(
    database_url: str,
    *,
    reset_opt_in: str | None,
) -> None:
    if reset_opt_in != "1":
        raise ValueError(
            "통합 테스트의 스키마 초기화에는 "
            "ALLOW_DESTRUCTIVE_TEST_DATABASE_RESET=1 설정이 필요합니다."
        )

    database_name = make_url(database_url).database
    if database_name is None or not database_name.lower().endswith("_test"):
        raise ValueError("TEST_DATABASE_URL의 데이터베이스 이름은 _test로 끝나야 합니다.")
