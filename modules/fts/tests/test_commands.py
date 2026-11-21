"""Tests for FTS management commands."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.fts.models.audit import NotificationEvent
from modules.fts.models.files import File

pytestmark = pytest.mark.django_db


def test_seed_fts_demo_command():
    call_command("seed_fts_demo")
    assert File.objects.filter(status="DRAFT").exists()
    assert File.objects.filter(status="CIRCULATED").exists()


def test_fts_scheduled_work_status_lag_exceeded():
    """BR-FTS-013: Command exits 1 when pending notification lag exceeds max-lag threshold."""
    past = timezone.now() - timedelta(seconds=120)
    NotificationEvent.objects.create(
        event_type="TEST",
        recipient_user_id=101,
        payload={},
        delivered=False,
    )
    NotificationEvent.objects.filter(event_type="TEST").update(created_at=past)

    with pytest.raises(SystemExit) as exc:
        call_command("fts_scheduled_work_status", max_lag=10)
    assert exc.value.code == 1


def test_fts_scheduled_work_status_integrity_failure(monkeypatch):
    """Command exits 1 when audit integrity check fails."""
    monkeypatch.setattr(
        "modules.fts.management.commands.fts_scheduled_work_status.verify_all_files_audit_integrity",
        lambda: False,
    )
    with pytest.raises(SystemExit) as exc:
        call_command("fts_scheduled_work_status")
    assert exc.value.code == 1
