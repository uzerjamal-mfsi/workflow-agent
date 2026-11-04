from pathlib import Path

from app.config.env_config import get_settings
from app.repository.vector_repository.qdrant_repository import (
    delete_source,
    upsert_documents,
)
from app.services.core_services.embedding_service import EmbeddingProvider
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

SOP_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "workflow_sops.md"

def split_markdown(document: list[Document]) -> list[Document]:
    """Split markdown file into chunks based on header"""
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "Header 2")], #sop document only contains this header
        strip_headers=False
    )

    md_header_splits = splitter.split_text(document[0].page_content)

    return md_header_splits

def split_chunks(document: list[Document], embedding_provider: EmbeddingProvider):
    """Split document into chunks"""

    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer=embedding_provider.tokenizer,
        chunk_size=500,
        chunk_overlap=75
    )

    return splitter.split_documents(document)

def ingest_sops():
    """Load workflow SOPs, split by section, index chunks into Qdrant."""
    settings = get_settings()
    loader = TextLoader(str(SOP_FILE_PATH), encoding="utf-8")
    embedding_provider = EmbeddingProvider()

    document = loader.load()

    markdown = split_markdown(document)

    chunks = split_chunks(markdown, embedding_provider)

    embeddings = embedding_provider.embed_documents([chunk.page_content for chunk in chunks])

    source_id = str(SOP_FILE_PATH.resolve())
    delete_source(settings.QDRANT_COLLECTION, source_id)
    upsert_documents(settings.QDRANT_COLLECTION, chunks, embeddings, source_id)