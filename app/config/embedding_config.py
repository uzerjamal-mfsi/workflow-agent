from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config.env_config import get_settings


@lru_cache()
def get_embedding_model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.EMBEDDING_MODEL)