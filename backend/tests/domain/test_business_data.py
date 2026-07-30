# 사업 데이터 SQLAlchemy 모델의 정규화와 무결성 제약을 검증하는 테스트
from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.domain.business import Business
from app.domain.dataset import (
    Dataset,
    DatasetFile,
    NormalizedOnlineSale,
    PublicDataSnapshot,
)
from app.domain.enums import DatasetFileType
from app.domain.user import User


def test_user_normalizes_email_before_persistence() -> None:
    user = User(email="  Owner@Example.COM ")

    assert user.email == "owner@example.com"


def test_business_requires_non_empty_profile_fields() -> None:
    try:
        Business(name="", region="서울 마포구", industry="음식점")
    except ValueError as error:
        assert str(error) == "사업장명은 필수입니다."
    else:
        raise AssertionError("빈 사업장명은 허용되면 안 됩니다.")


def test_dataset_file_type_is_unique_within_a_dataset() -> None:
    constraints = DatasetFile.__table__.constraints

    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns) == ("dataset_id", "file_type")
        for constraint in constraints
    )


def test_normalized_online_sale_has_consistent_zero_defaults() -> None:
    columns = NormalizedOnlineSale.__table__.c

    assert columns.sales_amount.default.arg == 0
    assert columns.order_count.default.arg == 0
    assert columns.sales_amount.server_default.arg == "0"
    assert columns.order_count.server_default.arg == "0"


def test_dataset_requires_sales_and_expense_files_but_not_online_sale() -> None:
    dataset = Dataset(
        files=[
            DatasetFile(file_type=DatasetFileType.SALE, original_filename="sales.csv"),
            DatasetFile(file_type=DatasetFileType.EXPENSE, original_filename="expenses.csv"),
        ]
    )

    dataset.validate_ready()


def test_dataset_rejects_missing_required_file_type() -> None:
    dataset = Dataset(
        files=[DatasetFile(file_type=DatasetFileType.SALE, original_filename="sales.csv")]
    )

    try:
        dataset.validate_ready()
    except ValueError as error:
        assert str(error) == "비용 파일이 필요합니다."
    else:
        raise AssertionError("비용 파일 누락은 허용되면 안 됩니다.")


def test_public_raw_data_and_file_metadata_use_postgresql_jsonb() -> None:
    assert isinstance(PublicDataSnapshot.__table__.c.raw_data.type, JSONB)
    assert isinstance(DatasetFile.__table__.c.file_metadata.type, JSONB)


def test_business_data_entities_use_bigint_primary_keys() -> None:
    for model in (User, Business, Dataset, DatasetFile, NormalizedOnlineSale, PublicDataSnapshot):
        assert isinstance(model.__table__.c.id.type, BigInteger)
