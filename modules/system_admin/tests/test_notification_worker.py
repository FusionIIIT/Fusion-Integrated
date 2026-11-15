"""Verification tests for BR-SA-023: Notification Outbox Worker & 1-Hour SLA.

Traceability: CFR-SA-019, AFR-SA-068..071B, BR-SA-023.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from modules.system_admin.constants import NotificationChannel, NotificationStatus
from modules.system_admin.models import NotificationOutbox
from modules.system_admin.services import notifications as notif_service


@patch("modules.system_admin.models.NotificationOutbox.objects")
def test_queue_notification_creates_pending_record(mock_outbox):
    """Queues a pending notification for asynchronous outbox delivery."""
    mock_record = MagicMock(spec=NotificationOutbox)
    mock_outbox.create.return_value = mock_record

    notif_service.queue_notification(
        recipient_id=10,
        email="user10@iiitdmj.ac.in",
        channel=NotificationChannel.EMAIL,
        template_code="role_expiry",
        subject="Role Expiry Notice",
        body="Your tenure as Warden will expire in 7 days.",
    )

    mock_outbox.create.assert_called_once()
    kwargs = mock_outbox.create.call_args[1]
    assert kwargs["recipient_id"] == 10
    assert kwargs["channel"] == NotificationChannel.EMAIL
    assert kwargs["recipient_email"] == "user10@iiitdmj.ac.in"
    assert "Warden" in kwargs["body"]


@patch("modules.system_admin.models.NotificationOutbox.objects")
@patch("modules.system_admin.services.notifications.send_mail")
def test_deliver_pending_notifications_batch_delivery(mock_mail, mock_outbox):
    """Drains pending notifications and updates status to sent."""
    n1 = MagicMock(spec=NotificationOutbox)
    n1.id = 1
    n1.channel = NotificationChannel.EMAIL
    n1.recipient_email = "test1@iiitdmj.ac.in"
    n1.subject = "Test Notice 1"
    n1.body = "Body 1"
    n1.retry_count = 0

    n2 = MagicMock(spec=NotificationOutbox)
    n2.id = 2
    n2.channel = NotificationChannel.EMAIL
    n2.recipient_email = "test2@iiitdmj.ac.in"
    n2.subject = "Test Notice 2"
    n2.body = "Body 2"
    n2.retry_count = 0

    mock_outbox.filter.return_value.order_by.return_value = [n1, n2]

    results = notif_service.deliver_pending_notifications(batch_size=50)

    assert results["delivered"] == 2
    assert results["failed"] == 0
    assert n1.status == NotificationStatus.SENT
    assert n2.status == NotificationStatus.SENT
    assert mock_mail.call_count == 2
