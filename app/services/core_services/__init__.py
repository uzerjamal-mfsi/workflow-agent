"""Core (product) services: retrieval and SOP management."""

from app.services.core_services.sop_service import (
    DEFAULT_SOP_COLLECTION,
    ingest_sops,
    search_workflow_templates,
    split_sops_by_headings,
)

__all__ = [
    "DEFAULT_SOP_COLLECTION",
    "ingest_sops",
    "search_workflow_templates",
    "split_sops_by_headings",
]
