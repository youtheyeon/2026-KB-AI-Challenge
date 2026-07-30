# PostgreSQL에서 데이터셋 업로드 저장과 트랜잭션 원자성을 검증하는 통합 테스트
import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.domain  # noqa: F401
from app.db import session as db_session
from app.db.base import Base
from app.domain.business import Business
from app.domain.dataset import (
    Dataset,
    DatasetFile,
    NormalizedExpense,
    NormalizedOnlineSale,
    NormalizedSale,
)
from app.domain.demo_session import DemoSession
from app.domain.enums import DatasetStatus, DemoSessionStatus
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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


def create_xlsx(headers: list[str], row: list[object]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    worksheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def create_business(postgres_engine: Engine) -> tuple[int, str]:
    now = datetime.now(UTC)
    session_id = uuid4()
    with Session(postgres_engine) as database, database.begin():
        demo_session = DemoSession(
            id=session_id,
            last_accessed_at=now,
            expires_at=now + timedelta(hours=24),
            status=DemoSessionStatus.ACTIVE,
        )
        business = Business(
            demo_session=demo_session,
            name="Y카페",
            region="서울 마포구",
            industry="카페",
        )
        database.add(business)
        database.flush()
        business_id = business.id
    return business_id, str(session_id)


def upload_all_files(client: TestClient, business_id: int):
    return client.post(
        f"/api/businesses/{business_id}/datasets",
        files={
            "salesFile": (
                "sales.xlsx",
                create_xlsx(
                    ["영업일자", "순매출"],
                    ["2026-07-01", 115_000],
                ),
                XLSX_MEDIA_TYPE,
            ),
            "expenseFile": (
                "expenses.xlsx",
                create_xlsx(
                    ["거래일자", "비용항목", "합계금액"],
                    ["2026-07-01", "재료비", 55_000],
                ),
                XLSX_MEDIA_TYPE,
            ),
            "onlineSalesFile": (
                "online-sales.xlsx",
                create_xlsx(
                    ["영업일자", "매출금액"],
                    ["2026-07-01", 70_000],
                ),
                XLSX_MEDIA_TYPE,
            ),
        },
    )


def test_upload_persists_metadata_and_normalized_rows_to_postgresql(
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
) -> None:
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False),
    )
    business_id, session_id = create_business(postgres_engine)
    client = TestClient(app)
    client.cookies.set("demo_session_id", session_id)

    response = upload_all_files(client, business_id)

    assert response.status_code == 202
    with Session(postgres_engine) as database:
        dataset = database.scalar(select(Dataset))
        dataset_file = database.scalar(select(DatasetFile))
        sale_count = database.scalar(select(func.count()).select_from(NormalizedSale))
        expense_count = database.scalar(select(func.count()).select_from(NormalizedExpense))
        online_count = database.scalar(select(func.count()).select_from(NormalizedOnlineSale))

    assert dataset is not None
    assert dataset.status is DatasetStatus.READY
    assert dataset_file is not None
    assert dataset_file.storage_path is None
    assert dataset_file.file_metadata["rowCount"] == 1
    assert sale_count == 1
    assert expense_count == 1
    assert online_count == 1


def test_upload_rolls_back_dataset_when_file_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
    postgres_engine: Engine,
) -> None:
    monkeypatch.setattr(
        db_session,
        "SessionFactory",
        sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False),
    )
    business_id, session_id = create_business(postgres_engine)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("demo_session_id", session_id)

    def fail_file_insert(*_: object) -> None:
        raise RuntimeError("의도적인 dataset file insert 실패")

    event.listen(DatasetFile, "before_insert", fail_file_insert)
    try:
        response = upload_all_files(client, business_id)
    finally:
        event.remove(DatasetFile, "before_insert", fail_file_insert)

    assert response.status_code == 500
    with Session(postgres_engine) as database:
        assert database.scalar(select(func.count()).select_from(Dataset)) == 0
        assert database.scalar(select(func.count()).select_from(DatasetFile)) == 0
