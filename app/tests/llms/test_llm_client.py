from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from app.llms.llm_client import get_llm


@pytest.fixture(autouse=True)
def clear_llm_cache():
    get_llm.cache_clear()
    yield
    get_llm.cache_clear()


def test_get_llm_initialization():
    mock_settings = MagicMock()
    mock_settings.MODEL_NAME = "google/gemini-2.5-flash"
    mock_settings.OPENROUTER_API_KEY = SecretStr("mock-key-123")
    mock_settings.LLM_TIMEOUT = 45
    mock_settings.LLM_MAX_RETRIES = 2

    with (
        patch("app.llms.llm_client.get_settings", return_value=mock_settings),
        patch("app.llms.llm_client.ChatOpenRouter") as mock_chat_cls,
    ):
        get_llm()
        mock_chat_cls.assert_called_once_with(
            model="google/gemini-2.5-flash",
            api_key=mock_settings.OPENROUTER_API_KEY,
            timeout=45,
            max_retries=2,
        )


def test_get_llm_caches_instance():
    mock_settings = MagicMock()
    mock_settings.MODEL_NAME = "google/gemini-2.5-flash"
    mock_settings.OPENROUTER_API_KEY = SecretStr("mock-key-123")
    mock_settings.LLM_TIMEOUT = 60
    mock_settings.LLM_MAX_RETRIES = 3

    with (
        patch("app.llms.llm_client.get_settings", return_value=mock_settings),
        patch("app.llms.llm_client.ChatOpenRouter") as mock_chat_cls,
    ):
        mock_instance = MagicMock()
        mock_chat_cls.return_value = mock_instance

        llm_first = get_llm()
        llm_second = get_llm()

        assert llm_first is llm_second
        assert mock_chat_cls.call_count == 1



