"""Tests for FTS scheduled Celery tasks, idempotence, and merged Celery configuration.

Validates BR-FTS-013, BR-FTS-014, AFR-FTS-024.
"""
from __future__ import annotations

import pytest
from django.core.management import call_command

from config.celery import app as celery_app
from modules.fts.models.audit import NotificationEvent
from modules.fts.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.fts.services.notifications import trigger_notification
from modules.fts.tasks import dispatch_pending_notifications, verify_audit_integrity

pytestmark = pytest.mark.django_db


def test_celery_schedule_and_routes_merged():
    """Verify that FTS beat schedule and task routes are merged into Celery configuration."""
    for key, spec in BEAT_SCHEDULE.items():
        assert key in celery_app.conf.beat_schedule, f"Missing {key} in Celery beat_schedule"
        assert celery_app.conf.beat_schedule[key]["task"] == spec["task"]

    for pattern, route in TASK_ROUTES.items():
        assert pattern in celery_app.conf.task_routes, f"Missing route for {pattern} in task_routes"
        assert celery_app.conf.task_routes[pattern]["queue"] == route["queue"]


def test_dispatch_pending_notifications_task_runs_twice_for_single_effect():
    """BR-FTS-013 & AFR-FTS-024: Running task twice dispatches pending events once."""
    trigger_notification(
        event_type="FILE_RECEIVED",
        recipient_user_id=101,
        payload={"file_id": 1, "test": True},
    )
    assert NotificationEvent.objects.filter(delivered=False).count() == 1

    # First run: dispatches pending events
    first_count = dispatch_pending_notifications()
    assert first_count == 1
    assert NotificationEvent.objects.filter(delivered=False).count() == 0

    # Second run: no-op, single effect verified
    second_count = dispatch_pending_notifications()
    assert second_count == 0
    assert NotificationEvent.objects.filter(delivered=False).count() == 0


def test_verify_audit_integrity_task_runs_twice_for_idempotence():
    """BR-FTS-014: Audit integrity verification is idempotent across consecutive runs."""
    first_valid = verify_audit_integrity()
    assert first_valid is True

    second_valid = verify_audit_integrity()
    assert second_valid is True


def test_fts_scheduled_work_status_command():
    """Verify management command fts_scheduled_work_status runs without error."""
    call_command("fts_scheduled_work_status", max_lag=3600)
