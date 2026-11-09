"""LangSmith tracing configuration and initialization."""

import logging
import os
from functools import lru_cache

from langchain_core.tracers.langchain import LangChainTracer
from langsmith import Client

from app.config.env_config import Settings, get_settings

logger = logging.getLogger(__name__)


def setup_tracing(settings: Settings | None = None) -> bool:
    """Configure and synchronize LangSmith tracing environment variables."""
    settings = settings or get_settings()

    if settings.LANGSMITH_TRACING:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT

        if settings.LANGSMITH_API_KEY:
            api_key = settings.LANGSMITH_API_KEY.get_secret_value()
            os.environ["LANGSMITH_API_KEY"] = api_key
            os.environ["LANGCHAIN_API_KEY"] = api_key

        logger.info(
            "LangSmith tracing enabled for project '%s' (%s)",
            settings.LANGSMITH_PROJECT,
            settings.LANGSMITH_ENDPOINT,
        )
        return True

    # When tracing is disabled, ensure flags in os.environ reflect that
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    logger.info("LangSmith tracing is disabled")
    return False


def create_langsmith_client(settings: Settings | None = None) -> Client | None:
    """Create a LangSmith client instance if an API key is available."""
    settings = settings or get_settings()
    api_key = (
        settings.LANGSMITH_API_KEY.get_secret_value()
        if settings.LANGSMITH_API_KEY
        else None
    )
    if not api_key:
        return None

    return Client(
        api_key=api_key,
        api_url=settings.LANGSMITH_ENDPOINT,
    )


@lru_cache()
def get_langsmith_client() -> Client | None:
    """Get cached LangSmith client instance."""
    return create_langsmith_client(get_settings())


def get_langchain_tracer(
    project_name: str | None = None,
    client: Client | None = None,
) -> LangChainTracer | None:
    """Return a LangChainTracer instance for explicit callback usage."""
    settings = get_settings()
    if not settings.LANGSMITH_TRACING:
        return None

    project = project_name or settings.LANGSMITH_PROJECT
    langsmith_client = client or get_langsmith_client()
    return LangChainTracer(project_name=project, client=langsmith_client)