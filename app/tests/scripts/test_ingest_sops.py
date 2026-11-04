from pathlib import Path
from unittest.mock import patch

import pytest

from app.scripts.ingest_sops import main
from app.services.core_services.sop_service import DEFAULT_SOP_PATH


def test_main_with_default_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("sys.argv", ["ingest_sops.py"]),
        patch(
            "app.scripts.ingest_sops.ingest_sops", return_value=12
        ) as mock_ingest,
    ):
        main()

        mock_ingest.assert_called_once_with(file_path=DEFAULT_SOP_PATH)
        captured = capsys.readouterr()
        assert (
            f"Successfully ingested 12 chunks from '{DEFAULT_SOP_PATH}' into Qdrant."
            in captured.out
        )


def test_main_with_custom_file_path(capsys: pytest.CaptureFixture[str]) -> None:
    custom_path = "custom/docs/sop.md"
    expected_path = Path(custom_path)

    with (
        patch("sys.argv", ["ingest_sops.py", custom_path]),
        patch(
            "app.scripts.ingest_sops.ingest_sops", return_value=8
        ) as mock_ingest,
    ):
        main()

        mock_ingest.assert_called_once_with(file_path=expected_path)
        captured = capsys.readouterr()
        assert (
            f"Successfully ingested 8 chunks from '{expected_path}' into Qdrant."
            in captured.out
        )

