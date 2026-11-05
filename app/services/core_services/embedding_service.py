from functools import lru_cache
from typing import cast

from app.config.embedding_config import get_embedding_model
from sentence_transformers import SentenceTransformer

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingProvider:
    def __init__(self) -> None:
        self.embedding_model: SentenceTransformer = get_embedding_model()

    @property
    def tokenizer(self):
        return self.embedding_model.tokenizer

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts."""
        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return cast(list[list[float]], embeddings.tolist())

    def embed_query(self, query: str) -> list[float]:
        """Embed a query with BGE search instruction prefix."""
        prefixed_query = f"{BGE_QUERY_PREFIX}{query}"
        embeddings = self.embedding_model.encode(
            prefixed_query,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return cast(list[float], embeddings.tolist())

@lru_cache()
def get_embedding_provider() -> EmbeddingProvider:
    return EmbeddingProvider()