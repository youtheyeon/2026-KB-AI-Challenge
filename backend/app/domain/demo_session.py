# 로그인 없는 시연 브라우저를 구분하는 익명 데모 세션 모델
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import DemoSessionStatus

if TYPE_CHECKING:
    from app.domain.business import Business


class DemoSession(TimestampMixin, Base):
    __tablename__ = "demo_sessions"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[DemoSessionStatus] = mapped_column(
        Enum(
            DemoSessionStatus,
            name="demo_session_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda members: [member.value for member in members],
            length=20,
        ),
        nullable=False,
        default=DemoSessionStatus.ACTIVE,
        server_default=DemoSessionStatus.ACTIVE.value,
    )

    businesses: Mapped[list["Business"]] = relationship(back_populates="demo_session")
