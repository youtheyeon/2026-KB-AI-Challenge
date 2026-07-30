# 사업자 기본 정보와 익명 데모 세션을 함께 등록하는 라우터
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import session as db_session
from app.domain.business import Business
from app.domain.demo_session import DemoSession
from app.domain.enums import DemoSessionStatus

router = APIRouter(prefix="/api/businesses", tags=["businesses"])


class BusinessRegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    region: str = Field(min_length=1, max_length=255)
    industry: str = Field(min_length=1, max_length=100)
    employee_count: int = Field(
        default=0,
        ge=0,
        le=2_147_483_647,
        alias="employeeCount",
    )
    primary_sales_channels: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list,
        alias="primarySalesChannels",
    )

    @field_validator("name", "region", "industry", mode="before")
    @classmethod
    def normalize_profile_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class BusinessRegistrationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_id: int = Field(alias="businessId")
    name: str
    region: str
    industry: str
    employee_count: int = Field(alias="employeeCount")
    primary_sales_channels: list[str] = Field(alias="primarySalesChannels")


def get_db() -> Generator[Session]:
    database = db_session.SessionFactory()
    try:
        yield database
    finally:
        database.close()


def get_active_demo_session(
    database: Session,
    session_cookie: str | None,
    now: datetime,
) -> tuple[DemoSession, bool]:
    try:
        session_id = UUID(session_cookie) if session_cookie else None
    except ValueError:
        session_id = None

    existing_session = database.get(DemoSession, session_id) if session_id else None
    if (
        existing_session
        and existing_session.status == DemoSessionStatus.ACTIVE
        and existing_session.expires_at > now
    ):
        existing_session.last_accessed_at = now
        return existing_session, False

    if (
        existing_session
        and existing_session.status == DemoSessionStatus.ACTIVE
        and existing_session.expires_at <= now
    ):
        existing_session.status = DemoSessionStatus.EXPIRED

    demo_session = DemoSession(
        id=uuid4(),
        last_accessed_at=now,
        expires_at=now + timedelta(hours=24),
        status=DemoSessionStatus.ACTIVE,
    )
    database.add(demo_session)
    return demo_session, True


@router.post("", response_model=BusinessRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_business(
    request: BusinessRegistrationRequest,
    response: Response,
    database: Annotated[Session, Depends(get_db)],
    demo_session_cookie: str | None = Cookie(default=None, alias="demo_session_id"),
) -> BusinessRegistrationResponse:
    now = datetime.now(UTC)
    with database.begin():
        demo_session, created_session = get_active_demo_session(
            database,
            demo_session_cookie,
            now,
        )
        business = Business(
            demo_session_id=demo_session.id,
            name=request.name,
            region=request.region,
            industry=request.industry,
            employee_count=request.employee_count,
            primary_sales_channels=request.primary_sales_channels,
        )
        database.add(business)
        database.flush()

        registered_business = BusinessRegistrationResponse(
            business_id=business.id,
            name=business.name,
            region=business.region,
            industry=business.industry,
            employee_count=business.employee_count,
            primary_sales_channels=business.primary_sales_channels,
        )

    if created_session:
        response.set_cookie(
            key="demo_session_id",
            value=str(demo_session.id),
            max_age=int(timedelta(hours=24).total_seconds()),
            httponly=True,
            samesite="lax",
            secure=settings.environment == "production",
        )

    return registered_business
