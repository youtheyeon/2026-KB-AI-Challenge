# 집행 후 관측 결과와 해결·잔존·신규 병목을 저장하는 SQLAlchemy 모델
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import (
    BottleneckChangeType,
    DataSourceType,
    OutcomeStatus,
)


def enum_type(enum_class: type, name: str, length: int) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        length=length,
    )


class OutcomeData(TimestampMixin, Base):
    __tablename__ = "outcome_data"
    __table_args__ = (UniqueConstraint("simulation_id", name="uq_outcome_data_simulation"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id", ondelete="RESTRICT"))
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id", ondelete="RESTRICT"))
    observed_business_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("business_snapshots.id", ondelete="RESTRICT")
    )
    source_type: Mapped[DataSourceType] = mapped_column(
        enum_type(DataSourceType, "outcome_data_source", 40),
        nullable=False,
        default=DataSourceType.USER_INPUT,
    )
    observed_at: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ready")

    simulation: Mapped["Simulation"] = relationship()
    dataset: Mapped["Dataset | None"] = relationship()
    observed_business_snapshot: Mapped["BusinessSnapshot"] = relationship()

    def validate_business(
        self,
        simulation_business_id: int,
        snapshot_business_id: int,
        dataset_business_id: int | None,
    ) -> None:
        if snapshot_business_id != simulation_business_id or (
            dataset_business_id is not None and dataset_business_id != simulation_business_id
        ):
            raise ValueError("관측 데이터는 시뮬레이션과 같은 사업체에 속해야 합니다.")


class OutcomeComparison(TimestampMixin, Base):
    __tablename__ = "outcome_comparisons"
    __table_args__ = (
        UniqueConstraint("simulation_id", name="uq_outcome_comparison_simulation"),
        UniqueConstraint("execution_id", name="uq_outcome_comparison_execution"),
        UniqueConstraint("outcome_data_id", name="uq_outcome_comparison_data"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id", ondelete="RESTRICT"))
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id", ondelete="RESTRICT"))
    outcome_data_id: Mapped[int] = mapped_column(ForeignKey("outcome_data.id", ondelete="RESTRICT"))
    reassessment_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("reassessment_snapshots.id", ondelete="RESTRICT"), unique=True
    )
    status: Mapped[OutcomeStatus] = mapped_column(
        enum_type(OutcomeStatus, "outcome_status", 30), nullable=False
    )

    metrics: Mapped[list["OutcomeComparisonMetric"]] = relationship(
        back_populates="comparison", cascade="all, delete-orphan"
    )
    reassessment_snapshot: Mapped["ReassessmentSnapshot | None"] = relationship(
        cascade="all, delete-orphan", single_parent=True
    )

    def validate_sources(self, execution_simulation_id: int, outcome_simulation_id: int) -> None:
        if (
            execution_simulation_id != self.simulation_id
            or outcome_simulation_id != self.simulation_id
        ):
            raise ValueError("집행과 관측 데이터는 같은 시뮬레이션에 속해야 합니다.")


class OutcomeComparisonMetric(Base):
    __tablename__ = "outcome_comparison_metrics"
    __table_args__ = (
        UniqueConstraint("comparison_id", "metric_code", name="uq_outcome_metric_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    comparison_id: Mapped[int] = mapped_column(
        ForeignKey("outcome_comparisons.id", ondelete="CASCADE")
    )
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    break_even_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[OutcomeStatus] = mapped_column(
        enum_type(OutcomeStatus, "outcome_metric_status", 30), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)

    comparison: Mapped["OutcomeComparison"] = relationship(back_populates="metrics")


class ReassessmentSnapshot(TimestampMixin, Base):
    __tablename__ = "reassessment_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    latest_business_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("business_snapshots.id", ondelete="RESTRICT")
    )
    previous_diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="RESTRICT")
    )
    current_diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="RESTRICT")
    )

    latest_business_snapshot: Mapped["BusinessSnapshot"] = relationship()
    changes: Mapped[list["BottleneckChange"]] = relationship(
        back_populates="reassessment", cascade="all, delete-orphan"
    )


class BottleneckChange(Base):
    __tablename__ = "bottleneck_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reassessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("reassessment_snapshots.id", ondelete="CASCADE")
    )
    bottleneck_type: Mapped[str] = mapped_column(String(100), nullable=False)
    change_type: Mapped[BottleneckChangeType] = mapped_column(
        enum_type(BottleneckChangeType, "bottleneck_change_type", 20), nullable=False
    )
    previous_bottleneck_id: Mapped[int | None] = mapped_column(
        ForeignKey("bottlenecks.id", ondelete="RESTRICT")
    )
    current_bottleneck_id: Mapped[int | None] = mapped_column(
        ForeignKey("bottlenecks.id", ondelete="RESTRICT")
    )
    detail: Mapped[str | None] = mapped_column(Text)

    reassessment: Mapped["ReassessmentSnapshot | None"] = relationship(back_populates="changes")


from app.domain.business import Business  # noqa: E402, F401
from app.domain.dataset import BusinessSnapshot, Dataset  # noqa: E402
from app.domain.execution import Execution  # noqa: E402, F401
from app.domain.simulation import Simulation  # noqa: E402, F401
