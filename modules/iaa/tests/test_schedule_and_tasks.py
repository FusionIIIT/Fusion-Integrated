"""Scheduled tasks and beat configuration tests."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from config.celery import app
from modules.iaa.models import (
    ExpenseVoucherRequest,
    IAAConfiguration,
    RequestStatus,
    TAClaim,
    TAClaimStatus,
)
from modules.iaa.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.iaa.tasks import escalate_overdue_approvals

pytestmark = pytest.mark.django_db


def test_every_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values() if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


def test_every_scheduled_task_is_routed():
    for task_name in [entry["task"] for entry in BEAT_SCHEDULE.values()]:
        assert task_name in TASK_ROUTES
        assert "queue" in TASK_ROUTES[task_name]


def test_beat_schedule_entry_options():
    for entry in BEAT_SCHEDULE.values():
        assert entry["options"]["expires"] > 0


def test_escalate_overdue_approvals_task():
    IAAConfiguration.objects.create(
        financial_year="2026-2027",
        approval_timeout_days=3,
        is_active=True,
    )
    overdue_time = timezone.now() - timedelta(days=5)
    recent_time = timezone.now() - timedelta(days=1)

    req_overdue = ExpenseVoucherRequest.objects.create(
        user_id=101,
        department="CSE",
        request_type="expense",
        title="Old Req",
        total_amount=Decimal("100.00"),
        status=RequestStatus.FINANCE_VALIDATED,
        approval_assigned_at=overdue_time,
    )
    req_recent = ExpenseVoucherRequest.objects.create(
        user_id=102,
        department="ECE",
        request_type="expense",
        title="Recent Req",
        total_amount=Decimal("100.00"),
        status=RequestStatus.FINANCE_VALIDATED,
        approval_assigned_at=recent_time,
    )
    ta_overdue = TAClaim.objects.create(
        user_id=103,
        department="ME",
        purpose="Trip",
        departure_date="2026-04-01",
        arrival_date="2026-04-05",
        source_location="DEL",
        destination_location="BOM",
        claimed_amount=Decimal("60000.00"),
        status=TAClaimStatus.APPROVAL_PENDING,
        approval_assigned_at=overdue_time,
    )

    escalated_count = escalate_overdue_approvals()
    assert escalated_count == 2

    req_overdue.refresh_from_db()
    req_recent.refresh_from_db()
    ta_overdue.refresh_from_db()

    assert req_overdue.status == RequestStatus.ESCALATED
    assert req_overdue.assigned_approver_role == "Director"
    assert req_recent.status == RequestStatus.FINANCE_VALIDATED
    assert ta_overdue.status == TAClaimStatus.ESCALATED
