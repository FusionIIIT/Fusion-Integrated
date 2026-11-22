"""Tests for Celery beat schedule, task registration, and automated transitions."""

from datetime import timedelta

import pytest
from django.utils import timezone

from config.celery import app
from modules.superadmin.models import RoleAssignmentRecord, UserAccountRecord
from modules.superadmin.schedule import BEAT_SCHEDULE
from modules.superadmin.tasks import (
    activate_scheduled_roles_task,
    expire_reversibility_windows_task,
    expire_roles_task,
)

pytestmark = pytest.mark.django_db


def test_every_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values() if entry["task"] not in app.tasks]
    assert not missing, f"Scheduled tasks missing from celery registry: {missing}"


def test_required_recurring_jobs_are_scheduled():
    tasks = {entry["task"] for entry in BEAT_SCHEDULE.values()}
    assert "superadmin.finalize_archived_user_reversibility_expiry" in tasks
    assert "superadmin.activate_scheduled_roles" in tasks
    assert "superadmin.expire_time_bound_roles" in tasks


@pytest.mark.parametrize("name,entry", sorted(BEAT_SCHEDULE.items()))
def test_each_entry_expires_before_next_run(name, entry):
    assert entry["options"]["expires"] > 0


def test_expire_reversibility_windows_task_advances_expired_users():
    """BW-SA-08 Transition 2: Scheduled task finalizes expired reversible accounts."""
    now = timezone.now()
    # User 1: Window has expired -> should transition to ARCHIVED_PERMANENT
    u1 = UserAccountRecord.objects.create(
        user_id=8101,
        institute_id="24BCS8101",
        email="u8101@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=95),
        reversibility_expires_at=now - timedelta(days=5),
    )
    # User 2: Window still active -> remains ARCHIVED_REVERSIBLE
    u2 = UserAccountRecord.objects.create(
        user_id=8102,
        institute_id="24BCS8102",
        email="u8102@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=10),
        reversibility_expires_at=now + timedelta(days=80),
    )

    count = expire_reversibility_windows_task()
    assert count >= 1

    u1.refresh_from_db()
    u2.refresh_from_db()

    assert u1.activation_status == "ARCHIVED_PERMANENT"
    assert u2.activation_status == "ARCHIVED_REVERSIBLE"


def test_activate_scheduled_roles_task():
    """BW-SA-04: Scheduled role activated when valid_from is reached."""
    now = timezone.now()
    r = RoleAssignmentRecord.objects.create(
        user_id=8201,
        role_name="Course Instructor",
        valid_from=now - timedelta(minutes=5),
        status="SCHEDULED",
        assigned_by_user_id=1,
    )

    count = activate_scheduled_roles_task()
    assert count >= 1

    r.refresh_from_db()
    assert r.status == "ACTIVE"


def test_expire_roles_task():
    """BW-SA-03: Time-bound role expired when valid_to is passed."""
    now = timezone.now()
    r = RoleAssignmentRecord.objects.create(
        user_id=8301,
        role_name="Course Instructor",
        valid_from=now - timedelta(days=60),
        valid_to=now - timedelta(days=1),
        status="ACTIVE",
        assigned_by_user_id=1,
    )

    count = expire_roles_task()
    assert count >= 1

    r.refresh_from_db()
    assert r.status == "EXPIRED"
