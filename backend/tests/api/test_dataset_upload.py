# 사업 데이터 xlsx 업로드와 처리 상태 조회 계약을 검증하는 테스트
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from uuid import UUID

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.db import session as db_session
from app.domain.business import Business
from app.domain.dataset import (
    Dataset,
    NormalizedExpense,
    NormalizedOnlineSale,
    NormalizedSale,
)
from app.domain.enums import DatasetStatus
from app.main import app

SESSION_ID = UUID("21ee64f2-0c95-4b55-a8c0-3943d36ef8f1")
OTHER_SESSION_ID = UUID("15e72615-d9e0-46d0-a4fa-33f5154d4447")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class FakeDatabaseSession:
    def __init__(self, business: Business) -> None:
        self.businesses = {business.id: business}
        self.datasets: dict[int, Dataset] = {}
        self.sales: list[NormalizedSale] = []
        self.expenses: list[NormalizedExpense] = []
        self.online_sales: list[NormalizedOnlineSale] = []
        self.get_calls: list[tuple[type, int]] = []
        self.next_dataset_id = 1
        self.next_file_id = 1

    @contextmanager
    def begin(self) -> Iterator[None]:
        yield

    def get(self, model: type, identifier: int) -> Business | Dataset | None:
        self.get_calls.append((model, identifier))
        if model is Business:
            return self.businesses.get(identifier)
        if model is Dataset:
            return self.datasets.get(identifier)
        raise AssertionError(f"지원하지 않는 모델 조회입니다: {model}")

    def add(self, instance: object) -> None:
        if isinstance(instance, Dataset):
            if instance.id is None:
                instance.id = self.next_dataset_id
                self.next_dataset_id += 1
            self.datasets[instance.id] = instance
        elif isinstance(instance, NormalizedSale):
            self.sales.append(instance)
        elif isinstance(instance, NormalizedExpense):
            self.expenses.append(instance)
        elif isinstance(instance, NormalizedOnlineSale):
            self.online_sales.append(instance)

    def flush(self) -> None:
        for dataset in self.datasets.values():
            for dataset_file in dataset.files:
                if dataset_file.id is None:
                    dataset_file.id = self.next_file_id
                    self.next_file_id += 1

    def close(self) -> None:
        pass


def create_business(session_id: UUID = SESSION_ID) -> Business:
    return Business(
        id=1,
        demo_session_id=session_id,
        name="Y카페",
        region="서울 마포구",
        industry="카페",
    )


