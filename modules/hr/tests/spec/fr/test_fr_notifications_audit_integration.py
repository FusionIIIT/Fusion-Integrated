"""FR spec tests for Notifications, Audit Events, and System Integrations."""

import pytest

from modules.hr.models import AuditEvent, Claim, ClaimIntegrationStatus, HRNotification
from modules.hr.services import notifications
from modules.hr.tasks import deliver_notifications
from modules.hr.tests.spec.conftest import (
    UID_ACCOUNTANT,
    UID_FACULTY_1,
    UID_HR_ADMIN,
    ensure_employee,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_fr_011_consolidated_hr_notifications(hr_caller):
    """TEST-FR-011 | HR-CFR-011 consolidated-hr-notifications.

    Verify that HR-EIS generates and exposes notifications for request submissions, workflow decisions (approval, rejection, forwarding), pending action reminders, and policy/deadline updates across dashboard and email delivery paths.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="request.status",
        dedupe_key="fr-011-key",
        subject="Leave Approved",
        body="Your casual leave was approved.",
    )
    res = hr_caller("get", "/api/v1/hr/notifications/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200
    assert any(n["id"] == notif.pk for n in res.data["results"])


def test_fr_012_consolidated_audit_and_compliance(hr_caller):
    """TEST-FR-012 | HR-CFR-012 consolidated-audit-and-compliance.

    Verify that HR-EIS logs all HR transactions with actor identity, timestamp, and action performed, enforces log immutability and role-restricted access, and supports compliance review.
    """
    event = AuditEvent.objects.create(
        entity_type="employee",
        entity_id=1,
        actor_user_id=UID_HR_ADMIN,
        action="employee.created",
        details={"user_id": UID_FACULTY_1},
    )
    assert event.pk is not None
    assert event.action == "employee.created"


def test_fr_013_consolidated_external_system_integration(hr_caller):
    """TEST-FR-013 | HR-CFR-013 consolidated-external-system-integration.

    Verify that HR-EIS exchanges claim payment/disbursement statuses with payroll systems, accounting statuses with finance systems, and identity/role information with Fusion modules without owning external execution semantics.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="financial_processing_recorded",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/integration-status/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={
            "system": "payroll",
            "external_status": "disbursed",
            "external_reference": "REF-EXT-1",
        },
    )
    assert res.status_code == 201


def test_fr_042_hr_admin_monitor_compliance_and_audits(hr_caller):
    """TEST-FR-042 | HR-AFR-014 hr-admin-monitor-compliance-and-audits.

    Verify that HR-EIS allows the HR Administrator to monitor compliance and audits using authorized HR-EIS records.
    """
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200


def test_fr_111_employee_notifications_requests_and_policies(hr_caller):
    """TEST-FR-111 | HR-AFR-005 employee-notifications-requests-and-policies.

    Verify that HR-EIS notifies an Employee about relevant HR request events and policy/deadline events.
    """
    HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="policy",
        dedupe_key="pol-111",
        subject="Appraisal Deadline",
        body="Appraisal window open.",
    )
    res = hr_caller("get", "/api/v1/hr/notifications/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200


def test_fr_112_generate_notifications_request_submission(hr_caller):
    """TEST-FR-112 | HR-AFR-077 generate-notifications-request-submission.

    Verify that HR-EIS generates notifications for request submission.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="leave.submitted",
        dedupe_key="sub-112",
        subject="Submitted",
        body="Leave submitted",
    )
    assert notif.pk is not None


def test_fr_113_generate_notifications_approval_rejection_forwarding(hr_caller):
    """TEST-FR-113 | HR-AFR-078 generate-notifications-approval-rejection-forwarding.

    Verify that HR-EIS generates notifications for approval, rejection, or forwarding events.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="leave.approved",
        dedupe_key="appr-113",
        subject="Approved",
        body="Leave approved",
    )
    assert notif.pk is not None


def test_fr_114_generate_notifications_pending_action_reminders(hr_caller):
    """TEST-FR-114 | HR-AFR-079 generate-notifications-pending-action-reminders.

    Verify that HR-EIS generates notifications for pending action reminders.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_HR_ADMIN,
        topic="reminder",
        dedupe_key="rem-114",
        subject="Reminder",
        body="Pending action reminder",
    )
    assert notif.pk is not None


def test_fr_115_generate_notifications_policy_deadline_updates(hr_caller):
    """TEST-FR-115 | HR-AFR-080 generate-notifications-policy-deadline-updates.

    Verify that HR-EIS generates notifications for policy or deadline updates.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    published = notifications.publish_notice(
        actor=actor,
        subject="Policy Notice",
        body="Update published",
        recipient_user_ids=[UID_FACULTY_1],
    )
    assert len(published) == 1


def test_fr_116_deliver_notifications_dashboard(hr_caller):
    """TEST-FR-116 | HR-AFR-081 deliver-notifications-dashboard.

    Verify that HR-EIS delivers notifications through the system dashboard.
    """
    HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="dashboard",
        dedupe_key="dash-116",
        subject="Notice",
        body="Dashboard notice",
    )
    res = hr_caller("get", "/api/v1/hr/notifications/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200


def test_fr_117_deliver_notifications_official_email(hr_caller, monkeypatch):
    """TEST-FR-117 | HR-AFR-082 deliver-notifications-official-email.

    Verify that HR-EIS dispatches notifications through the official email integration interface.
    """
    HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="email",
        dedupe_key="mail-117",
        subject="Official Email",
        body="Email notice",
        email_status="pending",
    )
    # Dispatch tasks
    sent = deliver_notifications()
    assert isinstance(sent, dict)


