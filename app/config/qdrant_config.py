from functools import lru_cache

from qdrant_client import QdrantClient

from app.config.env_config import get_settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Create and return a qdrant client"""

    settings = get_settings()

    return QdrantClient(
        url = settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )