from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from app.llms.llm_client import get_llm


def test_get_llm_initialization():
    mock_settings = MagicMock()
    mock_settings.MODEL_NAME = "google/gemini-2.5-flash"
    mock_settings.OPENROUTER_API_KEY = SecretStr("mock-key-123")

    with (
        patch("app.llms.llm_client.get_settings", return_value=mock_settings),
        patch("app.llms.llm_client.ChatOpenRouter") as mock_chat_cls,
    ):
        get_llm()
        mock_chat_cls.assert_called_once_with(
            model="google/gemini-2.5-flash",
            api_key=mock_settings.OPENROUTER_API_KEY,
        )

