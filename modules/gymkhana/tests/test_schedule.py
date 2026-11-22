"""Tests for scheduled notifications worker and management commands."""
import pytest
from django.core import mail
from django.core.management import call_command

from fusion_auth.client import UserRef as IamUser
from modules.gymkhana import schedule, tasks
from modules.gymkhana.models import NotificationOutbox
from modules.gymkhana.services import notifications

pytestmark = pytest.mark.django_db


def test_schedule_and_task_routes_configured():
    assert "gymkhana.deliver-notifications" in schedule.BEAT_SCHEDULE
    assert schedule.BEAT_SCHEDULE["gymkhana.deliver-notifications"]["task"] == (
        "gymkhana.deliver_notifications"
    )
    assert "gymkhana.deliver_notifications" in schedule.TASK_ROUTES


def test_notification_delivery_success(stub_iam):
    stub_iam(users={
        5001: IamUser(
            user_id=5001,
            username="u5001",
            display_name="Person 5001",
            kind="student",
            email="test5001@iiitdmj.ac.in",
        ),
    })
    outbox = NotificationOutbox.objects.create(
        recipient_user_id=5001,
        topic="test.event",
        dedupe_key="test-key-5001",
        subject="Hello Test",
        body="This is a test notification",
        status=NotificationOutbox.Status.PENDING,
    )

    report = notifications.deliver_pending(limit=10)
    assert report["sent"] == 1
    assert report["failed"] == 0

    outbox.refresh_from_db()
    assert outbox.status == NotificationOutbox.Status.SENT
    assert outbox.sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["test5001@iiitdmj.ac.in"]


def test_notification_missing_email_fails(stub_iam):
    stub_iam(users={
        5002: IamUser(
            user_id=5002,
            username="u5002",
            display_name="Person 5002",
            kind="student",
            email="",
        ),
    })
    outbox = NotificationOutbox.objects.create(
        recipient_user_id=5002,
        topic="test.event",
        dedupe_key="test-key-5002",
        subject="Missing Email",
        body="Will fail",
        status=NotificationOutbox.Status.PENDING,
    )

    report = notifications.deliver_pending(limit=10)
    assert report["failed"] == 1

    outbox.refresh_from_db()
    assert outbox.status == NotificationOutbox.Status.FAILED
    assert outbox.attempts == 1
    assert "no email address" in outbox.last_error

    # Retry failed
    retried = notifications.retry_failed()
    assert retried == 1
    outbox.refresh_from_db()
    assert outbox.status == NotificationOutbox.Status.PENDING


def test_celery_task_and_management_command(stub_iam):
    stub_iam(users={
        5003: IamUser(
            user_id=5003,
            username="u5003",
            display_name="Person 5003",
            kind="student",
            email="test5003@iiitdmj.ac.in",
        ),
    })
    NotificationOutbox.objects.create(
        recipient_user_id=5003,
        topic="test.event",
        dedupe_key="test-key-5003",
        subject="Celery Command Test",
        body="Body text",
        status=NotificationOutbox.Status.PENDING,
    )

    # Test celery task function directly
    task_res = tasks.deliver_notifications()
    assert task_res["sent"] == 1

    # Test management command
    NotificationOutbox.objects.create(
        recipient_user_id=5003,
        topic="test.event2",
        dedupe_key="test-key-5003-2",
        subject="Mgmt Test",
        body="Body text 2",
        status=NotificationOutbox.Status.PENDING,
    )
    call_command("send_gymkhana_notifications", limit=5)
