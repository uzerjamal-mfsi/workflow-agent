from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from transformers import PreTrainedTokenizerBase

from app.config.env_config import get_settings
from app.repository.vector_repository.qdrant_repository import (
    QdrantVectorRepository,
)
from app.services.core_services.embedding_service import EmbeddingProvider
from app.services.core_services.sop_service import (
    ingest_sops,
    split_chunks,
    split_markdown,
)


@pytest.fixture
def mock_tokenizer() -> MagicMock:
    tokenizer = MagicMock(spec=PreTrainedTokenizerBase)
    tokenizer.tokenize.side_effect = lambda text: text.split()
    return tokenizer


@pytest.fixture
def mock_embedding_provider(mock_tokenizer: MagicMock) -> MagicMock:
    provider = MagicMock(spec=EmbeddingProvider)
    provider.tokenizer = mock_tokenizer
    provider.embed_documents.side_effect = lambda texts: [
        [0.1 * (i + 1), 0.2, 0.3] for i in range(len(texts))
    ]
    return provider


@pytest.fixture
def mock_repository() -> MagicMock:
    repo = MagicMock(spec=QdrantVectorRepository)
    repo.upsert_documents.return_value = ["point-1", "point-2"]
    return repo


@pytest.fixture
def sample_sop_file(tmp_path: Path) -> Path:
    content = (
        "# Workflow SOPs\n\n"
        "## 1. Purpose and scope\n"
        "These procedures govern task creation and assignment.\n\n"
        "## 2. Task creation and assignment\n"
        "Every task must have a concise title, assignee, and priority.\n"
    )
    file_path = tmp_path / "test_sops.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_split_markdown_splits_headers() -> None:
    source = "test_sop.md"
    document = [
        Document(
            page_content=(
                "# Header 1\n\n"
                "## Section A\n"
                "Content for Section A.\n\n"
                "## Section B\n"
                "Content for Section B.\n"
            )
        )
    ]

    splits = split_markdown(document, source=source)

    assert len(splits) == 2
    assert splits[0].metadata["Header 2"] == "Section A"
    assert splits[0].metadata["source"] == source
    assert "Content for Section A" in splits[0].page_content

    assert splits[1].metadata["Header 2"] == "Section B"
    assert splits[1].metadata["source"] == source
    assert "Content for Section B" in splits[1].page_content


def test_split_markdown_attaches_source_metadata() -> None:
    source = "custom/source/path.md"
    document = [Document(page_content="## Single Section\nContent here.")]

    splits = split_markdown(document, source=source)

    assert len(splits) == 1
    assert splits[0].metadata["source"] == source


def test_split_chunks_creates_chunks_with_metadata(
    mock_embedding_provider: MagicMock,
) -> None:
    documents = [
        Document(
            page_content="Some long markdown section text to be chunked.",
            metadata={"Header 2": "Section 1", "source": "test.md"},
        )
    ]

    chunks = split_chunks(documents, mock_embedding_provider)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert isinstance(chunk, Document)
        assert chunk.metadata["Header 2"] == "Section 1"
        assert chunk.metadata["source"] == "test.md"


def test_ingest_sops_successful_pipeline(
    sample_sop_file: Path,
    mock_repository: MagicMock,
    mock_embedding_provider: MagicMock,
) -> None:
    settings = get_settings()

    chunk_count = ingest_sops(
        file_path=sample_sop_file,
        repository=mock_repository,
        embedding_provider=mock_embedding_provider,
    )

    assert chunk_count == 2
    mock_embedding_provider.embed_documents.assert_called_once()
    called_texts = mock_embedding_provider.embed_documents.call_args[0][0]
    assert len(called_texts) == 2

    mock_repository.upsert_documents.assert_called_once()
    call_kwargs = mock_repository.upsert_documents.call_args.kwargs
    assert call_kwargs["collection_name"] == settings.QDRANT_COLLECTION
    assert len(call_kwargs["documents"]) == 2
    assert len(call_kwargs["embeddings"]) == 2
    assert call_kwargs["source_id"] == sample_sop_file.as_posix()


def test_ingest_sops_with_default_dependencies(
    sample_sop_file: Path,
) -> None:
    settings = get_settings()

    mock_provider_instance = MagicMock()
    mock_tokenizer = MagicMock(spec=PreTrainedTokenizerBase)
    mock_tokenizer.tokenize.side_effect = lambda text: text.split()
    mock_provider_instance.tokenizer = mock_tokenizer
    mock_provider_instance.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]

    mock_repo_instance = MagicMock()

    with (
        patch(
            "app.services.core_services.sop_service.EmbeddingProvider",
            return_value=mock_provider_instance,
        ) as mock_provider_cls,
        patch(
            "app.services.core_services.sop_service.QdrantVectorRepository",
            return_value=mock_repo_instance,
        ) as mock_repo_cls,
    ):
        chunk_count = ingest_sops(file_path=sample_sop_file)

        mock_provider_cls.assert_called_once()
        mock_repo_cls.assert_called_once()
        assert chunk_count == 2
        mock_repo_instance.upsert_documents.assert_called_once_with(
            collection_name=settings.QDRANT_COLLECTION,
            documents=mock_repo_instance.upsert_documents.call_args.kwargs[
                "documents"
            ],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            source_id=sample_sop_file.as_posix(),
        )


def test_ingest_sops_missing_file_raises_error() -> None:
    missing_path = Path("non_existent_sop_file.md")

    with pytest.raises((RuntimeError, FileNotFoundError)):
        ingest_sops(file_path=missing_path)

