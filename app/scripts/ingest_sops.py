"""CLI command to ingest SOP documents into Qdrant."""

from app.services.core_services.sop_service import ingest_sops


def main() -> None:
    ingest_sops()

if __name__ == "__main__":
    main()