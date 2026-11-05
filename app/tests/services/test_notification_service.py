import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mock_services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_send_notification_success(db_session: AsyncSession):
    service = NotificationService(db_session)
    result = await service.send_notification(
        recipient="pm01",
        message="Task TASK-101 has been assigned to dev01",
        subject="Task Assignment",
    )

    assert result["recipient"] == "pm01"
    assert result["status"] == "sent"
    assert "assigned to dev01" in result["message"]


@pytest.mark.asyncio
async def test_send_notification_by_email(db_session: AsyncSession):
    service = NotificationService(db_session)
    result = await service.send_notification(
        recipient="sam.rivera@example.com",
        message="Please review pending tasks",
    )
    assert result["recipient"] == "sam.rivera@example.com"
    assert result["status"] == "sent"


@pytest.mark.asyncio
async def test_send_notification_invalid_recipient(db_session: AsyncSession):
    service = NotificationService(db_session)
    with pytest.raises(ValueError, match="not found in team directory"):
        await service.send_notification(
            recipient="nonexistent_user",
            message="Hello",
        )


@pytest.mark.asyncio
async def test_send_notification_idempotency(db_session: AsyncSession):
    service = NotificationService(db_session)
    key = "notify:TASK-101:dev01"

    res1 = await service.send_notification(
        recipient="pm01",
        message="Task assigned",
        idempotency_key=key,
    )

    res2 = await service.send_notification(
        recipient="pm01",
        message="Task assigned",
        idempotency_key=key,
    )

    assert res1["id"] == res2["id"]

    all_sent = await service.get_sent_notifications("pm01")
    matching = [n for n in all_sent if n.get("idempotency_key") == key]
    assert len(matching) == 1


@pytest.mark.asyncio
async def test_get_sent_notifications_with_limit(db_session: AsyncSession):
    service = NotificationService(db_session)
    await service.send_notification("pm01", "Message 1")
    await service.send_notification("pm01", "Message 2")
    await service.send_notification("pm01", "Message 3")

    results = await service.get_sent_notifications(recipient="pm01", limit=2)
    assert len(results) == 2
