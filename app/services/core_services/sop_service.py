import re
import uuid
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.config.qdrant_config import qdrant_config

DEFAULT_SOP_COLLECTION = "workflow_sops"

SECTION_METADATA: dict[int, dict[str, Any]] = {
    1: {
        "workflow_type": "policy",
        "action_type": "purpose_and_scope",
        "section_title": "Purpose and scope",
    },
    2: {
        "workflow_type": "task",
        "action_type": "create_task",
        "section_title": "Task creation and assignment",
    },
    3: {
        "workflow_type": "planning",
        "action_type": "dependency_planning",
        "section_title": "Dependency planning",
    },
    4: {
        "workflow_type": "notification",
        "action_type": "send_notification",
        "section_title": "Notification policy",
    },
    5: {
        "workflow_type": "task",
        "action_type": "update_task",
        "section_title": "Task updates and bulk operations",
    },
    6: {
        "workflow_type": "approval",
        "action_type": "sensitive_actions",
        "section_title": "Sensitive actions and approvals",
    },
    7: {
        "workflow_type": "reliability",
        "action_type": "retry_recovery",
        "section_title": "Retry, idempotency, and recovery",
    },
    8: {
        "workflow_type": "audit",
        "action_type": "verification",
        "section_title": "Verification and audit trail",
    },
    9: {
        "workflow_type": "governance",
        "action_type": "reviewer_roles",
        "section_title": "Reviewer roles",
    },
    10: {
        "workflow_type": "environment",
        "action_type": "data_environment",
        "section_title": "Data and environment",
    },
}


def _get_embeddings(embeddings: Any = None):
    if embeddings is not None:
        return embeddings
    from app.utils.core_utils.embedding_utils import embeddings_client

    return embeddings_client


def _extract_section_metadata(heading: str) -> dict[str, Any]:
    """Map section heading to workflow and action metadata."""
    match = re.match(r"^(\d+)\.\s*(.*)", heading)
    if match:
        num = int(match.group(1))
        meta = dict(
            SECTION_METADATA.get(
                num, {"workflow_type": "general", "action_type": "general"}
            )
        )
        meta["section_number"] = num
        meta.setdefault("section_title", match.group(2).strip())
        return meta

    lower = heading.lower()
    if "create" in lower or "assign" in lower:
        return {
            "workflow_type": "task",
            "action_type": "create_task",
            "section_title": heading,
        }
    if "update" in lower or "bulk" in lower:
        return {
            "workflow_type": "task",
            "action_type": "update_task",
            "section_title": heading,
        }
    if "notif" in lower:
        return {
            "workflow_type": "notification",
            "action_type": "send_notification",
            "section_title": heading,
        }
    if "plan" in lower or "depend" in lower:
        return {
            "workflow_type": "planning",
            "action_type": "dependency_planning",
            "section_title": heading,
        }
    if "approv" in lower or "sensit" in lower:
        return {
            "workflow_type": "approval",
            "action_type": "sensitive_actions",
            "section_title": heading,
        }
    return {
        "workflow_type": "general",
        "action_type": "general",
        "section_title": heading,
    }


def split_sops_by_headings(content: str) -> list[Document]:
    """Split markdown SOP content by H2 headings and attach typed metadata."""
    sections = re.split(r"(?m)^##\s+", content)
    documents: list[Document] = []

    for section in sections[1:]:
        lines = section.split("\n", 1)
        heading = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        metadata = _extract_section_metadata(heading)
        sec_id = metadata.get("section_number", heading)
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sop_section_{sec_id}"))
        doc = Document(
            id=doc_id,
            page_content=f"## {heading}\n{body}".strip(),
            metadata=metadata,
        )
        documents.append(doc)

    return documents


def ingest_sops(
    file_path: str | Path | None = None,
    collection_name: str | None = None,
    client: QdrantClient | None = None,
    embeddings: Any = None,
) -> list[Document]:
    """Load workflow SOPs, split by sections, and index chunks into Qdrant."""
    path = (
        Path(file_path)
        if file_path
        else Path(__file__).resolve().parents[2] / "data" / "workflow_sops.md"
    )
    content = path.read_text(encoding="utf-8")
    documents = split_sops_by_headings(content)

    col = collection_name or DEFAULT_SOP_COLLECTION
    emb = _get_embeddings(embeddings)
    cli = client or qdrant_config.get_qdrant_client()

    if not cli.collection_exists(col):
        dim = len(emb.embed_query("init_sop_collection"))
        cli.create_collection(
            collection_name=col,
            vectors_config=models.VectorParams(
                size=dim, distance=models.Distance.COSINE
            ),
        )

    store = QdrantVectorStore(client=cli, collection_name=col, embedding=emb)
    store.add_documents(documents, ids=[doc.id for doc in documents])
    return documents


def search_workflow_templates(
    query: str,
    workflow_type: str | None = None,
    action_type: str | None = None,
    collection_name: str | None = None,
    client: QdrantClient | None = None,
    embeddings: Any = None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Search SOP templates using semantic search and optional metadata filtering."""
    if not query:
        return []

    col = collection_name or DEFAULT_SOP_COLLECTION
    cli = client or qdrant_config.get_qdrant_client()

    conditions: list[Any] = []
    if workflow_type:
        conditions.append(
            models.FieldCondition(
                key="metadata.workflow_type",
                match=models.MatchValue(value=workflow_type),
            )
        )
    if action_type:
        conditions.append(
            models.FieldCondition(
                key="metadata.action_type",
                match=models.MatchValue(value=action_type),
            )
        )

    qdrant_filter = models.Filter(must=conditions) if conditions else None

    try:
        emb = _get_embeddings(embeddings)
        store = QdrantVectorStore(client=cli, collection_name=col, embedding=emb)
        docs = store.similarity_search(query, k=limit, filter=qdrant_filter)
    except (ConnectionError, ResponseHandlingException, UnexpectedResponse):
        # Gracefully handle unreachable or missing collection in offline envs
        return []

    return [
        {
            "content": doc.page_content,
            "page_content": doc.page_content,
            "metadata": doc.metadata,
            **doc.metadata,
        }
        for doc in docs
    ]


if __name__ == "__main__":
    from app.config.log_config import logger

    logger.info("Executing SOP ingestion...")
    documents = ingest_sops()
    logger.info("Successfully ingested %d SOP documents.", len(documents))

