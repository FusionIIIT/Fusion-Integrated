"""Tests for SLA reminder and escalation processing (BR-EL-032, BR-EL-033, BR-EL-038, EL-UC-021, WF-EL-08)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.leave.models import (
    LeaveActionHistory,
    LeaveBalance,
    LeaveNotificationOutbox,
    LeavePolicyConfig,
)
from modules.leave.services import apply_for_leave, withdraw_application
from modules.leave.services.sla import process_sla_thresholds


@pytest.mark.django_db
def test_sla_reminder_and_escalation():
    user_id = 901
    unit_head_id = 902
    sanctioner_id = 903
    today = date(2026, 11, 2)

    LeavePolicyConfig.objects.create(key="sla.reminder_hours", value=24)
    LeavePolicyConfig.objects.create(key="sla.escalation_hours", value=72)
    LeavePolicyConfig.objects.create(key="sla.escalation_user_id", value=sanctioner_id)

    LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=today,
        end_date=today + timedelta(days=1),
        purpose="CL request",
        unit_head_user_id=unit_head_id,
    )
    assert app.status == "under_review"

    # Step 1: 10 hours later - no reminder, no escalation
    now = app.updated_at + timedelta(hours=10)
    res = process_sla_thresholds(now=now)
    assert res["reminders"] == 0
    assert res["escalations"] == 0

    # Step 2: 25 hours later - reminder triggered
    now = app.updated_at + timedelta(hours=25)
    res = process_sla_thresholds(now=now)
    assert res["reminders"] == 1
    assert res["escalations"] == 0
    assert LeaveActionHistory.objects.filter(application=app, action="sla_reminder").exists()
    assert LeaveNotificationOutbox.objects.filter(
        recipient_user_id=unit_head_id, topic="workflow.reminder"
    ).exists()

    # Step 3: Running again at 30 hours - no duplicate reminder
    now = app.updated_at + timedelta(hours=30)
    res = process_sla_thresholds(now=now)
    assert res["reminders"] == 0

    # Step 4: 80 hours later - escalation triggered
    now = app.updated_at + timedelta(hours=80)
    res = process_sla_thresholds(now=now)
    assert res["escalations"] == 1
    assert LeaveActionHistory.objects.filter(application=app, action="sla_escalation").exists()
    assert LeaveNotificationOutbox.objects.filter(
        recipient_user_id=sanctioner_id, topic="workflow.escalation"
    ).exists()


@pytest.mark.django_db
def test_sla_ignores_non_pending_tasks():
    user_id = 904
    unit_head_id = 905
    today = date(2026, 11, 2)

    LeavePolicyConfig.objects.create(key="sla.reminder_hours", value=24)
    LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=today,
        end_date=today + timedelta(days=1),
        purpose="CL request",
        unit_head_user_id=unit_head_id,
    )
    withdraw_application(user_id=user_id, application_id=app.pk, reason="Cancelled plans")
    app.refresh_from_db()
    assert app.status == "withdrawn"

    # Fast forward 48 hours
    now = timezone.now() + timedelta(hours=48)
    res = process_sla_thresholds(now=now)
    assert res["reminders"] == 0
    assert res["escalations"] == 0
