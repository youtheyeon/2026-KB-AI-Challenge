# 고정 A·B·C 자금 배분안과 조건부 재무 결과를 저장하는 SQLAlchemy 모델
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, composite, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import (
    AllocationCategory,
    DataSourceType,
    RepaymentType,
    RiskLevel,
    ScenarioCode,
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


@dataclass(frozen=True)
class LoanCondition:
    amount: int
    annual_interest_rate: Decimal
    term_months: int
    grace_months: int
    repayment_type: RepaymentType


@dataclass(frozen=True)
class ScenarioFinancialResult:
    monthly_loan_payment: int | None = None
    monthly_recurring_cost: int | None = None
    cash_after_payment: int | None = None
    break_even_additional_revenue: int | None = None
    required_additional_orders: int | None = None
    payback_period_months: int | None = None
    risk_level: RiskLevel | None = None


class Simulation(TimestampMixin, Base):
    __tablename__ = "simulations"
    __table_args__ = (
        CheckConstraint("loan_amount > 0", name="ck_simulation_loan_amount"),
        CheckConstraint("loan_interest_rate >= 0", name="ck_simulation_interest_rate"),
        CheckConstraint("loan_term_months > 0", name="ck_simulation_term"),
        CheckConstraint("loan_grace_months >= 0", name="ck_simulation_grace"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="RESTRICT")
    )
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id", ondelete="RESTRICT"))
    diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="RESTRICT")
    )
    business_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("business_snapshots.id", ondelete="RESTRICT")
    )
    loan_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    loan_interest_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    loan_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    loan_grace_months: Mapped[int] = mapped_column(Integer, nullable=False)
    loan_repayment_type: Mapped[RepaymentType] = mapped_column(
        enum_type(RepaymentType, "repayment_type", 30), nullable=False
    )
    loan_condition: Mapped[LoanCondition] = composite(
        LoanCondition,
        loan_amount,
        loan_interest_rate,
        loan_term_months,
        loan_grace_months,
        loan_repayment_type,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="creating")
    allocation_generator_version: Mapped[str | None] = mapped_column(String(100))
    calculation_version: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    public_data_reference_date: Mapped[date | None] = mapped_column(Date)

    scenarios: Mapped[list["Scenario"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )
    selection: Mapped["ScenarioSelection | None"] = relationship(
        back_populates="simulation", uselist=False, cascade="all, delete-orphan"
    )

    def validate_scenarios(self) -> None:
        codes = [scenario.code for scenario in self.scenarios]
        if len(codes) != 3 or set(codes) != set(ScenarioCode):
            raise ValueError("A, B, C 시나리오가 각각 하나씩 필요합니다.")
        for scenario in self.scenarios:
            scenario.validate_allocations()


class Scenario(TimestampMixin, Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        UniqueConstraint("simulation_id", "code", name="uq_simulation_scenario_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int | None] = mapped_column(
        ForeignKey("simulations.id", ondelete="CASCADE")
    )
    code: Mapped[ScenarioCode] = mapped_column(
        enum_type(ScenarioCode, "scenario_code", 5), nullable=False
    )
    strategy_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monthly_loan_payment: Mapped[int | None] = mapped_column(BigInteger)
    monthly_recurring_cost: Mapped[int | None] = mapped_column(BigInteger)
    cash_after_payment: Mapped[int | None] = mapped_column(BigInteger)
    break_even_additional_revenue: Mapped[int | None] = mapped_column(BigInteger)
    required_additional_orders: Mapped[int | None] = mapped_column(Integer)
    payback_period_months: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[RiskLevel | None] = mapped_column(enum_type(RiskLevel, "risk_level", 20))
    financial_result: Mapped[ScenarioFinancialResult] = composite(
        ScenarioFinancialResult,
        monthly_loan_payment,
        monthly_recurring_cost,
        cash_after_payment,
        break_even_additional_revenue,
        required_additional_orders,
        payback_period_months,
        risk_level,
    )
    target_metrics: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list
    )
    risk_reasons: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    simulation: Mapped["Simulation | None"] = relationship(back_populates="scenarios")
    allocations: Mapped[list["ScenarioAllocation"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )
    reasons: Mapped[list["ScenarioReason"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )

    def validate_allocations(self) -> None:
        categories = [allocation.category for allocation in self.allocations]
        if len(categories) != 4 or set(categories) != set(AllocationCategory):
            raise ValueError("모든 배분 카테고리가 각각 하나씩 필요합니다.")
        if any(allocation.ratio < Decimal("0.05") for allocation in self.allocations):
            raise ValueError("각 카테고리 비율은 5% 이상이어야 합니다.")
        if sum((allocation.ratio for allocation in self.allocations), Decimal()) != Decimal(1):
            raise ValueError("배분 비율 합계는 100%여야 합니다.")
        if sum(allocation.amount for allocation in self.allocations) != self.total_amount:
            raise ValueError("배분 금액 합계는 대출금액과 같아야 합니다.")


class ScenarioAllocation(Base):
    __tablename__ = "scenario_allocations"
    __table_args__ = (
        UniqueConstraint("scenario_id", "category", name="uq_scenario_allocation_category"),
        CheckConstraint("ratio >= 0.05 AND ratio <= 1", name="ck_scenario_allocation_ratio"),
        CheckConstraint("amount >= 0", name="ck_scenario_allocation_amount"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int | None] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"))
    category: Mapped[AllocationCategory] = mapped_column(
        enum_type(AllocationCategory, "allocation_category", 40), nullable=False
    )
    ratio: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    scenario: Mapped["Scenario | None"] = relationship(back_populates="allocations")


class ScenarioReason(Base):
    __tablename__ = "scenario_reasons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"))
    bottleneck_id: Mapped[int | None] = mapped_column(
        ForeignKey("bottlenecks.id", ondelete="RESTRICT")
    )
    category: Mapped[AllocationCategory] = mapped_column(
        enum_type(AllocationCategory, "scenario_reason_category", 40), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[DataSourceType] = mapped_column(
        enum_type(DataSourceType, "scenario_reason_source", 40),
        nullable=False,
        default=DataSourceType.CALCULATED,
    )

    scenario: Mapped["Scenario"] = relationship(back_populates="reasons")


class ScenarioSelection(TimestampMixin, Base):
    __tablename__ = "scenario_selections"
    __table_args__ = (UniqueConstraint("simulation_id", name="uq_scenario_selection_simulation"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id", ondelete="RESTRICT"))
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="RESTRICT"))
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    simulation: Mapped["Simulation | None"] = relationship(back_populates="selection")
    scenario: Mapped["Scenario | None"] = relationship()

    def validate_scenario(self, scenario_simulation_id: int) -> None:
        if self.simulation_id != scenario_simulation_id:
            raise ValueError("선택 시나리오는 같은 시뮬레이션에 속해야 합니다.")

    def lock(self) -> None:
        self.locked = True

    def change_scenario(self, scenario_id: int) -> None:
        if self.locked:
            raise ValueError("집행 등록 후에는 시나리오 선택을 변경할 수 없습니다.")
        self.scenario_id = scenario_id
