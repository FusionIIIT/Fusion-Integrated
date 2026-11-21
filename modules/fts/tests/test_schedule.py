"""Tests for FTS scheduled Celery tasks and management commands."""
import pytest
from django.core.management import call_command

from modules.fts.models.audit import NotificationEvent
from modules.fts.services.notifications import trigger_notification
from modules.fts.tasks import dispatch_pending_notifications, verify_audit_integrity

pytestmark = pytest.mark.django_db


def test_dispatch_pending_notifications_task():
    trigger_notification(
        event_type="FILE_RECEIVED",
        recipient_user_id=101,
        payload={"file_id": 1, "test": True},
    )
    assert NotificationEvent.objects.filter(delivered=False).count() == 1

    dispatched = dispatch_pending_notifications()
    assert dispatched >= 1
    assert NotificationEvent.objects.filter(delivered=False).count() == 0


def test_verify_audit_integrity_task():
    assert verify_audit_integrity() is True


def test_fts_scheduled_work_status_command():
    call_command("fts_scheduled_work_status", max_lag=3600)
