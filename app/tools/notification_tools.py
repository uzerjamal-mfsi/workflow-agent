from typing import Any

from langchain_core.tools import tool

from app.services.notification_service import send_notification


@tool("send_notification")
def send_notification_tool(
    recipient: str,
    message: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Send notification to a recipient."""
    return send_notification(recipient=recipient, message=message, **kwargs)


__all__ = ["send_notification_tool"]
