from typing import Any

from app.config.env_config import get_settings
from app.repository.vector_repository.qdrant_repository import get_qdrant_repository
from app.schemas.state import WorkflowState
from app.services.core_services.embedding_service import get_embedding_provider
from app.services.core_services.sop_service import search_sops


def retrieve_sops(state: WorkflowState) -> dict[str, Any]:
    """Langgraph node to retrieve relevant SOP based on parsed_goal"""
    goal = state.get("parsed_goal", "")
    if not goal:
        return {"retrieved_sops": []}
    
    sops = search_sops(
        repository=get_qdrant_repository(),
        embedding_provider=get_embedding_provider(),
        collection_name=get_settings().QDRANT_COLLECTION,
        query=goal,
    )

    return {"retrieved_sops": sops}