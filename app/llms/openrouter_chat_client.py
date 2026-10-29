from typing import TYPE_CHECKING

from langchain_openrouter import ChatOpenRouter

from app.config.env_config import settings
from app.constants.app_constants import OPENROUTER_CHAT_MODEL

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler


class OpenRouterChatClient:
    """Factory for OpenRouter chat model clients."""

    def __init__(self) -> None:
        """Initialize with model name and temperature from constants."""
        self.model_name = (
            settings.MODEL_NAME
            or settings.OPENROUTER_MODEL_NAME
            or OPENROUTER_CHAT_MODEL.MODEL_NAME.value
        )
        self.temperature = OPENROUTER_CHAT_MODEL.TEMPERATURE.value

    @staticmethod
    def _tracing_callbacks() -> list["BaseCallbackHandler"]:
        """Return LangSmith tracing callbacks when tracing is enabled.

        Returns:
            A tracer callback list, or an empty list when tracing is disabled.
        """
        if not settings.LANGSMITH_TRACING:
            return []

        from langchain_core.tracers import LangChainTracer
        from langsmith import Client

        tracer = LangChainTracer(
            project_name=settings.LANGSMITH_PROJECT,
            client=Client(api_key=settings.LANGSMITH_API_KEY),
        )
        return [tracer]

    def create_client(self):
        """Create a chat model client.

        Returns:
            ChatOpenRouter instance.
        """
        chat_client = ChatOpenRouter(
            model=self.model_name,
            temperature=self.temperature,
            api_key=settings.OPENROUTER_API_KEY,
            callbacks=self._tracing_callbacks(),
        )
        return chat_client


default_chat_client = OpenRouterChatClient().create_client()
