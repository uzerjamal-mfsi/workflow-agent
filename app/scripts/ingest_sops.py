"""CLI command to ingest SOP documents into Qdrant."""

import sys
from pathlib import Path

from app.services.core_services.sop_service import (
    DEFAULT_SOP_PATH,
    ingest_sops,
)


def main() -> None:
    file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOP_PATH
    chunk_count = ingest_sops(file_path=file_path)
    print(f"Successfully ingested {chunk_count} chunks from '{file_path}' into Qdrant.")


if __name__ == "__main__":
    main()
