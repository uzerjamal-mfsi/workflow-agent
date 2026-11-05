from functools import lru_cache
from hashlib import sha256
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid5

from app.config.env_config import Settings, get_settings
from app.config.qdrant_config import get_qdrant_client
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    ExtendedPointId,
    FieldCondition,
    Filter,
    HasIdCondition,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)


class QdrantVectorRepository:
    """Repository for vector database operations using Qdrant."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings: Settings = settings or get_settings()
        self.client: QdrantClient = client or get_qdrant_client()

    def ensure_collection_exists(self, collection_name: str) -> None:
        """Ensure that the Qdrant collection and payload index exist."""
        if not self.client.collection_exists(collection_name):
            _ = self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.settings.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            _ = self.client.create_payload_index(
                collection_name=collection_name,
                field_name="source_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def upsert_documents(
        self,
        collection_name: str,
        documents: list[Document],
        embeddings: list[list[float]],
        source_id: str,
    ) -> list[str]:
        """Upsert documents into Qdrant using deterministic IDs, then clean up stale chunks."""
        self.ensure_collection_exists(collection_name)

        if len(documents) != len(embeddings):
            raise ValueError("Document and embedding counts do not match")

        points: list[PointStruct] = []
        point_ids: list[str] = []

        for index, (document, embedding) in enumerate(zip(documents, embeddings)):
            content = document.page_content
            content_hash = sha256(content.encode("utf-8")).hexdigest()

            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{source_id}:{content_hash}:{index}",
                )
            )
            point_ids.append(point_id)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "content": content,
                        "source": document.metadata.get("source", source_id),
                        "source_id": source_id,
                        "header": document.metadata.get("Header 2"),
                        "chunk_index": index,
                        "content_hash": content_hash,
                    },
                )
            )

        #Upsert points
        if points:
            self.client.upload_points(
                collection_name=collection_name,
                points=points,
                batch_size=64,
                wait=True,
            )

            #Clean up any stale chunks for this source_id
            _ = self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="source_id",
                            match=MatchValue(value=source_id),
                        )
                    ],
                    must_not=[
                        HasIdCondition(
                            has_id=cast(list[ExtendedPointId], point_ids)
                        )
                    ],
                ),
                wait=True,
            )

        return point_ids

    def search_documents(
        self,
        collection_name: str,
        query_vectors: list[float],
        limit: int = 3,
        filter: Filter | None = None
    ) -> list[dict[str, Any]]:
        """Search similar document chunks in Qdrant given a query embedding."""
        try:
            if not self.client.collection_exists(collection_name):
                return []

            search_result = self.client.query_points(
                collection_name=collection_name,
                query=query_vectors,
                limit=limit,
                query_filter=filter,
            )

            results: list[dict[str, Any]] = []
            for point in search_result.points:
                payload = point.payload or {}
                results.append(
                    {
                        "id": str(point.id),
                        "score": point.score,
                        "content": payload.get("content", ""),
                        "header": payload.get("header"),
                        "source": payload.get("source")
                    }
                )

            return results
        except Exception as e:
            print(e)
            return []

@lru_cache()
def get_qdrant_repository() -> QdrantVectorRepository:
    return QdrantVectorRepository()