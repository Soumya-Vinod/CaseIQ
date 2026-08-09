"""Centralised, type-safe configuration via pydantic-settings.

Everything is read from the environment (.env locally). No secrets in code.
Access through the cached `settings` singleton: `from app.core.config import settings`.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- App ---
    PROJECT_NAME: str = "CaseIQ"
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Security ---
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database (async) ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "caseiq"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """psycopg2 URL for Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis / Cache / Rate limit ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- LLM / Embeddings / News ---
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.1
    GROQ_MAX_TOKENS: int = 3000

    GEMINI_API_KEY: str | None = None
    GEMINI_EMBED_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_PROVIDER: Literal["gemini", "local"] = "local"
    EMBEDDING_DIM: int = 768

    NEWS_API_KEY: str | None = None

    # --- Retrieval ---
    RAG_TOP_K: int = 6
    RAG_MIN_SIMILARITY: float = 0.25  # cosine similarity floor for a "match"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
