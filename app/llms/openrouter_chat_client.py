from langchain_openrouter import ChatOpenRouter

from app.config.env_config import settings
from app.constants.app_constants import OPENROUTER_CHAT_MODEL


class OpenRouterChatClient:
    """Factory for OpenRouter chat model clients."""

    def __init__(self) -> None:
        """Initialize with model name and temperature from constants."""
        self.model_name = OPENROUTER_CHAT_MODEL.MODEL_NAME.value
        self.temperature = OPENROUTER_CHAT_MODEL.TEMPERATURE.value

    def create_client(self):
        """Create a chat model client.

        Returns:
            ChatOpenRouter instance.
        """
        chat_client = ChatOpenRouter(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENROUTER_API_KEY,
        )
        return chat_client


default_chat_client = OpenRouterChatClient().create_client()
