# 백엔드 애플리케이션 환경설정을 정의하는 모듈
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KB AI Challenge API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/kb_ai_challenge"
    migration_database_url: str = "postgresql+psycopg://postgres@localhost:5432/kb_ai_challenge"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BACKEND_",
        extra="ignore",
    )


settings = Settings()
