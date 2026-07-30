# 서비스 사용자와 소유 사업장의 관계를 저장하는 SQLAlchemy 모델
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domain.business import Business


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)

    businesses: Mapped[list["Business"]] = relationship(back_populates="user")

    @validates("email")
    def normalize_email(self, _key: str, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("이메일은 필수입니다.")
        return normalized
