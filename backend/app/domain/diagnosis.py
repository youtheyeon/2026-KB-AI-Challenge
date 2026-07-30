# 사업 지표의 비교 근거와 병목 진단 결과를 저장하는 SQLAlchemy 모델
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, BigInteger, CheckConstraint, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import (
    BottleneckSeverity,
    DataSourceType,
    DiagnosisEvidenceSource,
    DiagnosisStatus,
)

if TYPE_CHECKING:
    from app.domain.business import Business
    from app.domain.dataset import BusinessSnapshot, Dataset, PublicDataSnapshot


def enum_type(enum_class: type, name: str, length: int) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        length=length,
    )


class Diagnosis(TimestampMixin, Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint(
            "evidence_source IN ('business_and_public_data')",
            name="ck_diagnosis_evidence_source",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="RESTRICT")
    )
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id", ondelete="RESTRICT"))
    business_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("business_snapshots.id", ondelete="RESTRICT")
    )
    public_data_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("public_data_snapshots.id", ondelete="RESTRICT")
    )
    status: Mapped[DiagnosisStatus] = mapped_column(
        enum_type(DiagnosisStatus, "diagnosis_status", 20),
        nullable=False,
        default=DiagnosisStatus.RUNNING,
    )
    evidence_source: Mapped[DiagnosisEvidenceSource] = mapped_column(
        enum_type(DiagnosisEvidenceSource, "diagnosis_evidence_source", 32),
        nullable=False,
    )
    diagnosis_version: Mapped[str | None] = mapped_column(String(100))
    benchmark_version: Mapped[str | None] = mapped_column(String(100))

    business: Mapped["Business | None"] = relationship(back_populates="diagnoses")
    dataset: Mapped["Dataset | None"] = relationship(back_populates="diagnoses")
    business_snapshot: Mapped["BusinessSnapshot"] = relationship(back_populates="diagnoses")
    public_data_snapshot: Mapped["PublicDataSnapshot"] = relationship(back_populates="diagnoses")
    metrics: Mapped[list["DiagnosisMetric"]] = relationship(
        back_populates="diagnosis", cascade="all, delete-orphan"
    )
    bottlenecks: Mapped[list["Bottleneck"]] = relationship(
        back_populates="diagnosis", cascade="all, delete-orphan"
    )


class DiagnosisMetric(Base):
    __tablename__ = "diagnosis_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id", ondelete="CASCADE"))
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    current_source_type: Mapped[DataSourceType] = mapped_column(
        enum_type(DataSourceType, "diagnosis_metric_current_source", 40), nullable=False
    )
    comparison_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    comparison_source_type: Mapped[DataSourceType] = mapped_column(
        enum_type(DataSourceType, "diagnosis_metric_comparison_source", 40), nullable=False
    )
    difference_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    benchmark_version: Mapped[str | None] = mapped_column(String(100))

    diagnosis: Mapped["Diagnosis"] = relationship(back_populates="metrics")


class Bottleneck(Base):
    __tablename__ = "bottlenecks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id", ondelete="CASCADE"))
    bottleneck_type: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[BottleneckSeverity] = mapped_column(
        enum_type(BottleneckSeverity, "bottleneck_severity", 20), nullable=False
    )
    evidence_source_type: Mapped[DataSourceType] = mapped_column(
        enum_type(DataSourceType, "bottleneck_evidence_source", 40), nullable=False
    )
    evidence_description: Mapped[str] = mapped_column(Text, nullable=False)
    related_categories: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), nullable=False, default=list
    )

    diagnosis: Mapped["Diagnosis"] = relationship(back_populates="bottlenecks")
