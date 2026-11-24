"""Tests for Celery scheduled role tenure transitions (CFR-DEPT-016, BR-DEPT-021..024)."""

import datetime

import pytest
from django.utils import timezone

from modules.dept.models import Department, DepartmentRoleAssignment
from modules.dept.services.roles import evaluate_role_transitions
from modules.dept.tasks import evaluate_role_transitions_task

pytestmark = pytest.mark.django_db


@pytest.fixture
def dept():
    return Department.objects.create(code="CSE", name="Computer Science and Engineering")


def test_scheduled_role_activation_and_expiry(dept):
    now = timezone.now()
    past_start = now - datetime.timedelta(days=2)
    past_end = now - datetime.timedelta(hours=1)
    future_end = now + datetime.timedelta(days=365)

    # 1. Outgoing active assignment that has reached its end_date
    expired_assign = DepartmentRoleAssignment.objects.create(
        department=dept,
        role_name="HOD",
        user_id="old_hod",
        start_date=past_start - datetime.timedelta(days=365),
        end_date=past_end,
        status="ACTIVE",
        assigned_by_id="admin_1",
    )

    # 2. Incoming scheduled assignment whose start_date is now past
    scheduled_assign = DepartmentRoleAssignment.objects.create(
        department=dept,
        role_name="HOD",
        user_id="new_hod",
        start_date=past_end,
        end_date=future_end,
        status="SCHEDULED",
        assigned_by_id="admin_1",
    )

    # Execute celery task
    result_str = evaluate_role_transitions_task()
    assert "Processed" in result_str

    expired_assign.refresh_from_db()
    scheduled_assign.refresh_from_db()

    assert expired_assign.status in {"EXPIRED", "REVOKED"}
    assert scheduled_assign.status == "ACTIVE"

    # Verify idempotency on second execution
    count2 = evaluate_role_transitions()
    assert count2 == 0
