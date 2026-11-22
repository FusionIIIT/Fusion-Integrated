"""Schedule tests for System Admin automated periodic tasks."""
from datetime import date, timedelta

import pytest

from modules.system_admin.models.role_assignment import RoleAssignment
from modules.system_admin.models.user_account import UserAccount
from modules.system_admin.tasks import process_role_expiries_task

pytestmark = pytest.mark.django_db


def test_process_role_expiries_task_runs_idempotently():
    today = date.today()
    user = UserAccount.objects.create(
        user_id=8801,
        institute_id="EXP8801",
        username="exp_user",
        email="exp@iiitdmj.ac.in",
        user_type="faculty",
        department="CSE",
        status="active",
    )
    RoleAssignment.objects.create(
        user_id=user.user_id,
        role_code="faculty",
        status="active",
        start_date=today - timedelta(days=60),
        end_date=today - timedelta(days=1),
        reason="Expired tenure",
        assigned_by=1,
    )

    first_run = process_role_expiries_task()
    assert first_run == 1

    second_run = process_role_expiries_task()
    assert second_run == 0


def test_schedule_definitions():
    from modules.system_admin.schedule import BEAT_SCHEDULE, TASK_ROUTES

    assert "system_admin.process-role-expiries" in BEAT_SCHEDULE
    assert "system_admin.process_role_expiries" in TASK_ROUTES
