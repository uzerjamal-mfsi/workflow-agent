from datetime import datetime, timezone
from typing import Any

from app.models.mock_models import Notification, TeamMember
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


def notification_to_dict(notif: Notification) -> dict[str, Any]:
    return {
        "id": notif.id,
        "recipient": notif.recipient,
        "subject": notif.subject,
        "message": notif.message,
        "template_id": notif.template_id,
        "status": notif.status,
        "idempotency_key": notif.idempotency_key,
        "created_at": notif.created_at,
    }


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def send_notification(
        self,
        recipient: str,
        message: str,
        subject: str | None = None,
        template_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key:
            stmt = select(Notification).where(
                Notification.idempotency_key == idempotency_key
            )
            existing = await self.session.scalar(stmt)
            if existing:
                return notification_to_dict(existing)

        stmt = select(TeamMember).where(
            or_(TeamMember.user_id == recipient, TeamMember.email == recipient)
        )
        member = await self.session.scalar(stmt)
        if not member:
            raise ValueError(f"Recipient '{recipient}' not found in team directory")

        notif = Notification(
            recipient=recipient,
            subject=subject,
            message=message,
            template_id=template_id,
            status="sent",
            idempotency_key=idempotency_key,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.session.add(notif)
        await self.session.commit()
        return notification_to_dict(notif)

    async def get_sent_notifications(
        self, recipient: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        stmt = select(Notification).order_by(Notification.id.desc()).limit(limit)
        if recipient:
            stmt = stmt.where(Notification.recipient == recipient)

        notifs = (await self.session.scalars(stmt)).all()
        return [notification_to_dict(n) for n in notifs]
