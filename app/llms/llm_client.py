from functools import lru_cache

from langchain_openrouter import ChatOpenRouter

from app.config.env_config import get_settings


@lru_cache()
def get_llm() -> ChatOpenRouter:
    """Return cached OpenRouter chat model Instance"""
    settings = get_settings()

    return ChatOpenRouter(
        model=settings.MODEL_NAME,
        api_key=settings.OPENROUTER_API_KEY,
        timeout=settings.LLM_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )
