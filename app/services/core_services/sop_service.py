from pathlib import Path

from app.config.env_config import get_settings
from app.repository.vector_repository.qdrant_repository import (
    QdrantVectorRepository,
)
from app.services.core_services.embedding_service import EmbeddingProvider
from langchain_community.document_loaders import TextLoader
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
        chunk_size=500,
        chunk_overlap=75,
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

    loader = TextLoader(str(path), encoding="utf-8")
    documents = loader.load()

    provider = embedding_provider or EmbeddingProvider()
    repo = repository or QdrantVectorRepository()

    markdown = split_markdown(documents, source=source_id)
    chunks = split_chunks(markdown, provider)

    embeddings = provider.embed_documents(
        [chunk.page_content for chunk in chunks]
    )

    repo.upsert_documents(
        collection_name=settings.QDRANT_COLLECTION,
        documents=chunks,
        embeddings=embeddings,
        source_id=source_id,
    )

    return len(chunks)
