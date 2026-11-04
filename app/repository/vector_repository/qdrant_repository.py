from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from app.config.env_config import get_settings
from app.config.qdrant_config import get_qdrant_client
from langchain_core.documents import Document
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)


def ensure_collection_exists() -> None:
    """Ensure that the Qdrant collection exists, if not create it."""
    settings = get_settings()
    client = get_qdrant_client()

    if not client.collection_exists(settings.QDRANT_COLLECTION):
        _ = client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )


def upsert_documents(
    collection_name: str,
    documents: list[Document],
    embeddings: list[list[float]],
    source_id: str
):
    """Upsert documents into the Qdrant collection."""
    ensure_collection_exists()

    if len(documents) != len(embeddings):
        raise ValueError("Document and embedding counts do not match")

    client = get_qdrant_client()
    points: list[PointStruct] = []

    for index, (document, embedding) in enumerate(zip(documents, embeddings)):
        content = document.page_content
        content_hash = sha256(
            content.encode("utf-8")
        ).hexdigest()

        point_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{source_id}:{content_hash}:{index}"
            )
        )

        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "content": content,
                    "source": document.metadata.get("source"),
                    "source_id": source_id,
                    "chunk_index": index,
                    "content_hash": content_hash
                }
            )
        )
    
    client.upload_points(
        collection_name=collection_name,
        points=points,
        batch_size=64,
        wait=True
    )

def delete_source(
    collection_name: str,
    source_id: str,
) -> None:
    """Delete all documents associated with a source."""
    ensure_collection_exists()

    client = get_qdrant_client()
    _ = client.delete(
        collection_name = collection_name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="source_id",
                    match=MatchValue(value=source_id),
                )
            ]
        ),
        wait=True,
    )