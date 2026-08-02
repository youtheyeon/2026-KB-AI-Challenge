# 선택한 계획과 구분되는 실제 또는 Mock 집행 내역을 저장하는 SQLAlchemy 모델
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import AllocationCategory, ExecutionType


def enum_type(enum_class: type, name: str, length: int) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        length=length,
    )


class Execution(TimestampMixin, Base):
    __tablename__ = "executions"
    __table_args__ = (
        UniqueConstraint("simulation_id", name="uq_execution_simulation"),
        UniqueConstraint("selection_id", name="uq_execution_selection"),
        CheckConstraint("total_amount >= 0", name="ck_execution_total"),
        CheckConstraint("unused_amount >= 0", name="ck_execution_unused"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id", ondelete="RESTRICT"))
    selection_id: Mapped[int] = mapped_column(
        ForeignKey("scenario_selections.id", ondelete="RESTRICT")
    )
    execution_type: Mapped[ExecutionType] = mapped_column(
        enum_type(ExecutionType, "execution_type", 30), nullable=False
    )
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unused_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(1000))

    simulation: Mapped["Simulation"] = relationship()
    selection: Mapped["ScenarioSelection"] = relationship()
    allocations: Mapped[list["ExecutionAllocation"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )

    def validate_amounts(self, loan_amount: int) -> None:
        if self.total_amount + self.unused_amount != loan_amount:
            raise ValueError("집행금액과 미집행금액의 합은 대출금액과 같아야 합니다.")


class ExecutionAllocation(Base):
    __tablename__ = "execution_allocations"
    __table_args__ = (
        UniqueConstraint("execution_id", "category", name="uq_execution_allocation_category"),
        CheckConstraint("amount >= 0", name="ck_execution_allocation_amount"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[AllocationCategory | None] = mapped_column(
        enum_type(AllocationCategory, "execution_allocation_category", 40),
        nullable=True,
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    execution: Mapped["Execution"] = relationship(back_populates="allocations")


from app.domain.simulation import ScenarioSelection, Simulation  # noqa: E402
