"""Environment-driven application settings."""

import os
from typing import Annotated

from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Load, validate and expose environment settings for the application.

    Values come from the process environment first, then from `.env`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 1. Project information
    ENV: str = "dev"
    PROJECT_NAME: str = "agentic_web_starter"
    PROJECT_VERSION: str = "0.1.0"
    PROJECT_DESCRIPTION: str = "An agentic workflow automation application."

    # 2. API configuration
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = []
    BASE_PATH: str = ""
    OPENROUTER_API_KEY: str | None = None

    # 3. Working directory
    WORKING_DIR: str = ""

    # 4. PostgreSQL database
    DATABASE_URL: str

    # 5. Hugging Face configuration
    HF_HOME: str = ""

    # 6. Qdrant configuration
    COLLECTION_NAME: str = "agentic_web_starter"
    USE_QDRANT: bool = True
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: str = "6333"
    QDRANT_PROTOCOL: str = "http"

    # 7. LangSmith tracing
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "workflow-agent"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Split a comma-separated origin list and drop empty entries."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _derive_paths_and_validate(self) -> "Settings":
        """Derive dependent paths, export HF_HOME, and validate tracing config."""
        if not self.HF_HOME:
            self.HF_HOME = os.path.join(self.WORKING_PROJECT_DIR, "hf")
        if not os.environ.get("HF_HOME"):
            os.environ["HF_HOME"] = self.HF_HOME

        if self.LANGSMITH_TRACING and not self.LANGSMITH_API_KEY:
            raise ValueError(
                "LANGSMITH_API_KEY is required when LANGSMITH_TRACING is true"
            )
        return self

    @property
    def _base_dir(self) -> str:
        """Return the absolute working directory."""
        return os.path.abspath(self.WORKING_DIR.strip() or ".")

    @computed_field
    @property
    def WORKING_PROJECT_DIR(self) -> str:
        """Return the project-specific directory under the working directory."""
        return os.path.join(self._base_dir, self.PROJECT_NAME)

    @computed_field
    @property
    def LOG_DIR(self) -> str:
        """Return the log directory used by the JSON log handlers."""
        return os.path.join(self.WORKING_PROJECT_DIR, "logs")


settings = Settings()
