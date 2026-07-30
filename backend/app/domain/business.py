# 사업장 기본 프로필과 소유 사용자 관계를 저장하는 SQLAlchemy 모델
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, BigInteger, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.dataset import (
        BusinessSnapshot,
        Dataset,
        PublicDataSnapshot,
    )
    from app.domain.diagnosis import Diagnosis
    from app.domain.user import User


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    trade_area_usage_type: Mapped[str | None] = mapped_column(String(100))
    business_age: Mapped[str | None] = mapped_column(String(100))
    store_type: Mapped[str | None] = mapped_column(String(100))
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_revenue_band: Mapped[str | None] = mapped_column(String(100))
    primary_sales_channels: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list
    )
    seat_count: Mapped[int | None] = mapped_column(Integer)
    average_wait_time_minutes: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    peak_hour_utilization_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    repeat_customer_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))

    user: Mapped["User | None"] = relationship(back_populates="businesses")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="business")
    snapshots: Mapped[list["BusinessSnapshot"]] = relationship(back_populates="business")
    public_data_snapshots: Mapped[list["PublicDataSnapshot"]] = relationship(
        back_populates="business"
    )
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="business")

    @validates("name", "region", "industry")
    def require_profile_value(self, key: str, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            labels = {"name": "사업장명", "region": "지역", "industry": "업종"}
            raise ValueError(f"{labels[key]}은 필수입니다.")
        return normalized
