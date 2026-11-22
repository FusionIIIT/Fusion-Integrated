import pytest
from datetime import date, timedelta
from django.utils import timezone
from modules.hreis.models import HrNotification, LeaveRequest
from modules.hreis.schedule import send_deadline_notifications, send_pending_action_reminders
from modules.hreis.services.notifications import send_hr_notification
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_fr_088_notify_employee_events():
    """TEST-FR-088 [HR-AFR-005]: Verify HR-EIS notifies an Employee about relevant HR request and policy/deadline events."""
    notif = send_hr_notification(
        user_id=240,
        title="Leave Approved",
        message="Your casual leave was approved.",
        category="approval",
    )
    assert notif.id is not None
    assert notif.user_id == 240
    assert notif.category == "approval"


def test_fr_089_notifications_request_submission():
    """TEST-FR-089 [HR-AFR-077]: Verify HR-EIS generates notifications for request submission."""
    from modules.hreis.models import EmployeeServiceRecord
    from modules.hreis.services.leaves import submit_leave_request

    EmployeeServiceRecord.objects.create(
        user_id=241,
        employee_id="EMP0241",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    submit_leave_request(
        user_id=241,
        username="u241",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    notif = HrNotification.objects.filter(user_id=241, category="submission")
    assert notif.exists()


def test_fr_090_notifications_approval_rejection_forwarding():
    """TEST-FR-090 [HR-AFR-078]: Verify HR-EIS generates notifications for approval, rejection, or forwarding."""
    from modules.hreis.models import EmployeeServiceRecord
    from modules.hreis.services.leaves import decide_leave_request, submit_leave_request

    EmployeeServiceRecord.objects.create(
        user_id=242,
        employee_id="EMP0242",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=242,
        username="u242",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Trip",
    )
    decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved",
        actor_id=302,
        actor_username="hod",
        actor_role="hod",
    )
    notif = HrNotification.objects.filter(user_id=242, category="approved")
    assert notif.exists()


def test_fr_091_notifications_pending_action_reminders():
    """TEST-FR-091 [HR-AFR-079]: Verify HR-EIS generates notifications for pending action reminders."""
    past_date = timezone.now() - timedelta(days=5)
    leave = LeaveRequest.objects.create(
        user_id=243,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal errand",
        status="pending",
        current_authority_role="hod",
    )
    LeaveRequest.objects.filter(id=leave.id).update(created_at=past_date)

    reminders = send_pending_action_reminders()
    assert reminders >= 1
    assert HrNotification.objects.filter(user_id=243, category="reminder").exists()


def test_fr_092_notifications_policy_deadline_updates():
    """TEST-FR-092 [HR-AFR-080]: Verify HR-EIS generates notifications for policy or deadline updates."""
    from modules.hreis.models import EmployeeServiceRecord

    EmployeeServiceRecord.objects.create(
        user_id=244,
        employee_id="EMP0244",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        is_active=True,
    )
    deadline_date = (date.today() + timedelta(days=3)).isoformat()
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
    assert HrNotification.objects.filter(user_id=244, category="policy").exists()


def test_fr_093_dashboard_delivery_notifications(auth_client_factory):
    """TEST-FR-093 [HR-AFR-081]: Verify HR-EIS delivers notifications through the system dashboard."""
    send_hr_notification(
        user_id=245,
        title="Welcome Notice",
        message="System onboarding notice",
        category="policy",
    )
    client, _ = auth_client_factory(user_id=245, role="faculty")
    resp = client.get("/api/v1/hreis/notifications/")
    assert resp.status_code == 200
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert len(results) >= 1
    assert results[0]["title"] == "Welcome Notice"


def test_fr_094_email_delivery_channel():
    """TEST-FR-094 [HR-AFR-082]: Verify HR-EIS delivers notifications through official email dispatch channel."""
    pytest.skip("NOT_AUTOMATED: Email delivery infrastructure is external to HR-EIS module")