def create_xlsx(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def sales_xlsx() -> bytes:
    return create_xlsx(
        ["영업일자", "총매출", "할인금액", "환불금액", "순매출", "결제수단"],
        [["2026-07-01", 120_000, 5_000, 0, 115_000, "카드"]],
    )


def expense_xlsx() -> bytes:
    return create_xlsx(
        ["거래일자", "거래처", "비용항목", "공급가액", "부가세", "합계금액"],
        [["2026-07-01", "원두상사", "재료비", 50_000, 5_000, 55_000]],
    )


def online_sales_xlsx() -> bytes:
    return create_xlsx(
        ["영업일자", "판매채널", "주문건수", "총주문금액", "매출금액", "정산금액"],
        [["2026-07-01", "배달앱", 3, 75_000, 70_000, 62_000]],
    )


def create_client(database: FakeDatabaseSession, session_id: UUID = SESSION_ID) -> TestClient:
    app.dependency_overrides.clear()
    client = TestClient(app)
    client.cookies.set("demo_session_id", str(session_id))
    return client


def upload_files(
    client: TestClient,
    *,
    sales_content: bytes | None = None,
    expense_content: bytes | None = None,
    online_sales_content: bytes | None = None,
    sales_filename: str = "sales.xlsx",
):
    files = {}
    if sales_content is not None:
        files["salesFile"] = (sales_filename, sales_content, XLSX_MEDIA_TYPE)
    if expense_content is not None:
        files["expenseFile"] = ("expenses.xlsx", expense_content, XLSX_MEDIA_TYPE)
    if online_sales_content is not None:
        files["onlineSalesFile"] = (
            "online-sales.xlsx",
            online_sales_content,
            XLSX_MEDIA_TYPE,
        )
    return client.post("/api/businesses/1/datasets", files=files)


def test_upload_required_files_returns_accepted_and_normalizes_rows(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)

    response = upload_files(
        client,
        sales_content=sales_xlsx(),
        expense_content=expense_xlsx(),
    )

    assert response.status_code == 202
    assert response.json() == {"datasetId": 1, "status": "uploaded"}
    assert database.datasets[1].status == DatasetStatus.READY
    assert len(database.datasets[1].files) == 2
    assert all(dataset_file.storage_path is None for dataset_file in database.datasets[1].files)
    assert len(database.sales) == 1
    assert database.sales[0].net_sales == 115_000
    assert len(database.expenses) == 1
    assert database.expenses[0].total_amount == 55_000
    assert database.online_sales == []


def test_upload_optional_online_sales_and_get_mapping_status(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)
    upload_files(
        client,
        sales_content=sales_xlsx(),
        expense_content=expense_xlsx(),
        online_sales_content=online_sales_xlsx(),
    )

    response = client.get("/api/datasets/1")

    assert response.status_code == 200
    body = response.json()
    assert body["datasetId"] == 1
    assert body["businessId"] == 1
    assert body["status"] == "ready"
    assert [file["fileType"] for file in body["files"]] == [
        "sale",
        "expense",
        "online_sale",
    ]
    assert body["files"][0]["columnMapping"]["영업일자"] == "businessDate"
    assert body["files"][0]["missingColumns"] == []
    assert 0 < body["files"][0]["mappingConfidence"] <= 1
    assert body["files"][0]["rowCount"] == 1
    assert len(database.online_sales) == 1


def test_upload_requires_expense_file(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)

    response = upload_files(client, sales_content=sales_xlsx())

    assert response.status_code == 422
    assert database.datasets == {}


def test_upload_rejects_non_xlsx_file(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)

    response = upload_files(
        client,
        sales_content=sales_xlsx(),
        expense_content=expense_xlsx(),
        sales_filename="sales.csv",
    )

    assert response.status_code == 400
    assert database.datasets == {}


def test_upload_marks_damaged_workbook_as_failed(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)

    response = upload_files(
        client,
        sales_content=b"not-an-xlsx",
        expense_content=expense_xlsx(),
    )

    assert response.status_code == 202
    assert database.datasets[1].status == DatasetStatus.FAILED
    status_response = client.get("/api/datasets/1")
    assert status_response.json()["status"] == "failed"


def test_upload_marks_missing_required_column_as_needs_reupload(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)
    missing_net_sales = create_xlsx(
        ["영업일자", "총매출"],
        [["2026-07-01", 120_000]],
    )

    response = upload_files(
        client,
        sales_content=missing_net_sales,
        expense_content=expense_xlsx(),
    )

    assert response.status_code == 202
    assert database.datasets[1].status == DatasetStatus.NEEDS_REUPLOAD
    status_response = client.get("/api/datasets/1")
    assert status_response.json()["files"][0]["missingColumns"] == ["netSales"]


def test_upload_marks_unknown_headers_as_needs_reupload(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)
    unknown_sales = create_xlsx(
        ["알수없는날짜", "알수없는금액"],
        [["2026-07-01", 120_000]],
    )

    response = upload_files(
        client,
        sales_content=unknown_sales,
        expense_content=expense_xlsx(),
    )

    assert response.status_code == 202
    assert database.datasets[1].status == DatasetStatus.NEEDS_REUPLOAD
    status_response = client.get("/api/datasets/1")
    assert status_response.json()["files"][0]["missingColumns"] == [
        "businessDate",
        "netSales",
    ]


def test_upload_marks_invalid_row_value_as_failed(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database)
    invalid_sales = create_xlsx(
        ["영업일자", "순매출"],
        [["not-a-date", 120_000]],
    )

    response = upload_files(
        client,
        sales_content=invalid_sales,
        expense_content=expense_xlsx(),
    )

    assert response.status_code == 202
    assert database.datasets[1].status == DatasetStatus.FAILED


def test_upload_hides_business_owned_by_another_session(monkeypatch) -> None:
    database = FakeDatabaseSession(create_business())
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database, OTHER_SESSION_ID)

    response = upload_files(
        client,
        sales_content=sales_xlsx(),
        expense_content=expense_xlsx(),
    )

    assert response.status_code == 404
    assert database.datasets == {}
    assert database.get_calls == [(Business, 1)]


def test_get_dataset_hides_resource_owned_by_another_session(monkeypatch) -> None:
    business = create_business()
    database = FakeDatabaseSession(business)
    dataset = Dataset(id=1, business=business, status=DatasetStatus.READY)
    database.datasets[1] = dataset
    monkeypatch.setattr(db_session, "SessionFactory", lambda: database)
    client = create_client(database, OTHER_SESSION_ID)

    response = client.get("/api/datasets/1")

    assert response.status_code == 404
    assert database.get_calls == [(Dataset, 1)]
