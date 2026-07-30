# PostgreSQL 데이터베이스 설정과 공통 SQLAlchemy 모델 기반을 검증하는 테스트
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import Settings
from app.db.base import Base, TimestampMixin
from app.db.session import SessionFactory, engine


def test_settings_reads_separate_runtime_and_migration_urls(
    monkeypatch,
) -> None:
    runtime_url = "postgresql+psycopg://runtime_user@runtime.example.com:5432/runtime_db"
    migration_url = "postgresql+psycopg://migration_user@migration.example.com:5432/migration_db"
    monkeypatch.setenv("BACKEND_DATABASE_URL", runtime_url)
    monkeypatch.setenv("BACKEND_MIGRATION_DATABASE_URL", migration_url)

    settings = Settings()

    assert settings.database_url == runtime_url
    assert settings.migration_database_url == migration_url


def test_timestamp_mixin_adds_required_audit_columns_to_declarative_models() -> None:
    class AuditRecord(TimestampMixin, Base):
        __tablename__ = "audit_records"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    columns = AuditRecord.__table__.c

    assert Base.metadata is AuditRecord.metadata
    assert columns.created_at.nullable is False
    assert columns.created_at.server_default is not None
    assert columns.updated_at.nullable is False
    assert columns.updated_at.server_default is not None
    assert columns.updated_at.onupdate is not None


def test_session_factory_uses_the_configured_synchronous_engine() -> None:
    assert SessionFactory.kw["bind"] is engine
    assert SessionFactory.kw["autoflush"] is False
    assert SessionFactory.kw["autocommit"] is False
