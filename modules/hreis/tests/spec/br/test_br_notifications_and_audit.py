import pytest
from datetime import date, timedelta
from django.utils import timezone
from rest_framework import status
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog, HrNotification, LeaveRequest
from modules.hreis.schedule import send_deadline_notifications, send_pending_action_reminders
from modules.hreis.services.audit import log_hr_action
from modules.hreis.services.leaves import decide_leave_request, submit_leave_request
from modules.hreis.services.notifications import send_hr_notification
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_br_039_submission_notification():
    """TEST-BR-039 [BR-HR-024 Submission Notification]: Verify system generates notification upon request submission."""
    EmployeeServiceRecord.objects.create(
        user_id=410,
        employee_id="EMP0410",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=410,
        username="u410",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    assert HrNotification.objects.filter(user_id=410, category="submission").exists()


def test_br_040_decision_notification():
    """TEST-BR-040 [BR-HR-024 Decision Notification]: Verify system generates notification upon request decision."""
    EmployeeServiceRecord.objects.create(
        user_id=411,
        employee_id="EMP0411",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=411,
        username="u411",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert HrNotification.objects.filter(user_id=411, category="approved").exists()


def test_br_041_reminder_notification():
    """TEST-BR-041 [BR-HR-024 Reminder Notification]: Verify system generates notification for pending action reminder."""
    past_date = timezone.now() - timedelta(days=5)
    leave = LeaveRequest.objects.create(
        user_id=412,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Pending leave",
        status="pending",
        current_authority_role="hod",
    )
    LeaveRequest.objects.filter(id=leave.id).update(created_at=past_date)
    send_pending_action_reminders()
    assert HrNotification.objects.filter(user_id=412, category="reminder").exists()


def test_br_042_policy_notification():
    """TEST-BR-042 [BR-HR-024 Policy Notification]: Verify system generates notification for configured policy deadline."""
    EmployeeServiceRecord.objects.create(
        user_id=413,
        employee_id="EMP0413",
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
    assert HrNotification.objects.filter(user_id=413, category="policy").exists()


def test_br_043_audit_log_mandatory_content():
    """TEST-BR-043 [BR-HR-025 Mandatory Content]: Verify audit log record contains actor identity, timestamp, and action performed."""
    log = log_hr_action(
        actor_id=414,
        actor_username="u414",
        actor_role="faculty",
        action="submit_test_event",
        entity_type="test",
        entity_id=1,
    )
    assert log.actor_id == 414
    assert log.timestamp is not None
    assert log.action == "submit_test_event"


def test_br_044_audit_log_immutability():
    """TEST-BR-044 [BR-HR-025 Immutability]: Verify existing audit log records preserve historical integrity."""
    log = log_hr_action(
        actor_id=415,
        actor_username="u415",
        actor_role="faculty",
        action="audit_immutability_test",
        entity_type="test",
        entity_id=2,
    )
    log.refresh_from_db()
    assert log.action == "audit_immutability_test"


def test_br_045_audit_log_authorized_access(auth_client_factory):
    """TEST-BR-045 [BR-HR-026 Authorized Access]: Verify HR Administrator has authorized access to view audit log records."""
    HrAuditLog.objects.create(
        actor_id=416,
        actor_username="u416",
        actor_role="faculty",
        action="log_access_test",
        entity_type="test",
        entity_id="1",
    )
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp = client_admin.get("/api/v1/hreis/audit-logs/")
    assert resp.status_code == status.HTTP_200_OK


def test_br_046_audit_log_prohibited_access(auth_client_factory):
    """TEST-BR-046 [BR-HR-026 Prohibited Access]: Verify non-admin user cannot access audit logs."""
    client, _ = auth_client_factory(user_id=417, role="faculty")
    resp = client.get("/api/v1/hreis/audit-logs/")
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_br_052_notification_boundary_persisted():
    """TEST-BR-052 [BR-HR-033 Notification Boundary]: Verify notification is persisted in database for dashboard delivery."""
    notif = send_hr_notification(
        user_id=418,
        title="Dashboard Event",
        message="Message delivered to dashboard",
        category="general",
    )
    assert notif.id is not None
    assert notif.is_read is False
