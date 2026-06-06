from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Hintro Meeting Intelligence API"
    environment: str = "development"
    port: int = 8000
    cors_origin: str = "*"
    public_api_url: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql+asyncpg://hintro:hintro@localhost:5432/hintro"

    # Auth
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7

    # LLM providers
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "models/gemini-embedding-001"

    # Redis
    redis_url: str | None = "redis://localhost:6379"

    # Integrations
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None

    # Scheduler
    cron_secret: str = "change-me-cron-secret"

    # Candidate (for /api/evaluation)
    candidate_name: str = "Aman Kumar"
    candidate_email: str = "aman0611kumar@gmail.com"
    repository_url: str = ""
    deployed_url: str = ""

    @field_validator("database_url")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        # Managed providers (Render, Neon) hand out postgres:// or postgresql:// URLs.
        # SQLAlchemy's async engine needs the +asyncpg driver, so normalize here.
        if v.startswith("postgresql+asyncpg://") or v.startswith("postgresql+psycopg://"):
            return v
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_origin.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origin.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
