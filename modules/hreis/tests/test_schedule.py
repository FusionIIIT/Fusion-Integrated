"""Tests for scheduled jobs (reminders, notifications)."""
from datetime import timedelta
from django.utils import timezone
import pytest

from modules.hreis.models import LeaveRequest, HrNotification, WorkflowConfiguration
from modules.hreis.schedule import send_pending_action_reminders, send_deadline_notifications

pytestmark = pytest.mark.django_db


def test_send_pending_action_reminders():
    # Create an old pending leave
    old_time = timezone.now() - timedelta(days=3)
    leave = LeaveRequest.objects.create(
        user_id=105,
        leave_type="casual",
        start_date="2026-03-01",
        end_date="2026-03-02",
        duration_days=1.0,
        justification="Pending for 3 days",
        status="pending",
    )
    # Manually backdate created_at
    LeaveRequest.objects.filter(id=leave.id).update(created_at=old_time)

    count = send_pending_action_reminders()
    assert count >= 1

    notifs = HrNotification.objects.filter(user_id=105, category="reminder")
    assert notifs.exists()
    assert "Pending Leave Reminder" in notifs.first().title


def test_send_deadline_notifications():
    # Setup appraisal window with deadline approaching
    today = timezone.now().date()
    WorkflowConfiguration.objects.create(
        setting_key="appraisal_window",
        setting_value={
            "active": True,
            "start_date": str(today - timedelta(days=20)),
            "end_date": str(today + timedelta(days=3)),
        },
    )

    count = send_deadline_notifications()
    assert isinstance(count, int)
