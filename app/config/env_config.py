import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Load and expose environment settings for the application."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        # 1. Project information
        self.ENV: str = os.getenv("ENV", "dev")
        self.PROJECT_NAME: str = os.getenv("PROJECT_NAME", "agentic_web_starter")
        self.PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "0.1.0")
        self.PROJECT_DESCRIPTION: str = os.getenv(
            "PROJECT_DESCRIPTION",
            "An agentic workflow automation application.",
        )

        # 2. API configuration
        self.ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "").split(",")
        self.BASE_PATH: str = os.getenv("BASE_PATH", "")
        self.OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY", None)

        # 3. Working directory
        working_dir = os.path.abspath(os.getenv("WORKING_DIR", ".").strip() or ".")

        self.WORKING_PROJECT_DIR: str = os.path.join(working_dir, self.PROJECT_NAME)
        self.LOG_DIR: str = os.path.join(self.WORKING_PROJECT_DIR, "logs")

        # 4. Hugging Face configuration
        self.HF_HOME: str = os.getenv(
            "HF_HOME", os.path.join(self.WORKING_PROJECT_DIR, "hf")
        )
        os.environ.setdefault("HF_HOME", self.HF_HOME)

        # 5. Qdrant configuration
        self.COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "agentic_web_starter")
        self.USE_QDRANT: bool = (
            os.getenv("USE_QDRANT", "true").strip().lower() == "true"
        )

        self.QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
        self.QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
        self.QDRANT_PROTOCOL = os.getenv("QDRANT_PROTOCOL", "http")


settings = Settings()
