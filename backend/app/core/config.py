# 백엔드 애플리케이션 환경설정을 정의하는 모듈
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KB AI Challenge API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/kb_ai_challenge"
    migration_database_url: str = "postgresql+psycopg://postgres@localhost:5432/kb_ai_challenge"
    cors_allow_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://2026-kb-ai-challenge-kirby.vercel.app"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BACKEND_",
        extra="ignore",
    )

    @property
    def cors_allow_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()
