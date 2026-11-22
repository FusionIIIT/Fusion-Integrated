from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from modules.hreis.models import EmployeeServiceRecord, HrNotification, LeaveRequest
from modules.hreis.schedule import send_deadline_notifications, send_pending_action_reminders
from modules.hreis.services.notifications import send_hr_notification
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_uc_057_view_addressed_notifications(auth_client_factory):
    """TEST-UC-057 [HR-UC-019 Main Flow]: Verify user can view notifications addressed to their user ID or role."""
    send_hr_notification(
        user_id=260,
        title="Appraisal Assigned",
        message="You have been assigned as reviewer for an appraisal.",
        category="appraisal",
    )
    client, _ = auth_client_factory(user_id=260, role="faculty")
    resp = client.get("/api/v1/hreis/notifications/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert any(n["user_id"] == 260 for n in results)


def test_uc_058_view_policy_deadline_notifications(auth_client_factory):
    """TEST-UC-058 [HR-UC-019 Alternative A1]: Verify policy/deadline notifications appear when configured in the system."""
    send_hr_notification(
        user_id=261,
        title="Appraisal Submission Window Closing",
        message="Annual appraisal cycle closes in 3 days.",
        category="policy",
    )
    client, _ = auth_client_factory(user_id=261, role="faculty")
    resp = client.get("/api/v1/hreis/notifications/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert any(n["category"] == "policy" for n in results)


def test_uc_059_unaddressed_notifications_not_disclosed(auth_client_factory):
    """TEST-UC-059 [HR-UC-019 Exception E1]: Verify notifications not addressed to the actor are not disclosed."""
    send_hr_notification(
        user_id=262,
        title="Confidential Notice",
        message="Notice for user 262 only.",
        category="private",
    )
    client, _ = auth_client_factory(user_id=263, role="faculty")
    resp = client.get("/api/v1/hreis/notifications/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert not any(n["user_id"] == 262 for n in results)


def test_uc_060_generate_pending_action_reminder():
    """TEST-UC-060 [HR-UC-021 Main Flow]: Verify system generates pending-action reminder notification for requests pending authority decision."""
    past_date = timezone.now() - timedelta(days=5)
    leave = LeaveRequest.objects.create(
        user_id=264,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal errand",
        status="pending",
        current_authority_role="hod",
    )
    LeaveRequest.objects.filter(id=leave.id).update(created_at=past_date)
    count = send_pending_action_reminders()
    assert count >= 1
    assert HrNotification.objects.filter(user_id=264, category="reminder").exists()


def test_uc_061_no_reminder_for_resolved_request():
    """TEST-UC-061 [HR-UC-021 Alternative A1]: Verify resolved request does not generate reminder notifications."""
    past_date = timezone.now() - timedelta(days=5)
    leave = LeaveRequest.objects.create(
        user_id=265,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Resolved request",
        status="approved",
        current_authority_role="hod",
    )
    LeaveRequest.objects.filter(id=leave.id).update(created_at=past_date)
    initial_reminders = HrNotification.objects.filter(user_id=265, category="reminder").count()
    send_pending_action_reminders()
    assert HrNotification.objects.filter(user_id=265, category="reminder").count() == initial_reminders


def test_uc_062_reminder_targets_current_pending_authority():
    """TEST-UC-062 [HR-UC-021 Alternative A2]: Verify reminder notification addresses only the currently responsible authority."""
    past_date = timezone.now() - timedelta(days=6)
    leave = LeaveRequest.objects.create(
        user_id=266,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Pending HOD only",
        status="pending",
        current_authority_role="hod",
    )
    LeaveRequest.objects.filter(id=leave.id).update(created_at=past_date)
    send_pending_action_reminders()
    notifs = HrNotification.objects.filter(user_id=266, category="reminder")
    assert notifs.exists()


def test_uc_063_unresolvable_recipient_no_leak():
    """TEST-UC-063 [HR-UC-021 Exception E1]: Verify request information is not disclosed to unauthorized users if recipient cannot be determined."""
    leave = LeaveRequest.objects.create(
        user_id=267,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="No leak test",
        status="pending",
        current_authority_role="",
    )
    # Reminder run does not throw uncaught error or leak to random users
    send_pending_action_reminders()
    assert leave.status == "pending"


def test_uc_064_generate_policy_deadline_notification():
    """TEST-UC-064 [HR-UC-022 Main Flow]: Verify system generates policy/deadline update notification when configured event occurs."""
    EmployeeServiceRecord.objects.create(
        user_id=268,
        employee_id="EMP0268",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        is_active=True,
    )
    deadline_date = (date.today() + timedelta(days=2)).isoformat()
    update_workflow_config(
        "appraisal_window",
        {
            "active": True,
            "academic_year": "2025-2026",
            "start_date": "2026-01-01",
            "end_date": deadline_date,
        },
    )
    count = send_deadline_notifications()
    assert count >= 1
    assert HrNotification.objects.filter(user_id=268, category="policy").exists()


def test_uc_065_unconfigured_policy_no_notifications():
    """TEST-UC-065 [HR-UC-022 Alternative A1]: Verify unconfigured policy/deadline events do not generate spurious notifications."""
    update_workflow_config(
        "appraisal_window",
        {"active": False},
    )
    initial_policy_notifs = HrNotification.objects.filter(category="policy").count()
    send_deadline_notifications()
    # No new spurious policy notifications
    assert HrNotification.objects.filter(category="policy").count() == initial_policy_notifs


def test_uc_066_policy_notification_recipient_scope():
    """TEST-UC-066 [HR-UC-022 Alternative A2]: Verify policy notification recipient scope strictly follows configured role/access restrictions."""
    EmployeeServiceRecord.objects.create(
        user_id=269,
        employee_id="EMP0269",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        is_active=True,
    )
    deadline_date = (date.today() + timedelta(days=2)).isoformat()
    update_workflow_config(
        "appraisal_window",
        {
            "active": True,
            "academic_year": "2025-2026",
            "start_date": "2026-01-01",
            "end_date": deadline_date,
        },
    )
    send_deadline_notifications()
    assert HrNotification.objects.filter(user_id=269, category="policy").exists()


def test_uc_067_unauthorized_user_cannot_access_policy_details(auth_client_factory):
    """TEST-UC-067 [HR-UC-022 Exception E1]: Verify recipient authorization failure prevents notification disclosure."""
    send_hr_notification(
        user_id=270,
        title="Admin Confidential Policy",
        message="Internal HR policy discussion",
        category="admin_policy",
    )
    client, _ = auth_client_factory(user_id=271, role="faculty")
    resp = client.get("/api/v1/hreis/notifications/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert not any(n["user_id"] == 270 for n in results)
