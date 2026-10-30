import shutil
from pathlib import Path

import pytest

from app.services.notification_service import (
    DEFAULT_TEAM,
    DEFAULT_TEMPLATES,
    NotificationService,
    clear_sent_notifications,
    get_sent_notifications,
    send_notification,
    sent_messages,
    sent_notifications,
)
from app.tools.notification_tools import send_notification_tool


@pytest.fixture
def temp_notification_service(tmp_path: Path) -> NotificationService:
    """Fixture providing isolated NotificationService backed by temporary data files."""
    temp_team = tmp_path / "team_directory.json"
    temp_templates = tmp_path / "notification_templates.json"
    shutil.copyfile(DEFAULT_TEAM, temp_team)
    shutil.copyfile(DEFAULT_TEMPLATES, temp_templates)
    return NotificationService(team_path=temp_team, templates_path=temp_templates)


def test_send_notification_success(
    temp_notification_service: NotificationService,
) -> None:
    """Verify sending notification to a valid team member logs message."""
    res = temp_notification_service.send_notification(
        recipient="pm01",
        message="Review ready for payments API",
    )
    assert res["status"] == "sent"
    assert res["recipient"] == "pm01"
    assert res["recipient_name"] == "Sam Rivera"
    assert res["recipient_email"] == "sam.rivera@example.com"
    assert res["message"] == "Review ready for payments API"
    assert len(temp_notification_service.sent_notifications) == 1


def test_send_notification_inspect_logs() -> None:
    """Verify module-level send_notification stores records in inspectable list."""
    clear_sent_notifications()
    assert len(get_sent_notifications()) == 0

    res = send_notification("dev01", "Task assigned to dev01")
    assert res["status"] == "sent"
    assert len(sent_notifications) == 1
    assert len(sent_messages) == 1
    assert sent_notifications[0]["recipient"] == "dev01"
    assert sent_notifications[0]["message"] == "Task assigned to dev01"

    clear_sent_notifications()
    assert len(sent_notifications) == 0


def test_send_notification_template_rendering(
    temp_notification_service: NotificationService,
) -> None:
    """Verify template variables are rendered in notification subject and body."""
    res = temp_notification_service.send_notification(
        recipient="pm01",
        message="",
        template_id="NOTIFY-TASK-ASSIGNED",
        project="PLAT",
        task_id="TASK-101",
        title="Payment Gateway Integration",
        assignee_name="Alex Morgan",
        priority="High",
        due_date="2026-10-30",
    )
    assert res["status"] == "sent"
    assert res["template_id"] == "NOTIFY-TASK-ASSIGNED"
    assert (
        "[PLAT] Task assigned: TASK-101 — Payment Gateway Integration" == res["subject"]
    )
    assert "Hi Sam Rivera," in res["message"]
    assert "Task: TASK-101 — Payment Gateway Integration" in res["message"]
    assert "Priority: High" in res["message"]


def test_send_notification_channel_broadcast(
    temp_notification_service: NotificationService,
) -> None:
    """Verify channel recipients are accepted for broadcasts."""
    res = temp_notification_service.send_notification(
        recipient="task-updates",
        message="All overdue tasks updated",
    )
    assert res["status"] == "sent"
    assert res["recipient"] == "task-updates"
    assert res["message"] == "All overdue tasks updated"


def test_send_notification_validation_errors(
    temp_notification_service: NotificationService,
) -> None:
    """Verify validation errors for missing or invalid recipients and templates."""
    with pytest.raises(ValueError, match="Recipient is required"):
        temp_notification_service.send_notification("", "Hello")

    with pytest.raises(ValueError, match="Recipient 'unknown_user' not found"):
        temp_notification_service.send_notification("unknown_user", "Hello")

    with pytest.raises(ValueError, match="Template 'INVALID-TPL' not found"):
        temp_notification_service.send_notification(
            "pm01", "Hello", template_id="INVALID-TPL"
        )


def test_send_notification_tool_wrapper() -> None:
    """Verify LangChain tool wrapper invokes notification sending."""
    clear_sent_notifications()
    res = send_notification_tool.invoke(
        {"recipient": "dev02", "message": "Pairing session scheduled"}
    )
    assert res["status"] == "sent"
    assert res["recipient"] == "dev02"
    assert len(sent_notifications) >= 1
    clear_sent_notifications()
