import re
from functools import lru_cache
from typing import ClassVar, Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load, Validate and Expose environment settings for the application"""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Qdrant settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "workflow-sop"
    QDRANT_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384

    # Postgres settings
    POSTGRES_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/workflow_agent"
    )

    # Persistence mode
    CHECKPOINTER_TYPE: Literal["memory", "postgres"] = "memory"

    # API Security
    API_KEY: SecretStr = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("API_KEY", "CHAT_API_KEY"),
        description="Required API key for authenticating chat endpoints via X-API-Key header",
    )

    # LLM
    OPENROUTER_API_KEY: SecretStr
    MODEL_NAME: str

    @property
    def raw_postgres_url(self) -> str:
        """Strip driver prefixes (e.g. '+psycopg', '+asyncpg') for tools that expect plain 'postgresql://'."""
        return re.sub(
            r"^postgresql\+[a-zA-Z0-9_]+://", "postgresql://", self.POSTGRES_URL
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()  # pyright: ignore[reportCallIssue]
