from app.llms.openrouter_chat_client import default_chat_client


def get_default_chat_client():
    """Return the default OpenRouter chat client.

    Returns:
        Chat model client backed by OpenRouter.
    """
    return default_chat_client
