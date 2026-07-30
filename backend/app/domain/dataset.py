# 업로드 파일과 표준화된 매출·비용·온라인 데이터를 저장하는 SQLAlchemy 모델
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import (
    DatasetFileType,
    DatasetFormat,
    DatasetStatus,
    DataSourceType,
    ExpenseCategory,
    OnlineSalesReconciliationType,
)

if TYPE_CHECKING:
    from app.domain.business import Business
    from app.domain.diagnosis import Diagnosis


def string_enum(enum_type: type, name: str, length: int = 50) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        length=length,
    )


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="RESTRICT")
    )
    status: Mapped[DatasetStatus] = mapped_column(
        string_enum(DatasetStatus, "dataset_status", 20),
        nullable=False,
        default=DatasetStatus.UPLOADED,
    )
    dataset_version: Mapped[str | None] = mapped_column(String(100))

    business: Mapped["Business | None"] = relationship(back_populates="datasets")
    files: Mapped[list["DatasetFile"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    sales: Mapped[list["NormalizedSale"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["NormalizedExpense"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    online_sales: Mapped[list["NormalizedOnlineSale"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["BusinessSnapshot"]] = relationship(back_populates="dataset")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="dataset")

    def validate_ready(self) -> None:
        types = {file.file_type for file in self.files}
        if DatasetFileType.SALE not in types:
            raise ValueError("매출 파일이 필요합니다.")
        if DatasetFileType.EXPENSE not in types:
            raise ValueError("비용 파일이 필요합니다.")


class DatasetFile(TimestampMixin, Base):
    __tablename__ = "dataset_files"
    __table_args__ = (UniqueConstraint("dataset_id", "file_type", name="uq_dataset_file_type"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    file_type: Mapped[DatasetFileType] = mapped_column(
        string_enum(DatasetFileType, "dataset_file_type", 20), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    detected_format: Mapped[DatasetFormat] = mapped_column(
        string_enum(DatasetFormat, "dataset_format", 40),
        nullable=False,
        default=DatasetFormat.UNKNOWN,
    )
    source_type: Mapped[DataSourceType] = mapped_column(
        string_enum(DataSourceType, "dataset_file_source_type", 40),
        nullable=False,
        default=DataSourceType.USER_INPUT,
    )
    file_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    dataset: Mapped["Dataset | None"] = relationship(back_populates="files")


class NormalizedSale(TimestampMixin, Base):
    __tablename__ = "normalized_sales"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_files.id", ondelete="RESTRICT")
    )
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    receipt_number: Mapped[str | None] = mapped_column(String(100))
    pos_number: Mapped[str | None] = mapped_column(String(100))
    gross_sales: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    refund_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    net_sales: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    payment_method: Mapped[str | None] = mapped_column(String(100))
    transaction_status: Mapped[str | None] = mapped_column(String(100))

    dataset: Mapped["Dataset"] = relationship(back_populates="sales")


class NormalizedExpense(TimestampMixin, Base):
    __tablename__ = "normalized_expenses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_files.id", ondelete="RESTRICT")
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    expense_category: Mapped[ExpenseCategory] = mapped_column(
        string_enum(ExpenseCategory, "expense_category", 30), nullable=False
    )
    supply_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    vat_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_exempt_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(100))
    evidence_type: Mapped[str | None] = mapped_column(String(100))

    dataset: Mapped["Dataset"] = relationship(back_populates="expenses")


class NormalizedOnlineSale(TimestampMixin, Base):
    __tablename__ = "normalized_online_sales"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_files.id", ondelete="RESTRICT")
    )
    business_date: Mapped[date | None] = mapped_column(Date)
    sales_channel: Mapped[str | None] = mapped_column(String(100))
    order_type: Mapped[str | None] = mapped_column(String(100))
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    gross_order_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sales_amount: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    discount_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    refund_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    platform_fee_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    payment_fee_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    merchant_delivery_fee: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    settlement_amount: Mapped[int | None] = mapped_column(BigInteger)
    settlement_date: Mapped[date | None] = mapped_column(Date)
    settlement_status: Mapped[str | None] = mapped_column(String(100))
    reconciliation_type: Mapped[OnlineSalesReconciliationType] = mapped_column(
        string_enum(
            OnlineSalesReconciliationType,
            "online_sales_reconciliation_type",
            40,
        ),
        nullable=False,
        default=OnlineSalesReconciliationType.INCLUDED_IN_POS_TOTAL,
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="online_sales")


class PublicDataSnapshot(TimestampMixin, Base):
    __tablename__ = "public_data_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="RESTRICT"))
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    snapshot_version: Mapped[str] = mapped_column(String(100), nullable=False)
    reference_area: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    business: Mapped["Business"] = relationship(back_populates="public_data_snapshots")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="public_data_snapshot")


class BusinessSnapshot(TimestampMixin, Base):
    __tablename__ = "business_snapshots"
    __table_args__ = (
        UniqueConstraint("business_id", "dataset_id", name="uq_business_dataset_snapshot"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="RESTRICT"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="RESTRICT"))
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    snapshot_version: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_net_sales_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monthly_expense_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    existing_monthly_repayment_amount: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    contribution_margin_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    average_order_amount: Mapped[int | None] = mapped_column(BigInteger)
    monthly_order_count: Mapped[int | None] = mapped_column(Integer)
    online_sales_ratio: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[DataSourceType] = mapped_column(
        string_enum(DataSourceType, "business_snapshot_source_type", 40), nullable=False
    )

    business: Mapped["Business"] = relationship(back_populates="snapshots")
    dataset: Mapped["Dataset"] = relationship(back_populates="snapshots")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="business_snapshot")
