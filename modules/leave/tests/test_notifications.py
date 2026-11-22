"""Tests for notification outbox delivery and scheduled commands."""

from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command

from modules.leave.services.notifications import deliver_pending, enqueue


@pytest.mark.django_db
def test_notification_delivery_success(stub_iam, user_ref):
    from fusion_auth.client import UserRef

    recipient_id = 951
    user = UserRef(
        user_id=recipient_id,
        username=f"u{recipient_id}",
        display_name="Staff 951",
        kind="staff",
        email="staff951@iiitdmj.ac.in",
    )
    stub_iam(users={recipient_id: user})

    outbox = enqueue(
        recipient_user_id=recipient_id,
        topic="test.topic",
        dedupe_key="test-dedupe-1",
        subject="Test notification",
        body="This is a test notification body.",
    )
    assert outbox is not None
    assert outbox.status == "pending"

    # Dedupe check: duplicate key returns None
    dup = enqueue(
        recipient_user_id=recipient_id,
        topic="test.topic",
        dedupe_key="test-dedupe-1",
        subject="Duplicate",
        body="Duplicate body",
    )
    assert dup is None

    result = deliver_pending(limit=10)
    assert result["sent"] == 1
    assert result["failed"] == 0

    outbox.refresh_from_db()
    assert outbox.status == "sent"
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Test notification"
    assert mail.outbox[0].to == ["staff951@iiitdmj.ac.in"]


@pytest.mark.django_db
def test_deliver_leave_notifications_command(stub_iam, user_ref):
    from fusion_auth.client import UserRef

    recipient_id = 952
    user = UserRef(
        user_id=recipient_id,
        username=f"u{recipient_id}",
        display_name="Faculty 952",
        kind="faculty",
        email="faculty952@iiitdmj.ac.in",
    )
    stub_iam(users={recipient_id: user})

    enqueue(
        recipient_user_id=recipient_id,
        topic="test.cmd",
        dedupe_key="test-cmd-1",
        subject="Command notification",
        body="Testing management command",
    )

    out = StringIO()
    call_command("deliver_leave_notifications", "--limit", "50", stdout=out)
    output = out.getvalue()
    assert "sent=1" in output


@pytest.mark.django_db
def test_process_leave_sla_command():
    out = StringIO()
    call_command("process_leave_sla", stdout=out)
    output = out.getvalue()
    assert "reminders=0" in output


@pytest.mark.django_db
def test_leave_celery_tasks():
    from modules.leave.tasks import (
        deliver_leave_notifications,
        process_leave_sla_thresholds,
        run_leave_year_end_processing,
    )

    sla_res = process_leave_sla_thresholds()
    assert "reminders" in sla_res

    notify_res = deliver_leave_notifications()
    assert "sent" in notify_res

    year_end_res = run_leave_year_end_processing()
    assert isinstance(year_end_res, int)
