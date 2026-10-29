"""CLI command to ingest SOP documents into Qdrant."""

import argparse
import sys
from pathlib import Path

from qdrant_client import QdrantClient

from app.config.env_config import settings
from app.config.log_config import logger
from app.services.core_services.sop_service import (
    DEFAULT_SOP_COLLECTION,
    ingest_sops,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for SOP ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest workflow SOP markdown files into Qdrant vector database."
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=None,
        help="Path to markdown file containing SOPs (defaults to app/data/workflow_sops.md).",
    )
    parser.add_argument(
        "--collection",
        "-c",
        type=str,
        default=DEFAULT_SOP_COLLECTION,
        help=f"Target Qdrant collection name (default: {DEFAULT_SOP_COLLECTION}).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Qdrant host (defaults to QDRANT_HOST setting or localhost).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Qdrant port (defaults to QDRANT_PORT setting).",
    )
    return parser.parse_args()


def main() -> None:
    """Run the SOP ingestion command."""
    args = parse_args()

    host = args.host or settings.QDRANT_HOST or "localhost"
    port = args.port or int(settings.QDRANT_PORT or 6333)

    logger.info(
        "Connecting to Qdrant at %s:%s for collection '%s'...",
        host,
        port,
        args.collection,
    )
    client = QdrantClient(host=host, port=port)

    try:
        docs = ingest_sops(
            file_path=args.file,
            collection_name=args.collection,
            client=client,
        )
        logger.info(
            "Successfully ingested %d SOP sections into Qdrant collection '%s'.",
            len(docs),
            args.collection,
        )
        print(
            f"Successfully ingested {len(docs)} SOP documents into Qdrant collection '{args.collection}' at {host}:{port}."
        )
    except Exception as e:
        logger.exception("Failed to ingest SOP documents: %s", e)
        print(f"Error ingesting SOP documents into Qdrant: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
