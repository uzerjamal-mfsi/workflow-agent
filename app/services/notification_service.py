import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config.db_config import get_sync_engine
from app.models import SentNotification

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_TEAM = DATA_DIR / "team_directory.json"
DEFAULT_TEMPLATES = DATA_DIR / "notification_templates.json"


class NotificationService:
    """Service for team directory lookups and notification template rendering."""

    def __init__(
        self,
        team_path: str | Path = DEFAULT_TEAM,
        templates_path: str | Path = DEFAULT_TEMPLATES,
        engine=None,
    ) -> None:
        self.team_path = Path(team_path)
        self.templates_path = Path(templates_path)
        self.engine = engine or get_sync_engine()
        self.sent_notifications: list[dict[str, Any]] = []

    def _read_team(self) -> dict[str, Any]:
        if not self.team_path.exists():
            return {}
        return json.loads(self.team_path.read_text(encoding="utf-8"))

    def _read_templates(self) -> list[dict[str, Any]]:
        if not self.templates_path.exists():
            return []
        data = json.loads(self.templates_path.read_text(encoding="utf-8"))
        return data.get("templates", [])

    def _find_user(self, recipient: str) -> dict[str, Any] | None:
        users = self._read_team().get("users", [])
        norm = recipient.strip().lower()
        for user in users:
            if (
                user.get("user_id", "").lower() == norm
                or user.get("email", "").lower() == norm
                or user.get("name", "").lower() == norm
            ):
                return user
        return None

    def _find_template(self, template_id_or_event: str | None) -> dict[str, Any] | None:
        if not template_id_or_event:
            return None
        norm = template_id_or_event.strip().lower()
        for tpl in self._read_templates():
            if (
                tpl.get("template_id", "").lower() == norm
                or tpl.get("event", "").lower() == norm
                or tpl.get("name", "").lower() == norm
            ):
                return tpl
        return None

    def render_template(
        self, template: dict[str, Any], context: dict[str, Any]
    ) -> tuple[str, str]:
        """Render subject and body strings with context substitutions."""
        subject = template.get("subject", "")
        body = template.get("body", "")
        for key, val in context.items():
            pattern = re.compile(rf"\{{\{{\s*{re.escape(key)}\s*\}}\}}")
            subject = pattern.sub(str(val), subject)
            body = pattern.sub(str(val), body)
        return subject, body

    def send_notification(
        self,
        recipient: str,
        message: str,
        template_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send notification to verified recipient with optional template rendering."""
        if not recipient or not recipient.strip():
            raise ValueError("Recipient is required")

        user = self._find_user(recipient)
        is_channel = (
            recipient.startswith("#")
            or recipient.startswith("task-")
            or recipient.lower() in {"task-updates", "platform", "operations"}
        )
        if not user and not is_channel:
            raise ValueError(f"Recipient '{recipient}' not found in team directory")

        if user and not user.get("active", True):
            raise ValueError(f"Recipient '{recipient}' is not an active team member")

        context = dict(kwargs)
        if user:
            context.setdefault("recipient_name", user.get("name", recipient))
            context.setdefault("recipient_email", user.get("email", ""))
        else:
            context.setdefault("recipient_name", recipient)

        tpl = self._find_template(template_id or kwargs.get("event"))
        if template_id and not tpl:
            raise ValueError(f"Template '{template_id}' not found")

        if tpl:
            subject, rendered_body = self.render_template(tpl, context)
            final_message = (
                rendered_body if not message or message == tpl.get("name") else message
            )
        else:
            subject = context.get("subject", f"Notification for {recipient}")
            final_message = message

        record = {
            "id": f"NOTIF-{len(self.sent_notifications) + 1:04d}",
            "notification_id": f"NOTIF-{len(self.sent_notifications) + 1:04d}",
            "recipient": recipient,
            "recipient_id": user.get("user_id") if user else None,
            "recipient_name": user.get("name") if user else recipient,
            "recipient_email": user.get("email") if user else None,
            "subject": subject,
            "message": final_message,
            "template_id": tpl.get("template_id") if tpl else None,
            "status": "sent",
        }
        self.sent_notifications.append(record)
        self._persist_notification(record)
        return record

    def _persist_notification(self, record: dict[str, Any]) -> None:
        try:
            with Session(self.engine) as session:
                entry = SentNotification(
                    id=record["notification_id"],
                    recipient=record["recipient"],
                    message=record["message"],
                    created_at=datetime.now(timezone.utc),
                )
                session.add(entry)
                session.commit()
        except Exception:
            pass


_default_notification_service = NotificationService()
send_notification = _default_notification_service.send_notification
sent_notifications = _default_notification_service.sent_notifications
sent_messages = sent_notifications


def get_sent_notifications() -> list[dict[str, Any]]:
    """Return all sent notification records."""
    return _default_notification_service.sent_notifications


def clear_sent_notifications() -> None:
    """Clear sent notification records."""
    _default_notification_service.sent_notifications.clear()
    try:
        with Session(_default_notification_service.engine) as session:
            session.execute(delete(SentNotification))
            session.commit()
    except Exception:
        pass
