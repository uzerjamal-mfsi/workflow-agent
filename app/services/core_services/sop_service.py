from pathlib import Path

from app.config.env_config import get_settings
from app.repository.vector_repository.qdrant_repository import (
    QdrantVectorRepository,
)
from app.services.core_services.embedding_service import EmbeddingProvider
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

DEFAULT_SOP_PATH = Path("app/data/workflow_sops.md")


def split_markdown(document: list[Document], source: str) -> list[Document]:
    """Split markdown file into sections based on headers and attach source."""
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "Header 2")],
        strip_headers=False,
    )

    md_header_splits = splitter.split_text(document[0].page_content)
    for split in md_header_splits:
        split.metadata["source"] = source

    return md_header_splits


def split_chunks(
    documents: list[Document], embedding_provider: EmbeddingProvider
) -> list[Document]:
    """Split markdown sections into chunks using the embedding tokenizer."""
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer=embedding_provider.tokenizer,
        chunk_size=300,
        chunk_overlap=50,
    )

    return splitter.split_documents(documents)


def ingest_sops(
    file_path: Path | str = DEFAULT_SOP_PATH,
    repository: QdrantVectorRepository | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> int:
    """Load workflow SOPs, split by section, and index chunks into Qdrant."""
    settings = get_settings()
    path = Path(file_path)
    source_id = path.as_posix()

    content = path.read_text(encoding="utf-8")
    documents = [Document(page_content=content, metadata={"source": str(path)})]

    provider = embedding_provider or EmbeddingProvider()
    repo = repository or QdrantVectorRepository()

    markdown = split_markdown(documents, source=source_id)
    chunks = split_chunks(markdown, provider)

    embeddings = provider.embed_documents(
        [chunk.page_content for chunk in chunks]
    )

    _ = repo.upsert_documents(
        collection_name=settings.QDRANT_COLLECTION,
        documents=chunks,
        embeddings=embeddings,
        source_id=source_id,
    )

    return len(chunks)

def search_sops(
    repository: QdrantVectorRepository,
    embedding_provider: EmbeddingProvider,
    collection_name: str,
    query: str,
    limit: int = 3,
) -> list[str]:
    """Retrieve top-k relevant SOP sections using vector similarity search."""
    
    query_vector = embedding_provider.embed_query(query)

    results = repository.search_documents(
        collection_name=collection_name,
        query_vectors=query_vector,
        limit=limit,
    )

    return [item["content"] for item in results if item.get("content")]