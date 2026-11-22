from datetime import date, time, timedelta
from types import SimpleNamespace

import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from fusion_auth.client import UserRef
from modules.badms import tasks
from modules.badms.models import (
    ArchiveRequest,
    AuditEvent,
    BackupRun,
    BackupSchedule,
    NotificationOutbox,
    StorageThreshold,
)

pytestmark = pytest.mark.django_db


def archive_request(*, user_id=4101, size=100, **kwargs):
    return ArchiveRequest.objects.create(
        user_id=user_id,
        department="CSE",
        requester_email="student@example.test",
        file_name="data.zip",
        file_date=date(2026, 11, 20),
        owners=["Student"],
        file_type="application/zip",
        reason="Test retention",
        attachment_key=kwargs.pop("attachment_key", "incoming/data.zip"),
        attachment_size_bytes=size,
        **kwargs,
    )


def test_notification_delivery_marks_outbox_sent():
    row = NotificationOutbox.objects.create(
        recipient="student@example.test", subject="Done", body="Completed."
    )

    assert tasks.deliver_notifications() == 1

    row.refresh_from_db()
    assert row.status == "sent"
    assert row.attempts == 1
    assert len(mail.outbox) == 1


def test_due_schedule_creates_run_and_dispatches_worker(monkeypatch):
    now = timezone.now()
    BackupSchedule.objects.create(
        scope="local",
        dataset="test_dataset",
        frequency="daily",
        scheduled_time=time(now.hour, now.minute),
        timezone="UTC",
        updated_by=4102,
    )
    monkeypatch.setattr("modules.badms.services.storage.require_secure_storage", lambda: None)
    monkeypatch.setattr(
        "modules.badms.services.storage.badms_storage",
        lambda: SimpleNamespace(save=lambda name, value: name, delete=lambda name: None),
    )
    dispatched = []
    monkeypatch.setattr(tasks.execute_backup, "delay", dispatched.append)

    assert tasks.run_due_schedules() == 1

    run = BackupRun.objects.get(dataset="test_dataset")
    assert run.trigger == "scheduled"
    assert dispatched == [run.pk]


@override_settings(BADMS_USER_QUOTA_BYTES=100)
def test_threshold_monitor_updates_state_and_audits(monkeypatch):
    archive_request(size=100)
    monkeypatch.setattr(
        "modules.directory.contracts.get_users",
        lambda user_ids: {
            4101: UserRef(
                user_id=4101,
                username="student",
                display_name="Student",
                kind="student",
                department="CSE",
            )
        },
    )

    assert tasks.monitor_storage_thresholds() == 1

    threshold = StorageThreshold.objects.get(user_id=4101)
    assert threshold.usage_bytes == 100
    assert threshold.is_full is True
    assert AuditEvent.objects.filter(action="storage.threshold_changed", outcome="full").exists()


def test_retention_task_deletes_expired_objects_and_records_audit(monkeypatch):
    row = archive_request(
        attachment_key="incoming/data.zip",
        archive_key="archives/data.zip",
        retention_until=timezone.now() - timedelta(days=1),
    )
    deleted = []
    monkeypatch.setattr(
        "modules.badms.services.storage.badms_storage",
        lambda: SimpleNamespace(delete=deleted.append),
    )

    assert tasks.enforce_retention() == 1

    row.refresh_from_db()
    assert set(deleted) == {"incoming/data.zip", "archives/data.zip"}
    assert row.archive_key == ""
    assert row.attachment_key == ""
    assert AuditEvent.objects.filter(
        action="archive.retention_expired", object_id=str(row.pk)
    ).exists()