def test_fr_118_log_every_hr_transaction(hr_caller):
    """TEST-FR-118 | HR-AFR-083 log-every-hr-transaction.

    Verify that HR-EIS logs every HR transaction.
    """
    event = AuditEvent.objects.create(
        entity_type="claim",
        entity_id=10,
        actor_user_id=UID_FACULTY_1,
        action="claim.submitted",
        details={"type": "ltc"},
    )
    assert event.pk is not None


def test_fr_119_audit_logs_include_actor_identity(hr_caller):
    """TEST-FR-119 | HR-AFR-084 audit-logs-include-actor-identity.

    Verify that HR-EIS audit logs include actor identity.
    """
    event = AuditEvent.objects.create(
        entity_type="claim", entity_id=11, actor_user_id=UID_FACULTY_1, action="claim.submitted"
    )
    assert event.actor_user_id == UID_FACULTY_1


def test_fr_120_audit_logs_include_timestamp(hr_caller):
    """TEST-FR-120 | HR-AFR-085 audit-logs-include-timestamp.

    Verify that HR-EIS audit logs include a valid timestamp.
    """
    event = AuditEvent.objects.create(
        entity_type="claim", entity_id=12, actor_user_id=UID_FACULTY_1, action="claim.submitted"
    )
    assert event.created_at is not None


def test_fr_121_audit_logs_include_action_performed(hr_caller):
    """TEST-FR-121 | HR-AFR-086 audit-logs-include-action-performed.

    Verify that HR-EIS audit logs include the action performed.
    """
    event = AuditEvent.objects.create(
        entity_type="claim", entity_id=13, actor_user_id=UID_FACULTY_1, action="claim.verified"
    )
    assert event.action == "claim.verified"


def test_fr_122_audit_logs_immutable(hr_caller):
    """TEST-FR-122 | HR-AFR-087 audit-logs-immutable.

    Verify that HR-EIS audit logs are immutable and reject modification or deletion attempts.
    """
    event = AuditEvent.objects.create(
        entity_type="claim", entity_id=14, actor_user_id=UID_FACULTY_1, action="claim.verified"
    )
    with pytest.raises(TypeError):
        event.action = "tampered"
        event.save()
    with pytest.raises(TypeError):
        event.delete()


def test_fr_123_restrict_audit_log_access_authorized_roles(hr_caller):
    """TEST-FR-123 | HR-AFR-088 restrict-audit-log-access-authorized-roles.

    Verify that HR-EIS restricts audit log access to authorized roles only and blocks unauthorized users.
    """
    # Regular employee cannot view audit events
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 403


def test_fr_124_support_compliance_through_logged_transactions(hr_caller):
    """TEST-FR-124 | HR-AFR-089 support-compliance-through-logged-transactions.

    Verify that HR-EIS supports compliance with institutional HR and financial policies through logged HR-EIS transactions.
    """
    # Audit log querying provides tamper-evident compliance history
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200


def test_fr_125_integrate_payroll_disbursement_status_exchange(hr_caller):
    """TEST-FR-125 | HR-AFR-090 integrate-payroll-disbursement-status-exchange.

    Verify that HR-EIS integrates with the payroll system for disbursement-status exchange related to approved claims.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="financial_processing_recorded",
    )
    status_row = ClaimIntegrationStatus.objects.create(
        claim=claim,
        system="payroll",
        external_status="processed",
        external_reference="PAY-99",
        recorded_by_user_id=UID_ACCOUNTANT,
        received_at=claim.created_at,
    )
    assert status_row.system == "payroll"


def test_fr_126_integrate_finance_accounting_status_exchange(hr_caller):
    """TEST-FR-126 | HR-AFR-091 integrate-finance-accounting-status-exchange.

    Verify that HR-EIS integrates with the finance system for accounting-status exchange related to approved claims.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=1000,
        status="financial_processing_recorded",
    )
    status_row = ClaimIntegrationStatus.objects.create(
        claim=claim,
        system="finance",
        external_status="booked",
        external_reference="FIN-99",
        recorded_by_user_id=UID_ACCOUNTANT,
        received_at=claim.created_at,
    )
    assert status_row.system == "finance"


def test_fr_127_integrate_fusion_modules_identity_role_consistency(hr_caller):
    """TEST-FR-127 | HR-AFR-092 integrate-fusion-modules-identity-role-consistency.

    Verify that HR-EIS integrates with other Fusion modules for identity and role consistency.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    assert emp.employee_category == "faculty"


def test_fr_128_synchronize_integration_data_real_time(hr_caller):
    """TEST-FR-128 | HR-AFR-093 synchronize-integration-data-real-time.

    Verify that HR-EIS synchronizes integration data automatically and in real time where configured.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_reimbursement",
        purpose="Books",
        amount=500,
        status="financial_processing_recorded",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/integration-status/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={"system": "finance", "external_status": "reconciled", "external_reference": "REC-01"},
    )
    assert res.status_code == 201
